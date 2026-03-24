"""
Corpus-Level Deduplication Store — HPGCS Research Extension

Core idea: Instead of compressing each prompt independently, split prompts
into structural components and store each unique component ONCE.
Prompts are stored as lightweight reconstruction blueprints.

For corpora where prompts share system instructions, tool schemas, RAG
passages, or other boilerplate, this achieves dramatically higher
corpus-level compression than per-prompt methods.

Modules used:
    • PromptParser.parse_segments()  → lossless structural segmentation
    • Zstd                          → per-node compression
    • SHA-256                       → content-addressable deduplication
    • SQLite                        → persistent storage
"""

import hashlib
import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import zstandard as zstd

    _ZSTD = True
except ImportError:
    zstd = None
    _ZSTD = False

import gzip as _gzip


# ─── Schema ───────────────────────────────────────────────────────────────────

_CORPUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS content_nodes (
    content_hash    TEXT PRIMARY KEY,
    component_type  TEXT NOT NULL,
    compressed_data BLOB NOT NULL,
    original_size   INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    ref_count       INTEGER NOT NULL DEFAULT 1,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_blueprints (
    prompt_id       TEXT PRIMARY KEY,
    original_hash   TEXT NOT NULL,
    original_size   INTEGER NOT NULL,
    blueprint       BLOB NOT NULL,
    blueprint_size  INTEGER NOT NULL,
    n_refs          INTEGER NOT NULL DEFAULT 0,
    n_literals      INTEGER NOT NULL DEFAULT 0,
    n_reused        INTEGER NOT NULL DEFAULT 0,
    n_new           INTEGER NOT NULL DEFAULT 0,
    cluster_id      TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cn_refcount
    ON content_nodes(ref_count DESC);

CREATE INDEX IF NOT EXISTS idx_pb_original_hash
    ON prompt_blueprints(original_hash);
"""


class CorpusStore:
    """
    Content-addressable store with per-component deduplication.

    Storage model
    ─────────────
    content_nodes:    hash → compressed(content)   [each unique component once]
    prompt_blueprints: prompt_id → [ref/literal]*   [reconstruction recipe]

    Compression flow
    ────────────────
    For each prompt:
      1. Split into segments (literals + content refs) via PromptParser
      2. For each content ref:
           hash = SHA-256(content)
           if hash in content_nodes:  increment ref_count  (0 new bytes)
           else:                      compress & store       (new bytes)
      3. Store blueprint: ordered list of literal texts + content hashes

    Reconstruction
    ──────────────
    Load blueprint → for each ref, decompress from content_nodes →
    concatenate with literals → verify SHA-256 of full text
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        zstd_level: int = 15,
    ):
        self.db_path = db_path
        self.zstd_level = zstd_level
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CORPUS_SCHEMA)
        self._conn.commit()

        # Compressor / decompressor
        if _ZSTD:
            self._cctx = zstd.ZstdCompressor(level=zstd_level)
            self._dctx = zstd.ZstdDecompressor()
        else:
            self._cctx = self._dctx = None

        # Fast in-memory set of known hashes (avoids DB round-trips)
        self._known: set = set()
        self._load_known()

    # ── helpers ───────────────────────────────────────────────────────

    def _load_known(self):
        rows = self._conn.execute(
            "SELECT content_hash FROM content_nodes"
        ).fetchall()
        self._known = {r["content_hash"] for r in rows}

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _short_hash(text: str) -> str:
        """16-char hash prefix — sufficient for dedup with collision probability < 1e-19."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _compress_blueprint(self, blueprint: list) -> bytes:
        """Compress the JSON blueprint with Zstd for compact storage."""
        bp_json = json.dumps(blueprint, separators=(",", ":")).encode("utf-8")
        return self._compress(bp_json)

    def _decompress_blueprint(self, data: bytes) -> list:
        """Decompress a stored blueprint."""
        bp_json = self._decompress(data)
        return json.loads(bp_json.decode("utf-8"))

    # ── Store ─────────────────────────────────────────────────────────

    def store(
            self,
            prompt_id: str,
            text: str,
            segments: List[dict],
            cluster_id: str = "",
        ) -> Dict[str, Any]:
            """
            Store a prompt using corpus-level component deduplication.

            Args:
                prompt_id:  Unique identifier.
                text:       Original prompt text.
                segments:   Output of PromptParser.parse_segments(text).
                cluster_id: Optional cluster assignment.

            Returns:
                Metrics dict with compression statistics.
            """
            t0 = time.perf_counter()
            original_bytes = text.encode("utf-8")
            original_size = len(original_bytes)
            original_hash = self._sha256(text)

            blueprint: List[dict] = []
            new_bytes = 0
            reused = 0
            new = 0

            for seg in segments:
                if seg["type"] == "literal":
                    blueprint.append({"t": "l", "v": seg["text"]})

                elif seg["type"] == "ref":
                    content = seg["content"]
                    # Use full hash for storage key, short hash for blueprint
                    full_hash = self._sha256(content)
                    short_h = full_hash[:16]
                    ctype = seg.get("ctype", "unstructured")

                    if full_hash in self._known:
                        self._conn.execute(
                            "UPDATE content_nodes "
                            "SET ref_count = ref_count + 1 "
                            "WHERE content_hash = ?",
                            (full_hash,),
                        )
                        reused += 1
                    else:
                        raw = content.encode("utf-8")
                        compressed = self._compress(raw)
                        self._conn.execute(
                            "INSERT INTO content_nodes "
                            "(content_hash, component_type, compressed_data, "
                            " original_size, compressed_size, ref_count, created_at) "
                            "VALUES (?,?,?,?,?,1,?)",
                            (full_hash, ctype, compressed,
                            len(raw), len(compressed), time.time()),
                        )
                        self._known.add(full_hash)
                        new_bytes += len(compressed)
                        new += 1

                    # Store short hash in blueprint to reduce size
                    blueprint.append({"t": "r", "h": short_h, "f": full_hash})

            # Compress the blueprint itself
            bp_compressed = self._compress_blueprint(blueprint)
            bp_size = len(bp_compressed)

            self._conn.execute(
                "INSERT OR REPLACE INTO prompt_blueprints "
                "(prompt_id, original_hash, original_size, blueprint, "
                " blueprint_size, n_refs, n_literals, n_reused, n_new, "
                " cluster_id, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    prompt_id, original_hash, original_size,
                    bp_compressed,       # Now storing compressed bytes
                    bp_size,
                    reused + new,
                    sum(1 for s in segments if s["type"] == "literal"),
                    reused, new, cluster_id, time.time(),
                ),
            )
            self._conn.commit()

            elapsed = time.perf_counter() - t0
            marginal = bp_size + new_bytes

            return {
                "prompt_id": prompt_id,
                "original_size": original_size,
                "blueprint_size": bp_size,
                "new_bytes_stored": new_bytes,
                "marginal_bytes": marginal,
                "reused_refs": reused,
                "new_refs": new,
                "total_refs": reused + new,
                "marginal_ratio": (
                    original_size / marginal if marginal > 0 else float("inf")
                ),
                "marginal_savings_pct": (
                    (1 - marginal / original_size) * 100 if original_size else 0.0
                ),
                "compression_time_s": elapsed,
            }

    # ── Retrieve ──────────────────────────────────────────────────────

    def retrieve(self, prompt_id: str) -> Tuple[Optional[str], dict]:
        """
        Reconstruct a prompt from its blueprint + shared nodes.

        Returns:
            (text | None, verification_dict)
        """
        t0 = time.perf_counter()
        row = self._conn.execute(
            "SELECT * FROM prompt_blueprints WHERE prompt_id = ?",
            (prompt_id,),
        ).fetchone()
        if not row:
            return None, {"error": "not found", "exact_match": False}

        # Blueprint is now stored as compressed bytes
        bp_data = bytes(row["blueprint"])
        blueprint = self._decompress_blueprint(bp_data)
        original_hash = row["original_hash"]

        parts: List[str] = []
        for seg in blueprint:
            if seg["t"] == "l":
                parts.append(seg["v"])
            elif seg["t"] == "r":
                # Use full hash to retrieve
                full_hash = seg.get("f", seg["h"])
                node = self._conn.execute(
                    "SELECT compressed_data FROM content_nodes "
                    "WHERE content_hash = ?",
                    (full_hash,),
                ).fetchone()
                if not node:
                    return None, {
                        "error": f"missing node {full_hash[:16]}...",
                        "exact_match": False,
                    }
                raw = self._decompress(bytes(node["compressed_data"]))
                parts.append(raw.decode("utf-8"))

        text = "".join(parts)
        rebuilt_hash = self._sha256(text)
        elapsed = time.perf_counter() - t0

        return text, {
            "exact_match": rebuilt_hash == original_hash,
            "hash_match": rebuilt_hash == original_hash,
            "original_hash": original_hash,
            "rebuilt_hash": rebuilt_hash,
            "reconstruction_time_s": elapsed,
        }

    # ── Corpus-level analytics ────────────────────────────────────────

    def corpus_stats(self) -> Dict[str, Any]:
        """
        Compute corpus-wide compression statistics.

        Key metrics:
          corpus_stored_bytes:      actual bytes on disk (nodes + blueprints)
          corpus_compression_ratio: total_original / corpus_stored
          avg_refs_per_node:        mean reuse factor (higher = more sharing)
          marginal_cost_latest:     storage cost of the most recent prompt
        """
        p = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(original_size), 0) AS orig, "
            "  COALESCE(SUM(blueprint_size), 0) AS bp "
            "FROM prompt_blueprints"
        ).fetchone()

        c = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(original_size), 0) AS node_orig, "
            "  COALESCE(SUM(compressed_size), 0) AS node_comp, "
            "  COALESCE(SUM(ref_count), 0) AS total_refs "
            "FROM content_nodes"
        ).fetchone()

        n_prompts = p["n"]
        total_original = p["orig"]
        total_bp = p["bp"]
        n_nodes = c["n"]
        total_node_comp = c["node_comp"]
        total_node_orig = c["node_orig"]
        total_refs = c["total_refs"]
        corpus_stored = total_node_comp + total_bp

        return {
            "n_prompts": n_prompts,
            "n_unique_nodes": n_nodes,
            "total_refs": total_refs,
            "avg_refs_per_node": total_refs / n_nodes if n_nodes else 0,
            "total_original_bytes": total_original,
            "total_node_original_bytes": total_node_orig,
            "total_node_compressed_bytes": total_node_comp,
            "total_blueprint_bytes": total_bp,
            "corpus_stored_bytes": corpus_stored,
            "corpus_compression_ratio": (
                total_original / corpus_stored if corpus_stored else 0
            ),
            "corpus_space_savings_pct": (
                (1 - corpus_stored / total_original) * 100
                if total_original else 0
            ),
            "node_compression_ratio": (
                total_node_orig / total_node_comp if total_node_comp else 0
            ),
            "storage_overhead_bytes": total_bp,
            "storage_overhead_pct": (
                total_bp / corpus_stored * 100 if corpus_stored else 0
            ),
        }

    def node_reuse_report(self) -> List[dict]:
        """Return nodes sorted by reuse count (most shared first)."""
        rows = self._conn.execute(
            "SELECT content_hash, component_type, original_size, "
            "  compressed_size, ref_count "
            "FROM content_nodes ORDER BY ref_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Housekeeping ──────────────────────────────────────────────────

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __repr__(self):
        s = self.corpus_stats()
        return (
            f"CorpusStore(prompts={s['n_prompts']}, "
            f"nodes={s['n_unique_nodes']}, "
            f"ratio={s['corpus_compression_ratio']:.1f}x)"
        )
"""
Corpus-Level Deduplication Store — HPGCS Research Extension

Core idea: Instead of compressing each prompt independently, split prompts
into structural components and store each unique component ONCE.
Prompts are stored as lightweight reconstruction blueprints.
"""

import hashlib
import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    zstd = None
    _ZSTD = False

import gzip as _gzip


# ─── Schema ───────────────────────────────────────────────────────────────────

_CORPUS_SCHEMA = """
CREATE TABLE IF NOT EXISTS content_nodes (
    content_hash    TEXT PRIMARY KEY,
    component_type  TEXT NOT NULL,
    compressed_data BLOB NOT NULL,
    original_size   INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    ref_count       INTEGER NOT NULL DEFAULT 1,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_blueprints (
    prompt_id       TEXT PRIMARY KEY,
    original_hash   TEXT NOT NULL,
    original_size   INTEGER NOT NULL,
    blueprint       BLOB NOT NULL,
    blueprint_size  INTEGER NOT NULL,
    n_refs          INTEGER NOT NULL DEFAULT 0,
    n_literals      INTEGER NOT NULL DEFAULT 0,
    n_reused        INTEGER NOT NULL DEFAULT 0,
    n_new           INTEGER NOT NULL DEFAULT 0,
    cluster_id      TEXT NOT NULL DEFAULT '',
    created_at      REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_cn_refcount
    ON content_nodes(ref_count DESC);

CREATE INDEX IF NOT EXISTS idx_pb_original_hash
    ON prompt_blueprints(original_hash);
"""


class CorpusStore:
    """
    Content-addressable store with per-component deduplication.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        zstd_level: int = 15,
    ):
        self.db_path = db_path
        self.zstd_level = zstd_level
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_CORPUS_SCHEMA)
        self._conn.commit()

        # Compressor / decompressor
        if _ZSTD:
            self._cctx = zstd.ZstdCompressor(level=zstd_level)
            self._dctx = zstd.ZstdDecompressor()
        else:
            self._cctx = self._dctx = None

        # Fast in-memory set of known hashes
        self._known: set = set()
        self._load_known()

    # ── helpers ───────────────────────────────────────────────────────

    def _load_known(self):
        rows = self._conn.execute(
            "SELECT content_hash FROM content_nodes"
        ).fetchall()
        self._known = {r["content_hash"] for r in rows}

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _short_hash(text: str) -> str:
        """16-char hash prefix for compact blueprint storage."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _compress(self, data: bytes) -> bytes:
        """Compress bytes using Zstd (or gzip fallback)."""
        if self._cctx:
            return self._cctx.compress(data)
        return _gzip.compress(data)

    def _decompress(self, data: bytes) -> bytes:
        """Decompress bytes using Zstd (or gzip fallback)."""
        if self._dctx:
            return self._dctx.decompress(data)
        return _gzip.decompress(data)

    def _compress_blueprint(self, blueprint: list) -> bytes:
        """Compress the JSON blueprint for compact storage."""
        bp_json = json.dumps(blueprint, separators=(",", ":")).encode("utf-8")
        return self._compress(bp_json)

    def _decompress_blueprint(self, data: bytes) -> list:
        """Decompress a stored blueprint."""
        bp_json = self._decompress(data)
        return json.loads(bp_json.decode("utf-8"))

    # ── Store ─────────────────────────────────────────────────────────

    def store(
        self,
        prompt_id: str,
        text: str,
        segments: List[dict],
        cluster_id: str = "",
    ) -> Dict[str, Any]:
        """
        Store a prompt using corpus-level component deduplication.

        Args:
            prompt_id:  Unique identifier.
            text:       Original prompt text.
            segments:   Output of PromptParser.parse_segments(text).
            cluster_id: Optional cluster assignment.

        Returns:
            Metrics dict with compression statistics.
        """
        t0 = time.perf_counter()
        original_bytes = text.encode("utf-8")
        original_size = len(original_bytes)
        original_hash = self._sha256(text)

        blueprint: List[dict] = []
        new_bytes = 0
        reused = 0
        new = 0

        for seg in segments:
            if seg["type"] == "literal":
                blueprint.append({"t": "l", "v": seg["text"]})

            elif seg["type"] == "ref":
                content = seg["content"]
                full_hash = self._sha256(content)
                ctype = seg.get("ctype", "unstructured")

                if full_hash in self._known:
                    self._conn.execute(
                        "UPDATE content_nodes "
                        "SET ref_count = ref_count + 1 "
                        "WHERE content_hash = ?",
                        (full_hash,),
                    )
                    reused += 1
                else:
                    raw = content.encode("utf-8")
                    compressed = self._compress(raw)
                    self._conn.execute(
                        "INSERT INTO content_nodes "
                        "(content_hash, component_type, compressed_data, "
                        " original_size, compressed_size, ref_count, created_at) "
                        "VALUES (?,?,?,?,?,1,?)",
                        (full_hash, ctype, compressed,
                         len(raw), len(compressed), time.time()),
                    )
                    self._known.add(full_hash)
                    new_bytes += len(compressed)
                    new += 1

                # Store full hash in blueprint for retrieval
                blueprint.append({"t": "r", "h": full_hash[:16], "f": full_hash})

        # Compress the blueprint itself
        bp_compressed = self._compress_blueprint(blueprint)
        bp_size = len(bp_compressed)

        self._conn.execute(
            "INSERT OR REPLACE INTO prompt_blueprints "
            "(prompt_id, original_hash, original_size, blueprint, "
            " blueprint_size, n_refs, n_literals, n_reused, n_new, "
            " cluster_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                prompt_id, original_hash, original_size,
                bp_compressed,
                bp_size,
                reused + new,
                sum(1 for s in segments if s["type"] == "literal"),
                reused, new, cluster_id, time.time(),
            ),
        )
        self._conn.commit()

        elapsed = time.perf_counter() - t0
        marginal = bp_size + new_bytes

        return {
            "prompt_id": prompt_id,
            "original_size": original_size,
            "blueprint_size": bp_size,
            "new_bytes_stored": new_bytes,
            "marginal_bytes": marginal,
            "reused_refs": reused,
            "new_refs": new,
            "total_refs": reused + new,
            "marginal_ratio": (
                original_size / marginal if marginal > 0 else float("inf")
            ),
            "marginal_savings_pct": (
                (1 - marginal / original_size) * 100 if original_size else 0.0
            ),
            "compression_time_s": elapsed,
        }


    def store_adaptive(
        self,
        prompt_id: str,
        text: str,
        segments: List[dict],
        cluster_id: str = "",
        fallback_threshold: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Adaptive storage: use corpus dedup when beneficial,
        fall back to per-prompt Zstd when dedup won't help.
        """
        ref_segments = [s for s in segments if s["type"] == "ref"]
        if not ref_segments:
            return self._store_monolithic(prompt_id, text)

        reusable = sum(
            1 for s in ref_segments
            if self._sha256(s["content"]) in self._known
        )
        reuse_fraction = reusable / len(ref_segments) if ref_segments else 0

        if reuse_fraction >= fallback_threshold:
            result = self.store(prompt_id, text, segments, cluster_id)
            result["strategy"] = "corpus_dedup"
            result["reuse_fraction"] = reuse_fraction
            return result
        else:
            result = self.store(prompt_id, text, segments, cluster_id)
            result["strategy"] = "corpus_dedup_with_new_nodes"
            result["reuse_fraction"] = reuse_fraction
            return result

    def store_chunked(
        self,
        prompt_id: str,
        text: str,
        segments: List[dict],
        cluster_id: str = "",
    ) -> Dict[str, Any]:
        """
        Store using fine-grained sub-component deduplication.
        
        Identical to store() but expects segments from 
        parse_segments_chunked() which splits large components
        into smaller chunks for finer-grained dedup.
        """
        return self.store(prompt_id, text, segments, cluster_id)

    def _store_monolithic(self, prompt_id: str, text: str) -> Dict[str, Any]:
        """Fall back: compress entire prompt as one blob."""
        t0 = time.perf_counter()
        raw = text.encode("utf-8")
        original_size = len(raw)
        original_hash = self._sha256(text)
        compressed = self._compress(raw)

        full_hash = self._sha256(text)
        if full_hash not in self._known:
            self._conn.execute(
                "INSERT INTO content_nodes "
                "(content_hash, component_type, compressed_data, "
                " original_size, compressed_size, ref_count, created_at) "
                "VALUES (?,?,?,?,?,1,?)",
                (full_hash, "monolithic", compressed,
                 original_size, len(compressed), time.time()),
            )
            self._known.add(full_hash)

        blueprint = [{"t": "r", "h": full_hash[:16], "f": full_hash}]
        bp_compressed = self._compress_blueprint(blueprint)
        bp_size = len(bp_compressed)

        self._conn.execute(
            "INSERT OR REPLACE INTO prompt_blueprints "
            "(prompt_id, original_hash, original_size, blueprint, "
            " blueprint_size, n_refs, n_literals, n_reused, n_new, "
            " cluster_id, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (prompt_id, original_hash, original_size,
             bp_compressed, bp_size, 1, 0, 0, 1, "", time.time()),
        )
        self._conn.commit()

        elapsed = time.perf_counter() - t0
        marginal = bp_size + len(compressed)

        return {
            "prompt_id": prompt_id,
            "original_size": original_size,
            "blueprint_size": bp_size,
            "new_bytes_stored": len(compressed),
            "marginal_bytes": marginal,
            "reused_refs": 0,
            "new_refs": 1,
            "total_refs": 1,
            "marginal_ratio": original_size / marginal if marginal else float("inf"),
            "marginal_savings_pct": (1 - marginal / original_size) * 100 if original_size else 0,
            "compression_time_s": elapsed,
            "strategy": "monolithic_fallback",
            "reuse_fraction": 0.0,
        }

    



    # ── Retrieve ──────────────────────────────────────────────────────

    def retrieve(self, prompt_id: str) -> Tuple[Optional[str], dict]:
        """
        Reconstruct a prompt from its blueprint + shared nodes.

        Returns:
            (text | None, verification_dict)
        """
        t0 = time.perf_counter()
        row = self._conn.execute(
            "SELECT * FROM prompt_blueprints WHERE prompt_id = ?",
            (prompt_id,),
        ).fetchone()
        if not row:
            return None, {"error": "not found", "exact_match": False}

        bp_data = bytes(row["blueprint"])
        blueprint = self._decompress_blueprint(bp_data)
        original_hash = row["original_hash"]

        parts: List[str] = []
        for seg in blueprint:
            if seg["t"] == "l":
                parts.append(seg["v"])
            elif seg["t"] == "r":
                full_hash = seg.get("f", seg["h"])
                node = self._conn.execute(
                    "SELECT compressed_data FROM content_nodes "
                    "WHERE content_hash = ?",
                    (full_hash,),
                ).fetchone()
                if not node:
                    return None, {
                        "error": f"missing node {full_hash[:16]}...",
                        "exact_match": False,
                    }
                raw = self._decompress(bytes(node["compressed_data"]))
                parts.append(raw.decode("utf-8"))

        text = "".join(parts)
        rebuilt_hash = self._sha256(text)
        elapsed = time.perf_counter() - t0

        return text, {
            "exact_match": rebuilt_hash == original_hash,
            "hash_match": rebuilt_hash == original_hash,
            "original_hash": original_hash,
            "rebuilt_hash": rebuilt_hash,
            "reconstruction_time_s": elapsed,
        }

    # ── Corpus-level analytics ────────────────────────────────────────

    def corpus_stats(self) -> Dict[str, Any]:
        """Compute corpus-wide compression statistics."""
        p = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(original_size), 0) AS orig, "
            "  COALESCE(SUM(blueprint_size), 0) AS bp "
            "FROM prompt_blueprints"
        ).fetchone()

        c = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(original_size), 0) AS node_orig, "
            "  COALESCE(SUM(compressed_size), 0) AS node_comp, "
            "  COALESCE(SUM(ref_count), 0) AS total_refs "
            "FROM content_nodes"
        ).fetchone()

        n_prompts = p["n"]
        total_original = p["orig"]
        total_bp = p["bp"]
        n_nodes = c["n"]
        total_node_comp = c["node_comp"]
        total_node_orig = c["node_orig"]
        total_refs = c["total_refs"]
        corpus_stored = total_node_comp + total_bp

        return {
            "n_prompts": n_prompts,
            "n_unique_nodes": n_nodes,
            "total_refs": total_refs,
            "avg_refs_per_node": total_refs / n_nodes if n_nodes else 0,
            "total_original_bytes": total_original,
            "total_node_original_bytes": total_node_orig,
            "total_node_compressed_bytes": total_node_comp,
            "total_blueprint_bytes": total_bp,
            "corpus_stored_bytes": corpus_stored,
            "corpus_compression_ratio": (
                total_original / corpus_stored if corpus_stored else 0
            ),
            "corpus_space_savings_pct": (
                (1 - corpus_stored / total_original) * 100
                if total_original else 0
            ),
            "node_compression_ratio": (
                total_node_orig / total_node_comp if total_node_comp else 0
            ),
            "storage_overhead_bytes": total_bp,
            "storage_overhead_pct": (
                total_bp / corpus_stored * 100 if corpus_stored else 0
            ),
        }

    def node_reuse_report(self) -> List[dict]:
        """Return nodes sorted by reuse count (most shared first)."""
        rows = self._conn.execute(
            "SELECT content_hash, component_type, original_size, "
            "  compressed_size, ref_count "
            "FROM content_nodes ORDER BY ref_count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Housekeeping ──────────────────────────────────────────────────

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __repr__(self):
        s = self.corpus_stats()
        return (
            f"CorpusStore(prompts={s['n_prompts']}, "
            f"nodes={s['n_unique_nodes']}, "
            f"ratio={s['corpus_compression_ratio']:.1f}x)"
        )