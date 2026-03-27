# HPGCS Benchmark Lab — Corpus-Aware Prompt Compression

**Author:** Babul Bishwas ([babul09](https://github.com/babul09))
**Based on:** Original [LoPace](https://github.com/connectaman/LoPace) by Aman Ulla
**Last updated:** 28 March 2026

---

## Overview

HPGCS (Hybrid Prompt Graph Compression System) is a **lossless, corpus-aware prompt compression framework** for LLM prompt workloads.

The core objective is to evaluate compression on prompt corpora where reusable structures (system prompts, tool schemas, contextual templates) appear repeatedly, and to compare corpus-aware methods against strong per-prompt baselines under controlled and real-data conditions.

This repository now serves as both a compression framework and a reproducible benchmark lab for cross-method evaluation.

### Active Compression Tracks

| Track | Module | Purpose |
|---|---|---|
| Per-prompt compression | `lopace/compressor.py` | Single-prompt and baseline methods |
| Corpus-level deduplication | `lopace/corpus_store.py` | Content-addressable reuse across corpora |
| Delta compression | `lopace/delta_store.py` | Diff-based storage vs centroids |

### Comprehensive Baseline Suite (Current)

`benchmark_full_evaluation.py` evaluates:

- Per-prompt Zstd
- gzip/DEFLATE sweep (`L1`, `L6`, `L9`)
- Brotli quality sweep (`Q1`, `Q5`, `Q9`, `Q11`)
- Hybrid cascades (`Brotli→Zstd`, `Zstd→LZ4HC` variants)
- Per-prompt Hybrid (BPE + Zstd)
- Zstd dictionary training (with and without dictionary-overhead views)
- Corpus Dedup (standard + chunked)
- Delta compression
- Adaptive strategy selector (best method by measured ratio)

### Latest Techniques in Use

- **Quality/level sweeps** for Brotli and gzip/DEFLATE to avoid single-point baseline bias.
- **Hybrid cascades** to test sequential compression pipelines (`Brotli→Zstd`, `Zstd→LZ4HC`).
- **Adaptive router** that selects the empirically best method for each experiment.
- **Dictionary dual reporting** (`with overhead` vs `without overhead`) for deployment-realistic interpretation.
- **File-driven benchmark frontend** that parses stored result JSON files and supports experiment/run-type filtering.
- **Real-data scaling by prompt caps** (`200`, `1000`, `2000`, `5000`) for controlled growth analysis.

---

## Installation

```bash
pip install -r requirements.txt
```

Frontend:

```bash
cd frontend
npm install
```

---

## Quick Start (Python API)

```python
from lopace import PromptCompressor, PromptParser, CorpusStore

compressor = PromptCompressor(zstd_level=15)
blob = compressor.compress("System: You are helpful.\nUser: Explain entropy.", method="zstd")
text = compressor.decompress(blob, method="zstd")

parser = PromptParser()
store = CorpusStore(db_path=":memory:", zstd_level=15)

prompt = "System: You are helpful.\nUser: Explain KL divergence."
segments = parser.parse_segments(prompt)
result = store.store("P0", prompt, segments)
rebuilt, verify = store.retrieve("P0")

assert verify["exact_match"]
print(result["marginal_bytes"], store.corpus_stats()["corpus_compression_ratio"])
```

---

## Running Benchmarks

### Synthetic Benchmark Suite

```bash
python benchmark_full_evaluation.py --n 5000 --output evaluation_results.json --csv scaling_results.csv
```

### Real Dataset Benchmark

```bash
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 1000 --output benchmark_results.json --csv scaling_results_real.csv
```

### Real Dataset Prompt-Cap Series (Recommended)

```bash
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 200  --output research_real_200.json  --csv research_real_scaling_200.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 1000 --output research_real_1000.json --csv research_real_scaling_1000.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 2000 --output research_real_2000.json --csv research_real_scaling_2000.csv
python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 5000 --output research_real_5000.json --csv research_real_scaling_5000.csv
```

### Combined Real + Synthetic (research-friendly)

```bash
python benchmark_full_evaluation.py \
  --real-data datasets/eval_results.json \
  --max-prompts 200 \
  --include-synthetic \
  --n 100 \
  --output research_results_2026_03_28.json \
  --csv research_scaling_2026_03_28.csv
```

This command also writes a real-data scaling CSV:

- `research_scaling_2026_03_28_real_eval_results.csv`

For a full research summary generated from these artifacts, see:

- `RESEARCH_RESULTS_2026_03_28.md`

---

## Frontend / API

### Start API

```bash
python -m uvicorn serve_api:app --host 0.0.0.0 --port 8000 --reload
```

### Start Frontend

```bash
cd frontend
npm run dev
```

Dev port is pinned to `5174`.

### File-driven Benchmark View

The Benchmarks page loads result JSON files via:

- `GET /api/benchmark-results?path=<json_file>`

You can select:

- run type (`all`, `synthetic`, `real`)
- specific experiment
- dictionary metric view (`with overhead` vs `without overhead`)

This lets you compare experiments produced in separate runs (for example, different real-data prompt caps) without modifying code.

---

## Metrics Interpretation

- `ratio = total_original / total_stored`
- `savings_pct = (1 - total_stored / total_original) * 100`
- Dictionary mode reports both:
  - `ratio_without_dict` (raw compression only)
  - `ratio_with_dict` (includes dictionary payload)

Negative dictionary savings can occur when dictionary overhead is larger than gains (common on small or low-reuse samples).

---

## Repository Structure

```text
lopace/                         # Active compression package
evaluation/                     # Benchmark methods and runners
benchmark_full_evaluation.py    # Main end-to-end evaluation script
serve_api.py                    # FastAPI backend for demo/benchmarks UI
frontend/                       # React + Vite app (file-driven benchmark views)
datasets/                       # Real-world and synthetic corpus inputs
legacy/                         # Archived graph pipeline and historical assets
```

---

## License

MIT — see [LICENSE](LICENSE)

**Original LoPace:** Copyright © 2026 Aman Ulla
**HPGCS extensions:** Copyright © 2026 Babul Bishwas
