# HPGCS / LoPace — Corpus-Aware Prompt Compression

**Author:** Babul Bishwas ([babul09](https://github.com/babul09))
**Based on:** Original [LoPace](https://github.com/connectaman/LoPace) by Aman Ulla
**Last updated:** 27 March 2026

---

## Overview

HPGCS (Hybrid Prompt Graph Compression System) is a **lossless, corpus-aware prompt compression framework** for LLM prompt workloads. It targets real production scenarios where the same system prompts, tool schemas, and RAG context blocks are repeated across thousands of prompts — exploiting that redundancy to achieve compression ratios far beyond what per-prompt methods can deliver.

### Three Compression Strategies

| Strategy | Module | Best For |
|----------|--------|----------|
| **Per-prompt compression** | `lopace/compressor.py` | Baseline / single-prompt use |
| **Corpus-level deduplication** | `lopace/corpus_store.py` | Corpora with shared components |
| **Delta compression** | `lopace/delta_store.py` | Similar-but-not-identical prompts |

A fourth approach — **Zstd dictionary training** — is available in the benchmark suite (`benchmark_full_evaluation.py`) as a competitive baseline.

---

## Quick Start

```python
from lopace import PromptCompressor, PromptParser, CorpusStore, DeltaStore

# ── Per-prompt compression (baseline) ──
compressor = PromptCompressor(zstd_level=15)
blob = compressor.compress("System: You are helpful.\nUser: Explain entropy.", method="zstd")
text = compressor.decompress(blob, method="zstd")

# ── Corpus-level deduplication ──
parser = PromptParser()
store = CorpusStore(db_path=":memory:", zstd_level=15)

prompts = [
    "System: You are helpful.\nUser: Explain entropy.",
    "System: You are helpful.\nUser: Explain KL divergence.",
]

for i, prompt in enumerate(prompts):
    segments = parser.parse_segments(prompt)
    result = store.store(f"P{i}", prompt, segments)
    print(f"Prompt {i}: marginal={result['marginal_bytes']} bytes")

# Reconstruct losslessly
text, verify = store.retrieve("P0")
assert verify["exact_match"]

# Corpus-wide stats
stats = store.corpus_stats()
print(f"Corpus ratio: {stats['corpus_compression_ratio']:.2f}x")
print(f"Space savings: {stats['corpus_space_savings_pct']:.1f}%")
```

---

## Project Structure

```
lopace/                         # Core Python package
  ├── __init__.py               # Public API
  ├── compressor.py             # Multi-method per-prompt compressor
  ├── parser.py                 # Structural prompt parser
  ├── corpus_store.py           # Corpus-level component deduplication
  └── delta_store.py            # Delta compression (centroid + diffs)

benchmark_corpus_dedup.py       # Corpus dedup vs baselines benchmark
benchmark_full_evaluation.py    # Full evaluation (synthetic + real data)
generate_production_dataset.py  # Synthetic dataset generator

legacy/                         # Archived code (graph pipeline, old UIs)
  ├── lopace_graph/             # HPGCS graph pipeline modules
  ├── notebooks/                # Old Jupyter notebooks
  ├── paper/                    # Old paper assets
  ├── scripts/                  # Old visualization scripts
  └── tests/                    # Old test suite
```

---

## Benchmarking

```bash
# Corpus dedup vs per-prompt Zstd (synthetic data, fast)
python benchmark_corpus_dedup.py --n 1000

# Full evaluation with all baselines including Zstd dictionary training
python benchmark_full_evaluation.py --n 5000

# Real-world dataset evaluation
python benchmark_full_evaluation.py --real-data dataset.json
python benchmark_full_evaluation.py --real-data-dir ./datasets/
```

---

## Key Metrics

### Per-prompt marginal metrics
- `marginal_bytes` — bytes added to corpus for this prompt
- `reused_refs` / `new_refs` — component reuse tracking
- `marginal_ratio` and `marginal_savings_pct`

### Corpus-level metrics
- `corpus_compression_ratio` — total original / total stored
- `corpus_space_savings_pct`
- `n_unique_nodes` and `avg_refs_per_node`
- `storage_overhead_pct` — blueprint overhead

---

## Installation

```bash
pip install -r requirements.txt
```

### Dependencies

| Package | Role |
|---------|------|
| `zstandard` | Primary compression backend |
| `lz4` | Fast compression alternative |
| `brotli` | High-ratio compression |
| `python-snappy` | Ultra-fast compression |
| `tiktoken` | BPE tokenization |
| `networkx` | Graph processing |
| `numpy` | Numerical operations |
| `streamlit` | UI apps (optional) |
| `plotly`, `pandas` | Visualization (optional) |

---

## Methodology

### Corpus-Level Deduplication

1. Parse prompt into lossless segments (`PromptParser.parse_segments`)
2. Content-hash (SHA-256) each referenceable component
3. Store unique components once in `content_nodes` table
4. Store each prompt as a compact reconstruction blueprint
5. Verify lossless recovery via SHA-256 hash matching

### Delta Compression

1. Group prompts by semantic similarity
2. Select cluster centroids as reference points
3. Store deltas (unified diffs) against nearest centroid
4. Compress deltas with Zstd for additional savings
5. Reconstruct by applying delta to decompressed centroid

### Zstd Dictionary Training

- Train a shared Zstd dictionary from corpus samples
- Apply dictionary-assisted compression per prompt
- Evaluated as a competitive baseline in benchmarks

---

## License

MIT — see [LICENSE](LICENSE)

**Original LoPace:** Copyright © 2026 Aman Ulla
**HPGCS extensions:** Copyright © 2026 Babul Bishwas
