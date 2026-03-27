
"""
Full Evaluation: Corpus-Level Dedup vs All Baselines

Produces paper-ready results including:
    Per-prompt Zstd (base paper baseline)
    Per-prompt Hybrid BPE+Zstd (base paper best)
    Zstd with dictionary training (base paper's #1 future work)
    Corpus-level component dedup (proposed method)

Tests across:
    Controlled reuse rates (0%, 10%, 50%, 80%, 100%)
    Corpus sizes (1 to 10,000)
    Realistic vs worst-case scenarios
    Real-world datasets from JSON files

Usage:
    python benchmark_full_evaluation.py
    python benchmark_full_evaluation.py --n 5000
    python benchmark_full_evaluation.py --real-data dataset.json
    python benchmark_full_evaluation.py --real-data dataset.json --json-field prompt
    python benchmark_full_evaluation.py --real-data dataset.json --json-field conversations --nested-field value
    python benchmark_full_evaluation.py --real-data-dir ./datasets/
"""

import argparse
import csv
import glob
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import gzip
import brotli

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    _ZSTD = False

from lopace.parser import PromptParser
from lopace.corpus_store import CorpusStore

from evaluation.data_generators import generate_corpus, generate_zero_reuse_corpus
from evaluation.datasets import load_real_dataset, load_multiple_datasets, analyze_dataset_redundancy
from evaluation.runner import run_experiment, scaling_analysis, _print_scaling_table, _save_scaling_csv

# Legacy compatibility
try:
    import zstandard as zstd
    _ZSTD = True
except ImportError:
    _ZSTD = False

def main():
    ap = argparse.ArgumentParser(
        description="Full HPGCS evaluation with real dataset support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with synthetic data (default)
  python benchmark_full_evaluation.py --n 1000

  # Run with a real JSON dataset
  python benchmark_full_evaluation.py --real-data my_prompts.json

  # Specify which JSON field contains the prompts
  python benchmark_full_evaluation.py --real-data data.json --json-field prompt

  # ShareGPT format with custom value field
  python benchmark_full_evaluation.py --real-data sharegpt.json --json-field conversations --nested-field value

  # Load all JSON files from a directory
  python benchmark_full_evaluation.py --real-data-dir ./datasets/

  # Combine real and synthetic experiments
  python benchmark_full_evaluation.py --real-data data.json --include-synthetic

  # Only analyze dataset redundancy (no compression benchmarks)
  python benchmark_full_evaluation.py --real-data data.json --analyze-only

  # Limit number of prompts from real dataset
  python benchmark_full_evaluation.py --real-data huge_dataset.json --max-prompts 5000
        """
    )
    ap.add_argument("--n", type=int, default=1000,
                    help="Number of synthetic prompts to generate (default: 1000)")
    ap.add_argument("--real-data", type=str, default=None,
                    help="Path to a JSON/JSONL dataset file")
    ap.add_argument("--real-data-dir", type=str, default=None,
                    help="Path to directory containing JSON/JSONL files")
    ap.add_argument("--json-field", type=str, default=None,
                    help="JSON field containing prompt text (auto-detected if omitted)")
    ap.add_argument("--nested-field", type=str, default=None,
                    help="Nested field within list items (e.g., 'value' in ShareGPT)")
    ap.add_argument("--max-prompts", type=int, default=None,
                    help="Maximum number of prompts to load from real dataset")
    ap.add_argument("--include-synthetic", action="store_true",
                    help="Also run synthetic experiments when using --real-data")
    ap.add_argument("--analyze-only", action="store_true",
                    help="Only analyze dataset redundancy, skip compression benchmarks")
    ap.add_argument("--output", type=str, default="evaluation_results.json",
                    help="Output JSON file for results")
    ap.add_argument("--csv", type=str, default="scaling_results.csv",
                    help="Output CSV file for scaling data")
    args = ap.parse_args()

    all_results = []
    is_real_data_mode = args.real_data or args.real_data_dir

    # ═══════════════════════════════════════════════════════════════════
    # REAL DATA EXPERIMENTS
    # ═══════════════════════════════════════════════════════════════════

    if args.real_data:
        # Load the real dataset
        prompts, meta = load_real_dataset(
            args.real_data,
            json_field=args.json_field,
            nested_field=args.nested_field,
            max_prompts=args.max_prompts,
        )

        # Dataset redundancy analysis
        print(f"\n{'='*70}")
        print(f"  DATASET REDUNDANCY ANALYSIS")
        print(f"{'='*70}")

        analysis = analyze_dataset_redundancy(prompts)

        print(f"\n  Exact duplicates: {analysis['exact_duplicate_pct']:.1f}%")
        print(f"  Unique prompts: {analysis['unique_prompts']:,} / {analysis['total_prompts']:,}")

        if analysis['most_duplicated']:
            print(f"\n  Most duplicated prompts:")
            for i, item in enumerate(analysis['most_duplicated'][:5], 1):
                print(f"    {i}. ({item['count']}x) {item['preview']}")

        pl = analysis.get('prefix_sharing', {})
        if pl:
            print(f"\n  Prefix sharing analysis:")
            for key, info in pl.items():
                print(f"    {key}: {info['unique_prefixes']} unique, "
                      f"most common covers {info['most_common_pct']:.1f}% of prompts")

        ll = analysis.get('line_level', {})
        if ll:
            print(f"\n  Line-level reuse: {ll['line_reuse_pct']:.1f}% "
                  f"({ll['total_lines']:,} lines, {ll['unique_lines']:,} unique)")

        if args.analyze_only:
            # Save analysis and exit
            output = {"dataset_analysis": analysis, "metadata": meta}
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2, default=str)
            print(f"\n  Analysis saved to {args.output}")
            return

        # Run compression benchmarks on real data
        dataset_name = Path(args.real_data).stem
        all_results.append(run_experiment(
            f"Real: {dataset_name}", prompts, meta
        ))

        # Also run scaling analysis on real data
        print(f"\n{'='*70}")
        print(f"  SCALING ANALYSIS (Real Data: {dataset_name})")
        print(f"{'='*70}")

        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            csv_path = args.csv.replace('.csv', f'_real_{dataset_name}.csv')
            _save_scaling_csv(scaling, csv_path)

    elif args.real_data_dir:
        # Load from directory
        prompts, meta = load_multiple_datasets(
            args.real_data_dir,
            json_field=args.json_field,
            max_per_file=args.max_prompts,
        )

        if args.analyze_only:
            analysis = analyze_dataset_redundancy(prompts)
            output = {"dataset_analysis": analysis, "metadata": meta}
            with open(args.output, "w") as f:
                json.dump(output, f, indent=2, default=str)
            print(f"\n  Analysis saved to {args.output}")
            return

        dir_name = Path(args.real_data_dir).name
        all_results.append(run_experiment(
            f"Real: {dir_name} (combined)", prompts, meta
        ))

        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            csv_path = args.csv.replace('.csv', f'_real_{dir_name}.csv')
            _save_scaling_csv(scaling, csv_path)

    # ═══════════════════════════════════════════════════════════════════
    # SYNTHETIC EXPERIMENTS (run by default, or with --include-synthetic)
    # ═══════════════════════════════════════════════════════════════════

    if not is_real_data_mode or args.include_synthetic:
        # ── Experiment 1: Standard (80% reuse) ────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=0.8)
        all_results.append(run_experiment("Synthetic: Standard (80% reuse)", prompts, meta))

        # ── Experiment 2: Full reuse (100%) ───────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=1.0)
        all_results.append(run_experiment("Synthetic: Full reuse (100%)", prompts, meta))

        # ── Experiment 3: Low reuse (10%) ─────────────────────────────────
        prompts, meta = generate_corpus(args.n, system_reuse=0.1, n_unique_systems=5)
        all_results.append(run_experiment("Synthetic: Low reuse (10%)", prompts, meta))

        # ── Experiment 4: ZERO reuse (worst case) ─────────────────────────
        prompts, meta = generate_zero_reuse_corpus(args.n)
        all_results.append(run_experiment("Synthetic: Zero reuse (worst case)", prompts, meta))

        # ── Experiment 5: Zero reuse with tools/context ───────────────────
        prompts_long_zero, meta_long_zero = generate_corpus(
            n_prompts=args.n,
            system_reuse=0.0,
            n_unique_systems=args.n,
            include_tools=0.4,
            include_context=0.3,
            tool_reuse=0.0,
            context_reuse=0.0,
            seed=99,
        )
        all_results.append(run_experiment(
            "Synthetic: Zero reuse + tools/context", prompts_long_zero, meta_long_zero
        ))

        # ── Scaling analysis on synthetic data ────────────────────────────
        print(f"\n{'='*70}")
        print(f"  SCALING ANALYSIS (Synthetic)")
        print(f"{'='*70}")

        prompts, _ = generate_corpus(args.n, system_reuse=0.8)
        scaling = scaling_analysis(prompts)
        _print_scaling_table(scaling)

        if args.csv:
            _save_scaling_csv(scaling, args.csv)

    # ═══════════════════════════════════════════════════════════════════
    # SAVE & SUMMARIZE
    # ═══════════════════════════════════════════════════════════════════

    # Remove marginal_costs from JSON (too large)
    for r in all_results:
        for m in r["methods"].values():
            m.pop("marginal_costs", None)

    output = {
        "experiments": all_results,
        "scaling": scaling if 'scaling' in dir() else [],
    }
    with open(args.output, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\n  Full results saved to {args.output}")

    # ── Summary ───────────────────────────────────────────────────────
    print(f"  {'Experiment':<40} {'Zstd':>7} {'Gzip':>7} {'Brotli':>7} {'Dict':>7} {'Dedup':>7} {'Adapt':>7}")
    print(f"  {'-'*88}")
    for r in all_results:
        name = r["experiment"][:40]
        zr = r["methods"].get("zstd", {}).get("ratio", 0)
        gz = r["methods"].get("gzip", {}).get("ratio", 0)
        br = r["methods"].get("brotli", {}).get("ratio", 0)
        dr = r["methods"].get("zstd_dict", {}).get("ratio_with_dict", 0)
        cr = r["methods"].get("corpus_dedup", {}).get("ratio", 0)
        ar = r["methods"].get("adaptive", {}).get("ratio", 0)
        print(f"  {name:<40} {zr:>7.2f}x {gz:>7.2f}x {br:>7.2f}x {dr:>7.2f}x {cr:>7.2f}x {ar:>7.2f}x")

    # If real data was used, print additional comparison
    if is_real_data_mode:
        real_results = [r for r in all_results if r["metadata"].get("dataset_type") == "real"]
        if real_results:
            print(f"\n  {'─'*70}")
            print(f"  REAL DATA HIGHLIGHTS:")
            for r in real_results:
                dedup = r["methods"].get("corpus_dedup", {})
                zstd_r = r["methods"].get("zstd", {})
                if dedup and zstd_r and "ratio" in dedup and "ratio" in zstd_r:
                    improvement = (dedup["ratio"] / zstd_r["ratio"] - 1) * 100
                    print(f"    Corpus dedup achieves {dedup['ratio']:.2f}x compression")
                    print(f"    vs Zstd baseline {zstd_r['ratio']:.2f}x "
                          f"({'+' if improvement >= 0 else ''}{improvement:.1f}% {'better' if improvement >= 0 else 'worse'})")
                    if dedup.get("unique_nodes"):
                        print(f"    Deduplicated to {dedup['unique_nodes']} unique nodes "
                              f"with {dedup.get('avg_reuse', 0):.1f}x average reuse")

if __name__ == "__main__":
    main()