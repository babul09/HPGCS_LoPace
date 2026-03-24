"""
Graph Storage Database - HPGCS Component 7

Stores compressed prompt representations using SQLite (prototype) or
an in-memory store.  Each record contains:

    Prompt ID | Graph JSON | Cluster ID | Compressed Blob | Latent Bytes

A separate nodes table stores the reusable node registry so that node
content is stored only once regardless of how many prompts reference it.
"""

import json
import sqlite3
import time
import uuid
from typing import Dict, List, Optional, Any


# ─── Record schema ────────────────────────────────────────────────────────────

class PromptRecord:
    """A single compressed prompt record."""

    __slots__ = (
        "prompt_id", "original_text", "graph_json",
        "cluster_id", "compressed_blob", "latent_bytes",
        "original_size", "compressed_size", "created_at",
    )

    def __init__(
        self,
        prompt_id: str,
        original_text: str,
        graph_json: str,
        cluster_id: str,
        compressed_blob: bytes,
        latent_bytes: bytes,
        original_size: int,
        compressed_size: int,
        created_at: float,
    ):
        self.prompt_id = prompt_id
        self.original_text = original_text
        self.graph_json = graph_json
        self.cluster_id = cluster_id
        self.compressed_blob = compressed_blob
        self.latent_bytes = latent_bytes
        self.original_size = original_size
        self.compressed_size = compressed_size
        self.created_at = created_at

    @property
    def compression_ratio(self) -> float:
        return self.original_size / self.compressed_size if self.compressed_size else 0.0

    @property
    def space_savings_pct(self) -> float:
        return (1 - self.compressed_size / self.original_size) * 100 if self.original_size else 0.0

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "graph_json": self.graph_json,
            "cluster_id": self.cluster_id,
            "original_size": self.original_size,
            "compressed_size": self.compressed_size,
            "compression_ratio": self.compression_ratio,
            "space_savings_pct": self.space_savings_pct,
            "created_at": self.created_at,
        }


# ─── Database ─────────────────────────────────────────────────────────────────

_CREATE_PROMPTS = """
CREATE TABLE IF NOT EXISTS prompts (
    prompt_id      TEXT PRIMARY KEY,
    original_text  TEXT NOT NULL,
    graph_json     TEXT NOT NULL,
    cluster_id     TEXT NOT NULL,
    compressed_blob BLOB NOT NULL,
    latent_bytes   BLOB,
    original_size  INTEGER NOT NULL,
    compressed_size INTEGER NOT NULL,
    created_at     REAL NOT NULL
);
"""

_CREATE_NODES = """
CREATE TABLE IF NOT EXISTS nodes (
    node_id        TEXT PRIMARY KEY,
    component_type TEXT NOT NULL,
    content        TEXT NOT NULL,
    content_hash   TEXT NOT NULL UNIQUE,
    frequency      INTEGER NOT NULL DEFAULT 1
);
"""

_CREATE_CLUSTERS = """
CREATE TABLE IF NOT EXISTS clusters (
    cluster_id       TEXT PRIMARY KEY,
    centroid_json    TEXT NOT NULL,
    representative   TEXT,
    member_count     INTEGER NOT NULL DEFAULT 0
);
"""


class GraphStorageDatabase:
    """
    SQLite-backed store for compressed prompt records.

    Args:
        db_path: Path to the SQLite file, or ":memory:" for an in-memory DB.
    """

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.executescript(_CREATE_PROMPTS + _CREATE_NODES + _CREATE_CLUSTERS)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Prompt CRUD
    # ------------------------------------------------------------------

    def insert_prompt(self, record: PromptRecord):
        """Insert or replace a prompt record."""
        self._conn.execute(
            """INSERT OR REPLACE INTO prompts
               (prompt_id, original_text, graph_json, cluster_id,
                compressed_blob, latent_bytes,
                original_size, compressed_size, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                record.prompt_id,
                record.original_text,
                record.graph_json,
                record.cluster_id,
                record.compressed_blob,
                record.latent_bytes,
                record.original_size,
                record.compressed_size,
                record.created_at,
            ),
        )
        self._conn.commit()

    def get_prompt(self, prompt_id: str) -> Optional[PromptRecord]:
        row = self._conn.execute(
            "SELECT * FROM prompts WHERE prompt_id = ?", (prompt_id,)
        ).fetchone()
        return self._row_to_record(row) if row else None

    def all_prompts(self) -> List[PromptRecord]:
        rows = self._conn.execute("SELECT * FROM prompts ORDER BY created_at").fetchall()
        return [self._row_to_record(r) for r in rows]

    def delete_prompt(self, prompt_id: str):
        self._conn.execute("DELETE FROM prompts WHERE prompt_id = ?", (prompt_id,))
        self._conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> PromptRecord:
        return PromptRecord(
            prompt_id=row["prompt_id"],
            original_text=row["original_text"],
            graph_json=row["graph_json"],
            cluster_id=row["cluster_id"],
            compressed_blob=bytes(row["compressed_blob"]),
            latent_bytes=bytes(row["latent_bytes"]) if row["latent_bytes"] else b"",
            original_size=row["original_size"],
            compressed_size=row["compressed_size"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def upsert_nodes(self, nodes: List[dict]):
        """Insert or update multiple reusable nodes."""
        for n in nodes:
            self._conn.execute(
                """INSERT INTO nodes (node_id, component_type, content, content_hash, frequency)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(node_id) DO UPDATE SET frequency=excluded.frequency""",
                (n["node_id"], n["component_type"], n["content"], n["content_hash"], n["frequency"]),
            )
        self._conn.commit()

    def get_node(self, node_id: str) -> Optional[dict]:
        row = self._conn.execute(
            "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
        ).fetchone()
        return dict(row) if row else None

    def all_nodes(self) -> List[dict]:
        rows = self._conn.execute("SELECT * FROM nodes ORDER BY frequency DESC").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Cluster CRUD
    # ------------------------------------------------------------------

    def upsert_cluster(self, cluster_id: str, centroid: list, representative: str, member_count: int):
        self._conn.execute(
            """INSERT INTO clusters (cluster_id, centroid_json, representative, member_count)
               VALUES (?,?,?,?)
               ON CONFLICT(cluster_id) DO UPDATE SET
                 centroid_json=excluded.centroid_json,
                 member_count=excluded.member_count""",
            (cluster_id, json.dumps(centroid), representative, member_count),
        )
        self._conn.commit()

    def all_clusters(self) -> List[dict]:
        rows = self._conn.execute("SELECT * FROM clusters").fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        rows = self.all_prompts()
        if not rows:
            return {
                "total_prompts": 0,
                "total_original_bytes": 0,
                "total_compressed_bytes": 0,
                "overall_compression_ratio": 0.0,
                "overall_space_savings_pct": 0.0,
                "unique_nodes": 0,
                "num_clusters": 0,
            }
        total_orig = sum(r.original_size for r in rows)
        total_comp = sum(r.compressed_size for r in rows)
        return {
            "total_prompts": len(rows),
            "total_original_bytes": total_orig,
            "total_compressed_bytes": total_comp,
            "overall_compression_ratio": total_orig / total_comp if total_comp else 0.0,
            "overall_space_savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0.0,
            "unique_nodes": self._conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0],
            "num_clusters": self._conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0],
        }

    # ------------------------------------------------------------------
    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
