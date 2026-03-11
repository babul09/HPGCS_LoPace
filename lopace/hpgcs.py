"""
Hybrid Prompt Graph Compression System (HPGCS) - Main Pipeline Orchestrator

Combines all nine modules into a single coherent compression / decompression
pipeline as described in the HPGCS prototype specification.

Pipeline (compression)
----------------------
Prompt Input
     ↓  PromptParser
Prompt Graph Decomposer
     ↓  ReusableNodeManager
Vector Similarity Clustering
     ↓  ResidualTextTokenizer
Learned Compression Encoder
     ↓  Zstandard Compression
Graph Storage Database

Pipeline (decompression / reconstruction)
-----------------------------------------
Load Graph Representation
     ↓  Decompress Data
Decode Latent Vector
     ↓  Reconstruct Token Sequence
Rebuild Original Prompt
"""

import json
import time
import uuid
import hashlib
from typing import Dict, List, Optional, Tuple, Any

from .parser import PromptParser
from .graph import PromptGraphDecomposer, ReusableNodeManager
from .clustering import VectorSimilarityClusterer
from .tokenizer_module import ResidualTextTokenizer
from .encoder import LearnedCompressionEncoder
from .storage import GraphStorageDatabase, PromptRecord
from .reconstruction import PromptReconstructionEngine


class HPGCS:
    """
    Hybrid Prompt Graph Compression System.

    A multi-layer prompt compression pipeline that combines:
      • Structural graph decomposition
      • Reusable node deduplication
      • Semantic vector clustering
      • BPE residual tokenization
      • Zstandard entropy compression

    Args:
        db_path:              SQLite database path (":memory:" for in-memory).
        tokenizer_model:      tiktoken encoding name (default: "cl100k_base").
        zstd_level:           Zstandard compression level 1–22 (default: 15).
        cluster_threshold:    Cosine similarity threshold for clustering (default: 0.80).
        sentence_transformer: Model name for semantic embeddings
                              (None = use n-gram fallback).
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        tokenizer_model: str = "cl100k_base",
        zstd_level: int = 15,
        cluster_threshold: float = 0.80,
        sentence_transformer: Optional[str] = None,
    ):
        # Module 1 – Prompt Parser
        self.parser = PromptParser()

        # Modules 2 & 3 – Graph Decomposer + Reusable Node Manager
        self.node_manager = ReusableNodeManager()
        self.decomposer = PromptGraphDecomposer(self.node_manager)

        # Module 4 – Clustering
        self.clusterer = VectorSimilarityClusterer(
            model_name=sentence_transformer or VectorSimilarityClusterer.DEFAULT_MODEL,
            threshold=cluster_threshold,
            use_sentence_transformers=(sentence_transformer is not None),
        )

        # Module 5 – Tokenizer
        self.tokenizer = ResidualTextTokenizer(model=tokenizer_model)

        # Module 6 – Encoder + Zstd
        self.encoder = LearnedCompressionEncoder(zstd_level=zstd_level)

        # Module 7 – Graph Storage Database
        self.db = GraphStorageDatabase(db_path=db_path)

        # Module 8 – Reconstruction Engine
        self.reconstructor = PromptReconstructionEngine(
            self.node_manager, self.tokenizer, self.encoder
        )

        # Configuration snapshot
        self.config = {
            "db_path": db_path,
            "tokenizer_model": tokenizer_model,
            "zstd_level": zstd_level,
            "cluster_threshold": cluster_threshold,
            "clustering_backend": self.clusterer.backend,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Compression
    # ──────────────────────────────────────────────────────────────────────

    def compress(self, text: str, prompt_id: Optional[str] = None) -> dict:
        """
        Compress a single prompt through the full HPGCS pipeline.

        Args:
            text:      Raw prompt string.
            prompt_id: Optional stable ID; one is generated if not provided.

        Returns:
            Result dict containing metrics and the prompt_id for later
            retrieval / reconstruction.
        """
        t_start = time.perf_counter()

        if not prompt_id:
            prompt_id = str(uuid.uuid4())[:8].upper()

        original_size = len(text.encode("utf-8"))

        # ── Stage 1: Parse ────────────────────────────────────────────────
        parsed = self.parser.parse(text)

        # ── Stage 2 & 3: Graph decomposition + node deduplication ─────────
        prompt_graph = self.decomposer.decompose(parsed, prompt_id)

        # ── Stage 4: Vector similarity clustering ─────────────────────────
        cluster_id, cluster_sim = self.clusterer.assign(prompt_id, text)

        # ── Stage 5: Tokenize residual text ───────────────────────────────
        # "Residual" = the full prompt text (after node deduplication the
        # graph stores node IDs; residual content is what must be encoded).
        token_ids = self.tokenizer.tokenize(text)
        packed_tokens = self.tokenizer.pack(token_ids)

        # ── Stage 6 & 7: Encode + Zstd compress ──────────────────────────
        compressed_blob, latent_bytes = self.encoder.encode(packed_tokens, token_ids)

        compressed_size = len(compressed_blob)
        t_compress = time.perf_counter() - t_start

        # ── Stage 8: Store in graph database ──────────────────────────────
        record = PromptRecord(
            prompt_id=prompt_id,
            original_text=text,
            graph_json=json.dumps(prompt_graph.to_dict()),
            cluster_id=cluster_id,
            compressed_blob=compressed_blob,
            latent_bytes=latent_bytes,
            original_size=original_size,
            compressed_size=compressed_size,
            created_at=time.time(),
        )
        self.db.insert_prompt(record)

        # Persist node registry & cluster info
        self.db.upsert_nodes([n.to_dict() for n in self.node_manager.all_nodes()])
        cluster_obj = self.clusterer.get_cluster(cluster_id)
        if cluster_obj:
            self.db.upsert_cluster(
                cluster_id,
                cluster_obj.centroid,
                cluster_obj.representative_text,
                len(cluster_obj.member_ids),
            )

        return {
            "prompt_id": prompt_id,
            "original_size_bytes": original_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": original_size / compressed_size if compressed_size else 0.0,
            "space_savings_pct": (1 - compressed_size / original_size) * 100 if original_size else 0.0,
            "compression_time_s": t_compress,
            "graph_path": prompt_graph.path_string(),
            "node_count": len(prompt_graph.node_ids),
            "cluster_id": cluster_id,
            "cluster_similarity": cluster_sim,
            "token_count": len(token_ids),
            "packed_size_bytes": len(packed_tokens),
            "components": parsed.component_list(),
            "has_structure": parsed.has_structure,
        }

    def compress_batch(self, texts: List[str]) -> List[dict]:
        """Compress a list of prompts."""
        return [self.compress(t) for t in texts]

    # ──────────────────────────────────────────────────────────────────────
    # Reconstruction
    # ──────────────────────────────────────────────────────────────────────

    def reconstruct(self, prompt_id: str) -> Tuple[Optional[str], dict]:
        """
        Reconstruct the original prompt from the database.

        Returns:
            (reconstructed_text, verification_dict)
        """
        t0 = time.perf_counter()
        text, verification = self.reconstructor.reconstruct_from_db(prompt_id, self.db)
        verification["total_reconstruction_time_s"] = time.perf_counter() - t0
        return text, verification

    def compress_and_reconstruct(self, text: str) -> dict:
        """
        Compress a prompt and immediately reconstruct it.
        Returns a combined result dict with all metrics.
        """
        compress_result = self.compress(text)
        pid = compress_result["prompt_id"]

        t0 = time.perf_counter()
        rebuilt, verification = self.reconstruct(pid)
        decomp_time = time.perf_counter() - t0

        return {
            **compress_result,
            "reconstructed_text": rebuilt,
            "exact_match": verification.get("exact_match", False),
            "hash_match": verification.get("hash_match", False),
            "original_hash": verification.get("original_hash", ""),
            "rebuilt_hash": verification.get("rebuilt_hash", ""),
            "decompression_time_s": decomp_time,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Analytics
    # ──────────────────────────────────────────────────────────────────────

    def database_stats(self) -> dict:
        """Return aggregate statistics about the compressed dataset."""
        db_stats = self.db.stats()
        if db_stats["total_prompts"]:
            from .graph import PromptGraph
            graphs = [
                PromptGraph.from_dict(json.loads(r.graph_json))
                for r in self.db.all_prompts()
            ]
            graph_summary = self.decomposer.graph_summary(graphs)
        else:
            graph_summary = {}
        cluster_summary = self.clusterer.summary()

        return {
            **db_stats,
            **{f"graph_{k}": v for k, v in graph_summary.items()},
            **{f"cluster_{k}": v for k, v in cluster_summary.items()},
        }

    def list_prompts(self) -> List[dict]:
        """Return summary rows for all stored prompts."""
        return [r.to_dict() for r in self.db.all_prompts()]

    def list_nodes(self) -> List[dict]:
        """Return all reusable nodes from the database."""
        return self.db.all_nodes()

    def list_clusters(self) -> List[dict]:
        """Return cluster info from the database."""
        return self.db.all_clusters()

    # ──────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────

    def clear(self):
        """Reset the entire system (database + in-memory state)."""
        self.db = GraphStorageDatabase(db_path=self.config["db_path"])
        self.node_manager = ReusableNodeManager()
        self.decomposer = PromptGraphDecomposer(self.node_manager)
        self.clusterer = VectorSimilarityClusterer(
            threshold=self.config["cluster_threshold"]
        )
        self.reconstructor = PromptReconstructionEngine(
            self.node_manager, self.tokenizer, self.encoder
        )

    def __repr__(self) -> str:
        stats = self.db.stats()
        return (
            f"HPGCS(prompts={stats['total_prompts']}, "
            f"nodes={stats['unique_nodes']}, "
            f"clusters={stats['num_clusters']})"
        )
