# PROJECT CONTEXT — HPGCS Benchmark Lab / LoPace

**Author:** Babul Bishwas (babul09)
**Based on:** Original LoPace by Aman Ulla
**Last updated:** 28 March 2026

---

## 1. Project Purpose

HPGCS is a **lossless, corpus-aware prompt compression framework and benchmark lab** for LLM prompt workloads.

Current emphasis is not only compression methods, but also reproducible, multi-baseline benchmarking across synthetic and real prompt corpora with clear reporting and frontend visualization.

### Active Research Focus Areas

1. **Corpus-level component deduplication** (`lopace/corpus_store.py`)
2. **Delta compression** (`lopace/delta_store.py`)
3. **Per-prompt baselines at scale** (Zstd/gzip/Brotli)
4. **Zstd dictionary training with overhead-aware interpretation**
5. **Hybrid cascades** (`Brotli→Zstd`, `Zstd→LZ4HC`)
6. **Adaptive strategy selection** (best measured ratio per experiment)

### Legacy (archived)

The original graph pipeline (parse → graph → nodes → clustering → tokenize → encode → store → reconstruct) is preserved in `legacy/lopace_graph/` for reference.

---

## 2. Core Modules (`lopace/`)

### `lopace/compressor.py` — Per-Prompt Compressor

`PromptCompressor` supports multiple codecs and token workflows:

- `zstd`, `gzip`, `deflate`, `lzma`, `lz4`, `brotli`, `snappy`
- `token` (BPE packing)
- `hybrid` (BPE + Zstd)

Key API shape:

```python
compressor = PromptCompressor(model="cl100k_base", zstd_level=15)
blob = compressor.compress(text, method)
text = compressor.decompress(blob, method)
results = compressor.compare_all(text)
```

### `lopace/parser.py` — Structural Prompt Parser

Provides role-aware segmentation used by corpus dedup:

- `parse(text)` for typed prompt structure
- `parse_segments(text)` / `parse_segments_chunked(...)` for dedup references

### `lopace/corpus_store.py` — Corpus Dedup Store

Content-addressable storage over parsed prompt components:

1. Parse into referenceable segments
2. Hash components (SHA-256)
3. Reuse existing component nodes when possible
4. Compress new payloads with Zstd
5. Store prompt blueprints for deterministic reconstruction

Primary APIs:

```python
store = CorpusStore(db_path=":memory:", zstd_level=15)
result = store.store(prompt_id, text, segments)
text, verify = store.retrieve(prompt_id)
stats = store.corpus_stats()
```

### `lopace/delta_store.py` — Delta Compression

Stores prompts against centroids when similarity threshold is met, otherwise stores as new centroid. Retrieval verifies round-trip integrity.

---

## 3. Evaluation System

### `evaluation/baselines.py`

Implements baseline and sweep/cascade logic:

- Per-prompt Zstd
- gzip level sweep (`L1`, `L6`, `L9`)
- Brotli quality sweep (`Q1`, `Q5`, `Q9`, `Q11`)
- Hybrid cascades (`Brotli→Zstd`, `Zstd→LZ4HC` variants)
- Zstd dictionary training (`ratio_without_dict`, `ratio_with_dict`)
- Corpus dedup / chunked dedup / delta / adaptive routing

### `evaluation/runner.py`

Runs all methods for each experiment, stores sweep details, emits best baseline variants, and computes an adaptive best-of-methods result.

### `benchmark_full_evaluation.py`

Current end-to-end benchmark entrypoint:

- Synthetic scenarios: standard reuse, full reuse, low reuse, zero reuse, zero reuse + tools/context
- Real datasets: JSON/JSONL with format auto-detection
- Redundancy analysis and scaling exports
- JSON + CSV artifact generation

---

## 4. Frontend / API Benchmark Workflow

### Backend (`serve_api.py`)

- `POST /api/benchmark` runs experiments from UI parameters
- `GET /api/benchmark-results?path=...` loads stored result JSON files from workspace

### Frontend (`frontend/`)

- Vite dev port pinned to `5174`
- Benchmarks page is **file-driven** (path input + run-type + experiment filtering)
- Dictionary metrics can be toggled between:
  - with overhead (deployment realistic)
  - without overhead (raw compression view)

---

## 5. Current Research Artifacts

Primary outputs generated in current workflow:

- `RESEARCH_RESULTS_2026_03_28.md`
- `research_results_2026_03_28.json`
- `research_scaling_2026_03_28.csv`

Real-data prompt-cap artifacts:

- `research_real_200.json`
- `research_real_1000.json`
- `research_real_2000.json`
- `research_real_5000.json`

Real-data scaling artifacts:

- `research_real_scaling_200_real_eval_results.csv`
- `research_real_scaling_1000_real_eval_results.csv`
- `research_real_scaling_2000_real_eval_results.csv`
- `research_real_scaling_5000_real_eval_results.csv`

---

## 6. Dependencies (Operationally Relevant)

Core compression stack:

- `zstandard`, `brotli`, `lz4`, `python-snappy`, `tiktoken`

Benchmark/runtime support:

- `numpy`, `networkx`

UI/API stack:

- `fastapi`, `uvicorn`, React + Vite frontend

---

## 7. Losslessness Guarantee

All active compression paths are lossless:

- Corpus dedup validates reconstruction against stored original hash
- Delta store verifies reconstructed prompts
- Per-prompt compressor methods are round-trip checked in method-specific paths

Benchmark scripts include reconstruction assertions during runs.