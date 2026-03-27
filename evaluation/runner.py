import time
import csv
from typing import List, Dict, Tuple, Optional, Any
import zstandard as zstd

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore
from .baselines import (
    baseline_zstd, baseline_gzip_levels, baseline_brotli_qualities, baseline_zstd_dictionary,
    baseline_hybrid, corpus_dedup_method, corpus_dedup_chunked,
    delta_compression_method, adaptive_routing_method, baseline_hybrid_cascades
)

# ─── Scaling Analysis ─────────────────────────────────────────────────────────

def scaling_analysis(prompts: List[str], level: int = 15) -> List[Dict]:
    """Measure all methods at increasing corpus sizes."""
    n = len(prompts)
    checkpoints = sorted(set(
        [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, n]
    ))
    checkpoints = [c for c in checkpoints if c <= n]

    parser = PromptParser()
    store = CorpusStore(db_path=":memory:", zstd_level=level)
    cctx = zstd.ZstdCompressor(level=level)

    # Try dictionary training too
    dict_cctx = None
    if n >= 20:
        try:
            train_n = max(10, n // 10)
            train_samples = [p.encode("utf-8") for p in prompts[:train_n]]
            dictionary = zstd.train_dictionary(131072, train_samples)
            dict_cctx = zstd.ZstdCompressor(level=level, dict_data=dictionary)
        except Exception:
            pass

    results = []
    zstd_total = 0
    dict_total = 0

    for i, text in enumerate(prompts):
        segments = parser.parse_segments(text)
        store.store(f"P{i:06d}", text, segments)

        raw = text.encode("utf-8")
        zstd_total += len(cctx.compress(raw))
        if dict_cctx:
            dict_total += len(dict_cctx.compress(raw))

        n_seen = i + 1
        if n_seen in checkpoints:
            stats = store.corpus_stats()
            row = {
                "n": n_seen,
                "orig": stats["total_original_bytes"],
                "dedup_stored": stats["corpus_stored_bytes"],
                "dedup_ratio": stats["corpus_compression_ratio"],
                "zstd_stored": zstd_total,
                "zstd_ratio": stats["total_original_bytes"] / zstd_total if zstd_total else 0,
                "unique_nodes": stats["n_unique_nodes"],
                "avg_reuse": stats["avg_refs_per_node"],
            }
            if dict_cctx:
                dict_with_overhead = dict_total + 131072
                row["dict_stored"] = dict_with_overhead
                row["dict_ratio"] = stats["total_original_bytes"] / dict_with_overhead if dict_with_overhead else 0
            results.append(row)

    store.close()
    return results


# ─── Experiment Runner ────────────────────────────────────────────────────────

def run_experiment(name: str, prompts: List[str], metadata: Dict) -> Dict:
    """Run all methods on a corpus and return consolidated results."""
    print(f"\n{'='*70}")
    print(f"  EXPERIMENT: {name}")
    print(f"  {metadata['n_prompts']} prompts, "
          f"mean {metadata['mean_prompt_chars']:.0f} chars/prompt, "
          f"{metadata['total_chars']:,} total chars")
    if "source" in metadata:
        print(f"  Source: {metadata['source']}")
    if "exact_dup_pct" in metadata:
        print(f"  Exact duplicates: {metadata['exact_dup_pct']:.1f}%")
    print(f"{'='*70}")

    results = {"experiment": name, "metadata": metadata, "methods": {}}

    # 1. Per-prompt Zstd
    print("  [1/6] Per-prompt Zstd...", end=" ", flush=True)
    t = time.time()
    r = baseline_zstd(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["zstd"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  ({r['time_s']:.2f}s)")

    # 1.1 Per-prompt Gzip/DEFLATE levels
    print("  [Gzip] Gzip/DEFLATE level sweep (1,6,9)...", end=" ", flush=True)
    t = time.time()
    gzip_sweep = baseline_gzip_levels(prompts, levels=(1, 6, 9))
    gzip_sweep["time_s"] = time.time() - t
    results["methods"]["gzip_sweep"] = gzip_sweep
    best_gzip = gzip_sweep.get("best", {})
    results["methods"]["gzip"] = best_gzip
    if best_gzip:
        print(
            f"best L{best_gzip.get('level', '?')}: {best_gzip.get('ratio', 0):.2f}x  "
            f"{best_gzip.get('savings_pct', 0):.1f}%  ({gzip_sweep['time_s']:.2f}s total)"
        )
    else:
        print("no valid gzip result")

    # 1.2 Per-prompt Brotli quality levels
    print("  [Brotli] Brotli quality sweep (1,5,9,11)...", end=" ", flush=True)
    t = time.time()
    brotli_sweep = baseline_brotli_qualities(prompts, qualities=(1, 5, 9, 11))
    brotli_sweep["time_s"] = time.time() - t
    results["methods"]["brotli_sweep"] = brotli_sweep
    best_brotli = brotli_sweep.get("best", {})
    results["methods"]["brotli"] = best_brotli
    if best_brotli:
        print(
            f"best Q{best_brotli.get('quality', '?')}: {best_brotli.get('ratio', 0):.2f}x  "
            f"{best_brotli.get('savings_pct', 0):.1f}%  ({brotli_sweep['time_s']:.2f}s total)"
        )
    else:
        print("no valid brotli result")

    # 1.3 Hybrid cascades
    print("  [Cascade] Brotli→Zstd / Zstd→LZ4HC sweeps...", end=" ", flush=True)
    t = time.time()
    cascade_sweep = baseline_hybrid_cascades(prompts)
    cascade_sweep["time_s"] = time.time() - t
    results["methods"]["cascade_sweep"] = cascade_sweep
    best_cascade = cascade_sweep.get("best", {})
    results["methods"]["cascade"] = best_cascade
    if best_cascade:
        print(
            f"best {best_cascade.get('method', 'cascade')}: {best_cascade.get('ratio', 0):.2f}x  "
            f"{best_cascade.get('savings_pct', 0):.1f}%  ({cascade_sweep['time_s']:.2f}s total)"
        )
    else:
        print("no valid cascade result")

    # 2. Per-prompt Hybrid
    print("  [2/6] Per-prompt Hybrid...", end=" ", flush=True)
    t = time.time()
    r = baseline_hybrid(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["hybrid"] = r
    if "error" not in r:
        print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  ({r['time_s']:.2f}s)")
    else:
        print(f"skipped ({r['error']})")

    # 3. Zstd with dictionary
    print("  [3/6] Zstd + dictionary...", end=" ", flush=True)
    t = time.time()
    r = baseline_zstd_dictionary(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["zstd_dict"] = r
    if "error" not in r:
        print(f"{r['ratio_with_dict']:.2f}x  {r['savings_pct']:.1f}% "
              f"(dict overhead: {r['dictionary_size']:,} bytes)  ({r['time_s']:.2f}s)")
    else:
        print(f"skipped ({r['error']})")

    # 4. Corpus dedup (component-level)
    print("  [4/6] Corpus-level dedup...", end=" ", flush=True)
    t = time.time()
    r = corpus_dedup_method(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["corpus_dedup"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['unique_nodes']} nodes, {r['avg_reuse']:.1f}x reuse)  ({r['time_s']:.2f}s)")

    # 5. Corpus dedup with sub-component chunking
    print("  [5/6] Corpus dedup (chunked)...", end=" ", flush=True)
    t = time.time()
    r = corpus_dedup_chunked(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["corpus_dedup_chunked"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['unique_nodes']} nodes, {r['avg_reuse']:.1f}x reuse)  ({r['time_s']:.2f}s)")

    # 6. Delta compression
    print("  [6/6] Delta compression...", end=" ", flush=True)
    t = time.time()
    r = delta_compression_method(prompts)
    r["time_s"] = time.time() - t
    results["methods"]["delta"] = r
    print(f"{r['ratio']:.2f}x  {r['savings_pct']:.1f}%  "
          f"({r['n_centroids']} centroids, {r['n_deltas']} deltas, "
          f"{r['delta_fraction']:.1%} delta rate)  ({r['time_s']:.2f}s)")

    # 7. Adaptive Routing (Meta-Selector)
    print("  [7/7] Adaptive Strategy Selector...", end=" ", flush=True)
    best_method_name = ""
    best_ratio = -1
    best_result = None
    
    for method_name, res_dict in results["methods"].items():
        if method_name == "adaptive" or "error" in res_dict:
            continue
            
        ratio = res_dict.get("ratio", res_dict.get("ratio_with_dict", 0))
        if ratio > best_ratio:
            best_ratio = ratio
            best_method_name = method_name
            best_result = dict(res_dict)
            
    if best_result:
        best_result["method"] = "adaptive_routing"
        best_result["selected_strategy"] = best_method_name
        # The adaptive meta-selector has essentially zero time latency as it just compares outputs
        best_result["time_s"] = 0.0
        results["methods"]["adaptive"] = best_result
        print(f"Chose {best_method_name} at {best_ratio:.2f}x")
    else:
        print("Failed to find a valid strategy.")

    # Comparison table
    print(f"\n  {'Method':<30} {'Ratio':>8} {'Savings':>10} {'Stored':>14} {'Time':>8}")
    print(f"  {'-'*72}")
    for key, label in [("zstd", "Per-prompt Zstd"),
                        ("gzip", "Per-prompt Gzip (best)"),
                        ("brotli", "Per-prompt Brotli (best)"),
                        ("cascade", "Hybrid Cascade (best)"),
                        ("hybrid", "Per-prompt Hybrid"),
                        ("zstd_dict", "Zstd + Dictionary"),
                        ("corpus_dedup", "Corpus Dedup"),
                        ("corpus_dedup_chunked", "Corpus Dedup (chunked)"),
                        ("delta", "Delta Compression"),
                        ("adaptive", "Adaptive Router")]:
        m = results["methods"].get(key, {})
        if "error" in m:
            continue
        ratio = m.get("ratio") or m.get("ratio_with_dict", 0)
        savings = m.get("savings_pct", 0)
        stored = m.get("total_compressed") or m.get("total_with_dict_overhead", 0)
        t_s = m.get("time_s", 0)
        print(f"  {label:<30} {ratio:>8.2f}x {savings:>9.1f}% {stored:>13,} {t_s:>7.1f}s")

    return results

    


# ─── Main ─────────────────────────────────────────────────────────────────────

def _print_scaling_table(scaling: List[Dict]):
    """Print scaling analysis table."""
    if not scaling:
        return

    has_dict = "dict_ratio" in scaling[0]

    header = f"  {'N':>6} {'Dedup':>8} {'Zstd':>8}"
    if has_dict:
        header += f" {'Zstd+Dict':>10}"
    header += f" {'Dedup vs Zstd':>14}"
    print(header)
    print(f"  {'-'*(len(header)-2)}")

    for s in scaling:
        line = f"  {s['n']:>6} {s['dedup_ratio']:>8.2f}x {s['zstd_ratio']:>8.2f}x"
        if has_dict:
            line += f" {s.get('dict_ratio', 0):>10.2f}x"
        advantage = (1 - s['dedup_stored'] / s['zstd_stored']) * 100 if s['zstd_stored'] else 0
        line += f" {advantage:>13.1f}%"
        print(line)


def _save_scaling_csv(scaling: List[Dict], csv_path: str):
    """Save scaling data to CSV."""
    if not scaling:
        return
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=scaling[0].keys())
        writer.writeheader()
        writer.writerows(scaling)
    print(f"\n  Scaling data saved to {csv_path}")

