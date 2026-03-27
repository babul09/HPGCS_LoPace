import gzip
import brotli
import zstandard as zstd
import time
from typing import List, Dict, Tuple, Optional, Any

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore
from lopace.delta_store import DeltaStore
from lopace.adaptive_store import AdaptiveStore

try:
    _ZSTD = True
except ImportError:
    _ZSTD = False

# ─── Baseline Methods ─────────────────────────────────────────────────────────

def baseline_zstd(prompts: List[str], level: int = 15) -> Dict:
    """Per-prompt Zstd compression."""
    cctx = zstd.ZstdCompressor(level=level)
    total_orig = 0
    total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        total_orig += len(raw)
        total_comp += len(cctx.compress(raw))
    return {
        "method": "per_prompt_zstd",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "ratio": total_orig / total_comp if total_comp else 0,
        "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0,
    }

def baseline_gzip(prompts: List[str], level: int = 9) -> Dict:
    total_orig = total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        total_orig += len(raw)
        total_comp += len(gzip.compress(raw, compresslevel=level))
    return {"method": "per_prompt_gzip", "total_original": total_orig, "total_compressed": total_comp, "ratio": total_orig / total_comp if total_comp else 0, "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0}

def baseline_brotli(prompts: List[str], quality: int = 11) -> Dict:
    total_orig = total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        total_orig += len(raw)
        total_comp += len(brotli.compress(raw, quality=quality))
    return {"method": "per_prompt_brotli", "total_original": total_orig, "total_compressed": total_comp, "ratio": total_orig / total_comp if total_comp else 0, "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0}


def baseline_zstd_dictionary(prompts: List[str], level: int = 15,
                              dict_size: int = 131072,
                              train_fraction: float = 0.1) -> Dict:
    """
    Zstd with dictionary training — the base paper's #1 recommended future work.

    Trains a compression dictionary on a fraction of the corpus,
    then compresses all prompts using it.
    """
    if not _ZSTD:
        return {"method": "zstd_dictionary", "error": "zstd not available"}

    # Split into training and test (but compress ALL with the dictionary)
    n_train = max(10, int(len(prompts) * train_fraction))
    train_samples = [p.encode("utf-8") for p in prompts[:n_train]]

    # Train dictionary
    try:
        dictionary = zstd.train_dictionary(dict_size, train_samples)
    except Exception as e:
        return {"method": "zstd_dictionary", "error": str(e)}

    cctx = zstd.ZstdCompressor(level=level, dict_data=dictionary)
    dctx = zstd.ZstdDecompressor(dict_data=dictionary)

    total_orig = 0
    total_comp = 0
    dict_overhead = dict_size  # dictionary must be stored/transmitted

    for text in prompts:
        raw = text.encode("utf-8")
        compressed = cctx.compress(raw)
        # Verify lossless
        assert dctx.decompress(compressed) == raw
        total_orig += len(raw)
        total_comp += len(compressed)

    total_with_dict = total_comp + dict_overhead

    return {
        "method": "zstd_dictionary",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "total_with_dict_overhead": total_with_dict,
        "dictionary_size": dict_overhead,
        "ratio_without_dict": total_orig / total_comp if total_comp else 0,
        "ratio_with_dict": total_orig / total_with_dict if total_with_dict else 0,
        "savings_pct": (1 - total_with_dict / total_orig) * 100 if total_orig else 0,
        "train_samples": n_train,
    }


def baseline_hybrid(prompts: List[str], level: int = 15) -> Dict:
    """Per-prompt BPE + Zstd (base paper's hybrid method)."""
    try:
        from legacy.lopace_graph.tokenizer_module import ResidualTextTokenizer
        from legacy.lopace_graph.encoder import LearnedCompressionEncoder
    except ImportError as e:
        return {"method": "per_prompt_hybrid", "error": f"modules not available: {e}"}

    tokenizer = ResidualTextTokenizer(model="cl100k_base")
    encoder = LearnedCompressionEncoder(zstd_level=level, base_compressor="zstd")

    total_orig = 0
    total_comp = 0
    for text in prompts:
        raw = text.encode("utf-8")
        token_ids = tokenizer.tokenize(text)
        packed = tokenizer.pack(token_ids)
        blob, _ = encoder.encode(packed, token_ids)
        total_orig += len(raw)
        total_comp += len(blob)

    return {
        "method": "per_prompt_hybrid",
        "total_original": total_orig,
        "total_compressed": total_comp,
        "ratio": total_orig / total_comp if total_comp else 0,
        "savings_pct": (1 - total_comp / total_orig) * 100 if total_orig else 0,
    }


def corpus_dedup_method(prompts: List[str], level: int = 15) -> Dict:
    """Corpus-level component deduplication."""
    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    marginal_costs = []
    for i, text in enumerate(prompts):
        segments = parser.parse_segments(text)
        result = store.store(f"P{i:06d}", text, segments)
        marginal_costs.append(result["marginal_bytes"])

        # Verify every 100th prompt
        if i % 100 == 0:
            rebuilt, v = store.retrieve(f"P{i:06d}")
            assert v["exact_match"], f"Reconstruction failed at prompt {i}"

    stats = store.corpus_stats()
    store.close()

    return {
        "method": "corpus_dedup",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["corpus_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "unique_nodes": stats["n_unique_nodes"],
        "avg_reuse": stats["avg_refs_per_node"],
        "marginal_costs": marginal_costs,
    }


def corpus_dedup_chunked(prompts: List[str], level: int = 15,
                          min_chunk: int = 128, max_chunk: int = 2048) -> Dict:
    """Corpus-level dedup with sub-component chunking."""
    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)

    marginal_costs = []
    for i, text in enumerate(prompts):
        segments = parser.parse_segments_chunked(
            text, min_chunk_bytes=min_chunk, max_chunk_bytes=max_chunk
        )
        result = store.store(f"P{i:06d}", text, segments)
        marginal_costs.append(result["marginal_bytes"])

        if i % 500 == 0:
            rebuilt, v = store.retrieve(f"P{i:06d}")
            assert v["exact_match"], f"Reconstruction failed at prompt {i}"

    stats = store.corpus_stats()
    store.close()

    return {
        "method": "corpus_dedup_chunked",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["corpus_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "unique_nodes": stats["n_unique_nodes"],
        "avg_reuse": stats["avg_refs_per_node"],
        "marginal_costs": marginal_costs,
        "chunk_config": {"min": min_chunk, "max": max_chunk},
    }

def delta_compression_method(prompts: List[str], level: int = 15,
                              similarity_threshold: float = 0.4,
                              sample_centroids: int = 20) -> Dict:
    """Delta compression against cluster centroids."""
    from lopace.delta_store import DeltaStore

    store = DeltaStore(
        db_path=":memory:",
        zstd_level=level,
        similarity_threshold=similarity_threshold,
        sample_centroids=sample_centroids,
    )

    for i, text in enumerate(prompts):
        result = store.store(f"P{i:06d}", text)

        # Verify every 200th prompt
        if i % 200 == 0:
            rebuilt, v = store.retrieve(f"P{i:06d}")
            assert v["exact_match"], f"Delta reconstruction failed at prompt {i}: mode={v.get('storage_mode')}"
        
        # Progress for large datasets
        if (i + 1) % 1000 == 0:
            print(f"\r    Processing {i+1}/{len(prompts)}...", end="", flush=True)

    if len(prompts) > 1000:
        print()

    stats = store.corpus_stats()
    store.close()

    return {
        "method": "delta_compression",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["total_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "n_centroids": stats["n_centroids"],
        "n_deltas": stats["n_deltas"],
        "delta_fraction": stats["delta_fraction"],
        "avg_delta_similarity": stats["avg_delta_similarity"],
    }

def adaptive_routing_method(prompts: List[str], level: int = 15) -> Dict:
    """Dynamically route to Monolithic, Corpus Dedup, or Delta based on heuristics."""
    from lopace.adaptive_store import AdaptiveStore
    import time
    
    store = AdaptiveStore(db_path=":memory:", zstd_level=level)

    t0 = time.time()
    strategies = {}
    
    for i, text in enumerate(prompts):
        result = store.store(f"P{i:06d}", text)
        strat = result.get("strategy", result.get("storage_mode", "unknown"))
        strategies[strat] = strategies.get(strat, 0) + 1
        
        # Progress for large datasets
        if (i + 1) % 1000 == 0:
            print(f"\r    Processing Adaptive {i+1}/{len(prompts)}...", end="", flush=True)

    if len(prompts) > 1000:
        print()

    stats = store.stats()
    store.close()

    elapsed = time.time() - t0
    
    n_delta = strategies.get("delta", 0)
    n_centroid = strategies.get("centroid", 0) + strategies.get("new_centroid", 0)
    n_dedup = strategies.get("corpus_dedup", 0)
    n_mono = strategies.get("monolithic", 0)

    return {
        "method": "adaptive_routing",
        "total_original": stats["total_original_bytes"],
        "total_compressed": stats["total_stored_bytes"],
        "ratio": stats["corpus_compression_ratio"],
        "savings_pct": stats["corpus_space_savings_pct"],
        "n_delta": n_delta,
        "n_centroid": n_centroid,
        "n_dedup": n_dedup,
        "n_mono": n_mono,
        "time_s": elapsed,
    }


