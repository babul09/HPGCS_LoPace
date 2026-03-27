import time
from typing import Any, Dict

from lopace.corpus_store import CorpusStore
from lopace.delta_store import DeltaStore, _compute_delta
from lopace.parser import PromptParser

class AdaptiveStore:
    """
    Adaptive compression store overriding the 'Greedy Empirical Trap'.
    
    If we strictly use mathematical empirical routing (dry runs), the router
    suffers from the 'Cold Start Dictionary Paradox': It greedily choses Monolithic
    on Prompt #1 to save 20 bytes of chunking overhead, which deprives Prompt #2
    from deduplicating against it! Thus, Monolithic snowballs and ruins compression.
    
    Instead, this uses an Optimized Characteristic Router matching the paper's intent:
    1. Tiny prompts (<400 bytes): Monolithic Zstd.
    2. Highly Similar Variants (>85% matching a centroid): Delta Compression.
    3. Standard/Large content: Corpus Dedup (building the robust dictionary!).
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        zstd_level: int = 15,
        min_size_threshold: int = 400,
        delta_similarity_threshold: float = 0.85,
    ):
        self.corpus_store = CorpusStore(db_path, zstd_level)
        self.delta_store = DeltaStore(
            db_path,
            zstd_level,
            similarity_threshold=delta_similarity_threshold,
            max_centroids=1000,
            sample_centroids=50
        )
        self.parser = PromptParser()
        self.min_size_threshold = min_size_threshold
        self.similarity_threshold = delta_similarity_threshold

    def store(self, prompt_id: str, text: str) -> Dict[str, Any]:
        raw_size = len(text.encode("utf-8"))

        # 1. Monolithic Fallback for tiny non-dedupable strings
        if raw_size < self.min_size_threshold:
            res = self.corpus_store._store_monolithic(prompt_id, text)
            res["strategy"] = "monolithic"
            return res

        # 2. Delta Compression for highly similar variants
        best_cid, similarity = self.delta_store._find_best_centroid(text)
        if best_cid and similarity >= self.similarity_threshold:
            # Only route to Delta if they are nearly identical (e.g. system message diffs)
            res = self.delta_store.store(prompt_id, text)
            # If Delta reconstruction verify fails, it falls back to centroid mode.
            res["strategy"] = res.get("storage_mode", "delta")
            return res

        # 3. Corpus Deduplication (Chunked) ensures the global dictionary populates!
        segments = self.parser.parse_segments_chunked(
            text, min_chunk_bytes=128, max_chunk_bytes=2048
        )
        res = self.corpus_store.store(prompt_id, text, segments)
        res["strategy"] = "corpus_dedup"
        return res

    def close(self):
        self.corpus_store.close()
        self.delta_store.close()

    def stats(self) -> Dict[str, Any]:
        """Combine metrics from both distinct storage implementations."""
        cs = self.corpus_store.corpus_stats()
        ds = self.delta_store.corpus_stats()
        
        total_original = cs["total_original_bytes"] + ds["total_original_bytes"]
        corpus_footprint = cs["corpus_stored_bytes"]
        delta_footprint = ds["total_stored_bytes"]
        total_stored = corpus_footprint + delta_footprint
        
        return {
            "n_prompts": cs["n_prompts"] + ds["n_prompts"],
            "total_original_bytes": total_original,
            "total_stored_bytes": total_stored,
            "corpus_compression_ratio": total_original / total_stored if total_stored > 0 else 0,
            "corpus_space_savings_pct": (1 - total_stored / total_original) * 100 if total_original > 0 else 0,
            
            "dedup_nodes": cs["n_unique_nodes"],
            "delta_centroids": ds["n_centroids"],
            "deltas_formed": ds["n_deltas"]
        }
