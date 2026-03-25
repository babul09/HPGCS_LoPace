"""
Delta Compression Store — HPGCS Research Extension

Compresses prompts by storing diffs against cluster centroids.
For corpora where prompts are similar but not identical (e.g., 
ShareGPT conversations about similar topics), this captures
partial redundancy that exact dedup misses.

Architecture:
  1. Maintain a set of cluster centroids (representative prompts)
  2. For each new prompt, find the most similar centroid
  3. If similarity > threshold: store compressed delta (diff)
  4. If similarity < threshold: store as new centroid
  5. Reconstruct: retrieve centroid + apply delta
"""

import difflib
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

_DELTA_SCHEMA = """
CREATE TABLE IF NOT EXISTS centroids (
    centroid_id     TEXT PRIMARY KEY,
    compressed_text BLOB NOT NULL,
    original_size   INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    ref_count       INTEGER NOT NULL DEFAULT 0,
    text_hash       TEXT NOT NULL,
    created_at      REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS delta_prompts (
    prompt_id       TEXT PRIMARY KEY,
    original_hash   TEXT NOT NULL,
    original_size   INTEGER NOT NULL,
    centroid_id     TEXT NOT NULL,
    similarity      REAL NOT NULL,
    compressed_delta BLOB NOT NULL,
    delta_size      INTEGER NOT NULL,
    storage_mode    TEXT NOT NULL,
    created_at      REAL NOT NULL,
    FOREIGN KEY (centroid_id) REFERENCES centroids(centroid_id)
);

CREATE INDEX IF NOT EXISTS idx_dp_centroid
    ON delta_prompts(centroid_id);
"""


def _compute_delta(source: str, target: str) -> str:
    """
    Compute a compact diff from source to target.
    
    Uses unified diff format which is compact for similar texts
    and compresses well with Zstd.
    """
    source_lines = source.splitlines(keepends=True)
    target_lines = target.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        source_lines, target_lines,
        n=0,  # no context lines — most compact
    )
    return "".join(diff)


def _apply_delta(source: str, delta: str) -> str:
    """
    Apply a unified diff to reconstruct the target text.
    
    Parses the unified diff format and applies insertions/deletions
    to the source text to produce the target.
    """
    if not delta.strip():
        return source
    
    source_lines = source.splitlines(keepends=True)
    result_lines = list(source_lines)
    
    # Parse unified diff
    hunks = []
    current_hunk = None
    
    for line in delta.splitlines(keepends=True):
        if line.startswith("@@"):
            # Parse hunk header: @@ -start,count +start,count @@
            if current_hunk:
                hunks.append(current_hunk)
            
            parts = line.split("@@")
            if len(parts) >= 2:
                ranges = parts[1].strip().split()
                src_range = ranges[0] if ranges else "-1"
                dst_range = ranges[1] if len(ranges) > 1 else "+1"
                
                src_start = abs(int(src_range.split(",")[0]))
                current_hunk = {
                    "src_start": src_start - 1,  # 0-indexed
                    "removes": [],
                    "adds": [],
                }
        elif line.startswith("---") or line.startswith("+++"):
            continue
        elif current_hunk is not None:
            if line.startswith("-"):
                current_hunk["removes"].append(line[1:])
            elif line.startswith("+"):
                current_hunk["adds"].append(line[1:])
    
    if current_hunk:
        hunks.append(current_hunk)
    
    # Apply hunks in reverse order to preserve line numbers
    for hunk in reversed(hunks):
        start = hunk["src_start"]
        n_remove = len(hunk["removes"])
        
        # Remove old lines
        if n_remove > 0:
            del result_lines[start:start + n_remove]
        
        # Insert new lines
        for i, add_line in enumerate(hunk["adds"]):
            result_lines.insert(start + i, add_line)
    
    return "".join(result_lines)


def _fast_similarity(text_a: str, text_b: str) -> float:
    """
    Fast similarity using set intersection of line hashes.
    O(n) instead of O(n²).
    """
    if not text_a or not text_b:
        return 0.0

    # Length-based early rejection
    len_ratio = min(len(text_a), len(text_b)) / max(len(text_a), len(text_b))
    if len_ratio < 0.3:
        return 0.0

    # Use line-level Jaccard similarity (very fast)
    lines_a = set(text_a.split('\n'))
    lines_b = set(text_b.split('\n'))

    # Remove very short lines (whitespace, empty)
    lines_a = {l for l in lines_a if len(l.strip()) >= 3}
    lines_b = {l for l in lines_b if len(l.strip()) >= 3}

    if not lines_a or not lines_b:
        return 0.0

    intersection = len(lines_a & lines_b)
    union = len(lines_a | lines_b)

    return intersection / union if union else 0.0


class DeltaStore:
    """
    Delta compression store using cluster centroids.
    
    For each new prompt:
      1. Compare against existing centroids
      2. If similar enough: store as compressed diff from centroid
      3. If not similar: create a new centroid
    
    This captures partial redundancy between similar-but-not-identical
    prompts, which exact deduplication completely misses.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        zstd_level: int = 15,
        similarity_threshold: float = 0.4,
        max_centroids: int = 1000,
        sample_centroids: int = 50,
    ):
        """
        Args:
            db_path: SQLite database path.
            zstd_level: Compression level for both centroids and deltas.
            similarity_threshold: Minimum similarity to use delta encoding.
                                  Lower = more deltas, higher overhead.
            max_centroids: Maximum number of centroids to maintain.
            sample_centroids: Number of centroids to compare against
                              (for speed — don't compare against all).
        """
        self.db_path = db_path
        self.zstd_level = zstd_level
        self.similarity_threshold = similarity_threshold
        self.max_centroids = max_centroids
        self.sample_centroids = sample_centroids
        
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DELTA_SCHEMA)
        self._conn.commit()

        if _ZSTD:
            self._cctx = zstd.ZstdCompressor(level=zstd_level)
            self._dctx = zstd.ZstdDecompressor()
        else:
            self._cctx = self._dctx = None

        # In-memory centroid cache: centroid_id → text
        self._centroids: Dict[str, str] = {}
        self._centroid_ids: List[str] = []  # ordered for sampling
        self._load_centroids()

    def _load_centroids(self):
        """Load existing centroids into memory."""
        rows = self._conn.execute(
            "SELECT centroid_id, compressed_text FROM centroids "
            "ORDER BY ref_count DESC"
        ).fetchall()
        for row in rows:
            text = self._decompress(bytes(row["compressed_text"])).decode("utf-8")
            cid = row["centroid_id"]
            self._centroids[cid] = text
            self._centroid_ids.append(cid)

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _compress(self, data: bytes) -> bytes:
        if self._cctx:
            return self._cctx.compress(data)
        return _gzip.compress(data)

    def _decompress(self, data: bytes) -> bytes:
        if self._dctx:
            return self._dctx.decompress(data)
        return _gzip.decompress(data)

    def _find_best_centroid(self, text: str) -> Tuple[Optional[str], float]:
        """
        Find the most similar centroid for the given text.
        
        For efficiency, samples a subset of centroids rather than
        comparing against all of them.
        """
        if not self._centroid_ids:
            return None, 0.0

        # Sample centroids to compare against
        import random
        if len(self._centroid_ids) <= self.sample_centroids:
            candidates = self._centroid_ids
        else:
            # Always include the most recent centroids + random sample
            recent = self._centroid_ids[-10:]
            rest = self._centroid_ids[:-10]
            n_sample = min(self.sample_centroids - len(recent), len(rest))
            sampled = random.sample(rest, n_sample) if n_sample > 0 else []
            candidates = recent + sampled

        best_id = None
        best_sim = 0.0

        for cid in candidates:
            centroid_text = self._centroids[cid]
            sim = _fast_similarity(text, centroid_text)
            if sim > best_sim:
                best_sim = sim
                best_id = cid

        return best_id, best_sim

    def store(self, prompt_id: str, text: str) -> Dict[str, Any]:
        """
        Store a prompt using delta compression against centroids.
        
        Returns metrics dict.
        """
        t0 = time.perf_counter()
        raw = text.encode("utf-8")
        original_size = len(raw)
        original_hash = self._sha256(text)

        # Find best matching centroid
        best_cid, similarity = self._find_best_centroid(text)

        if best_cid and similarity >= self.similarity_threshold:
            # ── Delta mode: store diff from centroid ──
            centroid_text = self._centroids[best_cid]
            delta = _compute_delta(centroid_text, text)
            delta_bytes = delta.encode("utf-8")
            compressed_delta = self._compress(delta_bytes)
            delta_size = len(compressed_delta)

            # Verify delta correctness before storing
            reconstructed = _apply_delta(centroid_text, delta)
            if reconstructed != text:
                # Delta reconstruction failed — store as new centroid instead
                return self._store_as_centroid(prompt_id, text, original_hash,
                                                original_size, t0,
                                                reason="delta_verify_failed")

            self._conn.execute(
                "INSERT OR REPLACE INTO delta_prompts "
                "(prompt_id, original_hash, original_size, centroid_id, "
                " similarity, compressed_delta, delta_size, storage_mode, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (prompt_id, original_hash, original_size, best_cid,
                 similarity, compressed_delta, delta_size, "delta", time.time()),
            )
            self._conn.execute(
                "UPDATE centroids SET ref_count = ref_count + 1 "
                "WHERE centroid_id = ?",
                (best_cid,),
            )
            self._conn.commit()

            elapsed = time.perf_counter() - t0
            return {
                "prompt_id": prompt_id,
                "original_size": original_size,
                "stored_size": delta_size,
                "storage_mode": "delta",
                "centroid_id": best_cid,
                "similarity": similarity,
                "compression_ratio": original_size / delta_size if delta_size else float("inf"),
                "savings_pct": (1 - delta_size / original_size) * 100,
                "time_s": elapsed,
            }
        else:
            # ── Centroid mode: store as new centroid ──
            return self._store_as_centroid(prompt_id, text, original_hash,
                                            original_size, t0)

    def _store_as_centroid(self, prompt_id: str, text: str,
                           original_hash: str, original_size: int,
                           t0: float, reason: str = "new_centroid") -> Dict[str, Any]:
        """Store prompt as a new centroid."""
        raw = text.encode("utf-8")
        compressed = self._compress(raw)
        compressed_size = len(compressed)

        centroid_id = f"C{len(self._centroid_ids):06d}"

        self._conn.execute(
            "INSERT INTO centroids "
            "(centroid_id, compressed_text, original_size, compressed_size, "
            " ref_count, text_hash, created_at) "
            "VALUES (?,?,?,?,0,?,?)",
            (centroid_id, compressed, original_size, compressed_size,
             original_hash, time.time()),
        )

        # Also store in delta_prompts for uniform retrieval
        self._conn.execute(
            "INSERT OR REPLACE INTO delta_prompts "
            "(prompt_id, original_hash, original_size, centroid_id, "
            " similarity, compressed_delta, delta_size, storage_mode, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (prompt_id, original_hash, original_size, centroid_id,
             1.0, b"", 0, "centroid", time.time()),
        )
        self._conn.commit()

        # Cache in memory
        self._centroids[centroid_id] = text
        self._centroid_ids.append(centroid_id)

        elapsed = time.perf_counter() - t0
        return {
            "prompt_id": prompt_id,
            "original_size": original_size,
            "stored_size": compressed_size,
            "storage_mode": reason,
            "centroid_id": centroid_id,
            "similarity": 1.0,
            "compression_ratio": original_size / compressed_size if compressed_size else 0,
            "savings_pct": (1 - compressed_size / original_size) * 100,
            "time_s": elapsed,
        }

    def retrieve(self, prompt_id: str) -> Tuple[Optional[str], dict]:
        """Reconstruct a prompt from storage."""
        t0 = time.perf_counter()
        
        row = self._conn.execute(
            "SELECT * FROM delta_prompts WHERE prompt_id = ?",
            (prompt_id,),
        ).fetchone()
        if not row:
            return None, {"error": "not found", "exact_match": False}

        original_hash = row["original_hash"]
        centroid_id = row["centroid_id"]
        storage_mode = row["storage_mode"]

        # Load centroid
        centroid_row = self._conn.execute(
            "SELECT compressed_text FROM centroids WHERE centroid_id = ?",
            (centroid_id,),
        ).fetchone()
        if not centroid_row:
            return None, {"error": f"missing centroid {centroid_id}", "exact_match": False}

        centroid_text = self._decompress(
            bytes(centroid_row["compressed_text"])
        ).decode("utf-8")

        if storage_mode == "centroid" or storage_mode == "new_centroid":
            text = centroid_text
        else:
            # Delta mode — apply diff
            compressed_delta = bytes(row["compressed_delta"])
            delta = self._decompress(compressed_delta).decode("utf-8")
            text = _apply_delta(centroid_text, delta)

        rebuilt_hash = self._sha256(text)
        elapsed = time.perf_counter() - t0

        return text, {
            "exact_match": rebuilt_hash == original_hash,
            "hash_match": rebuilt_hash == original_hash,
            "original_hash": original_hash,
            "rebuilt_hash": rebuilt_hash,
            "storage_mode": storage_mode,
            "centroid_id": centroid_id,
            "reconstruction_time_s": elapsed,
        }

    def corpus_stats(self) -> Dict[str, Any]:
        """Compute corpus-wide statistics."""
        prompts = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(original_size), 0) AS orig, "
            "  COALESCE(SUM(delta_size), 0) AS delta_total, "
            "  SUM(CASE WHEN storage_mode = 'delta' THEN 1 ELSE 0 END) AS n_deltas, "
            "  SUM(CASE WHEN storage_mode != 'delta' THEN 1 ELSE 0 END) AS n_centroids_used, "
            "  AVG(CASE WHEN storage_mode = 'delta' THEN similarity ELSE NULL END) AS avg_sim "
            "FROM delta_prompts"
        ).fetchone()

        centroids = self._conn.execute(
            "SELECT COUNT(*) AS n, "
            "  COALESCE(SUM(compressed_size), 0) AS comp, "
            "  COALESCE(SUM(original_size), 0) AS orig "
            "FROM centroids"
        ).fetchone()

        n_prompts = prompts["n"]
        total_original = prompts["orig"]
        total_delta_bytes = prompts["delta_total"]
        n_deltas = prompts["n_deltas"]
        n_centroid_refs = prompts["n_centroids_used"]
        avg_similarity = prompts["avg_sim"] or 0
        n_centroids = centroids["n"]
        centroid_bytes = centroids["comp"]

        total_stored = centroid_bytes + total_delta_bytes

        return {
            "n_prompts": n_prompts,
            "n_centroids": n_centroids,
            "n_deltas": n_deltas,
            "n_stored_as_centroid": n_centroid_refs,
            "avg_delta_similarity": avg_similarity,
            "total_original_bytes": total_original,
            "total_centroid_bytes": centroid_bytes,
            "total_delta_bytes": total_delta_bytes,
            "total_stored_bytes": total_stored,
            "corpus_compression_ratio": total_original / total_stored if total_stored else 0,
            "corpus_space_savings_pct": (1 - total_stored / total_original) * 100 if total_original else 0,
            "delta_fraction": n_deltas / n_prompts if n_prompts else 0,
            "centroid_overhead_pct": centroid_bytes / total_stored * 100 if total_stored else 0,
        }

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()