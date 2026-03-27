# PROJECT CONTEXT — HPGCS / LoPace

**Author:** Babul Bishwas (babul09)
**Based on:** Original LoPace by Aman Ulla
**Last updated:** 27 March 2026

---

## 1. Project Purpose

HPGCS is a **lossless, corpus-aware prompt compression framework** for LLM prompt
workloads. It exploits the structural redundancy in production prompt corpora —
where system instructions, tool schemas, and RAG context blocks are repeated
across thousands of prompts — to achieve compression ratios far beyond per-prompt
methods.

### Research Focus Areas

1. **Corpus-level component deduplication** (`lopace/corpus_store.py`)
2. **Delta compression** (`lopace/delta_store.py`)
3. **Zstd dictionary training** (in benchmark suite)

### Legacy (archived)

The original HPGCS graph pipeline (parse → graph → nodes → clustering →
tokenize → encode → store → reconstruct) was evaluated but did not produce
significant compression gains. Its code is preserved in `legacy/lopace_graph/`.

---

## 2. Core Modules (`lopace/`)

### `lopace/compressor.py` — Per-Prompt Compressor

The `PromptCompressor` class provides multi-method per-prompt compression.

**Available methods** (enum `CompressionMethod`):
- `zstd` — Zstandard (primary, configurable level 1–22)
- `lz4` — LZ4 (fast)
- `brotli` — Brotli (high ratio)
- `snappy` — Snappy (ultra-fast)
- `gzip`, `deflate`, `lzma` — stdlib options
- `token` — BPE tokenization only (tiktoken → binary pack)
- `hybrid` — BPE + Zstd (tokenize → pack → compress)

**Key APIs:**
```python
compressor = PromptCompressor(model="cl100k_base", zstd_level=15)
blob = compressor.compress(text, method)
text = compressor.decompress(blob, method)
results = compressor.compare_all(text)  # benchmark all methods
```

### `lopace/parser.py` — Structural Parser

The `PromptParser` class segments prompts by role delimiters.

**Two parsing modes:**
1. `parse(text)` → `ParsedPrompt` with typed components (system, user, instruction, context, other)
2. `parse_segments(text)` → list of `{"type": "literal"|"ref", "content": ..., "component_type": ...}` for corpus dedup

**Recognized delimiters:** `System:`, `User:`, `Instruction:`, `Context:`, `Tool:`, `Assistant:`

### `lopace/corpus_store.py` — Corpus-Level Deduplication

The `CorpusStore` class implements content-addressable storage for prompt corpora.

**How it works:**
1. Parse prompt into lossless segments (`parser.parse_segments`)
2. SHA-256 hash each referenceable content segment
3. If hash exists → increment `ref_count` (zero marginal cost)
4. If new → compress with Zstd and insert as `content_node`
5. Store compact reconstruction blueprint for the prompt

**Storage model (SQLite):**
- `content_nodes`: `{content_hash, compressed_data, original_size, compressed_size, component_type, ref_count}`
- `prompt_blueprints`: `{prompt_id, original_hash, blueprint (JSON), original_size, marginal_bytes}`

**Key APIs:**
```python
store = CorpusStore(db_path=":memory:", zstd_level=15)
result = store.store(prompt_id, text, segments)  # returns marginal metrics
text, verify = store.retrieve(prompt_id)          # lossless reconstruction
stats = store.corpus_stats()                      # corpus-wide metrics
report = store.node_report()                      # per-node breakdown
```

**Marginal metrics per prompt:**
- `marginal_bytes` — total bytes newly added for this prompt
- `new_bytes_stored` — new content node bytes
- `blueprint_bytes` — blueprint overhead
- `reused_refs` / `new_refs` — component reuse tracking
- `marginal_ratio`, `marginal_savings_pct`

### `lopace/delta_store.py` — Delta Compression

The `DeltaStore` class stores prompts as diffs against cluster centroids.

**How it works:**
1. Incoming prompt is compared against existing centroids (configurable similarity threshold)
2. If similar enough → compute unified diff against centroid, compress the delta
3. If no match → store as new centroid (full text, compressed)
4. Reconstruct by decompressing centroid + applying patch

**Key APIs:**
```python
ds = DeltaStore(db_path=":memory:", zstd_level=15, similarity_threshold=0.7)
result = ds.store(prompt_id, text)
text, verify = ds.retrieve(prompt_id)
stats = ds.corpus_stats()
```

**Storage model (SQLite):**
- `centroids`: `{centroid_id, compressed_text, original_size, compressed_size}`
- `deltas`: `{prompt_id, centroid_id, compressed_delta, original_size, delta_size, similarity}`

---

## 3. Evaluation Scripts

### `benchmark_corpus_dedup.py`
Focused comparison of three methods:
1. Per-prompt Zstd (baseline)
2. Per-prompt Hybrid / BPE+Zstd (original paper's best)
3. Corpus-level component dedup (proposed method)

Also includes scaling analysis (compression ratio vs corpus size).

### `benchmark_full_evaluation.py`
Comprehensive evaluation (~1500 lines) supporting:
- **Synthetic data** with controllable reuse rates (0%–100%)
- **Real-world datasets** (JSON, JSONL, NDJSON, Parquet)
- Format auto-detection (ShareGPT, Alpaca, OpenAI messages)
- **Four methods:** per-prompt Zstd, per-prompt Hybrid, Zstd with dictionary training, corpus dedup
- Scaling analysis, redundancy analysis, CSV/JSON export

**Usage:**
```bash
python benchmark_full_evaluation.py --n 5000
python benchmark_full_evaluation.py --real-data dataset.json
python benchmark_full_evaluation.py --real-data-dir ./datasets/
```

### `generate_production_dataset.py`
Generates a realistic 1500-prompt dataset simulating 3 LLM applications:
1. Customer support bot (high system prompt reuse)
2. Code review assistant (shared tools, unique code)
3. RAG research assistant (shared contexts, unique queries)

---

## 4. Dependencies

**Core (required):**
- `zstandard >= 0.22.0` — Primary compression backend
- `lz4 >= 4.3.3` — Fast compression
- `brotli >= 1.1.0` — High-ratio compression
- `python-snappy >= 0.7.1` — Ultra-fast compression
- `tiktoken >= 0.5.0` — BPE tokenization

**Analysis (required for benchmarks):**
- `networkx >= 3.0` — Graph processing
- `numpy >= 1.24.0` — Numerical operations

**Visualization (optional):**
- `streamlit >= 1.28.0` — Web UI
- `plotly >= 5.0.0` — Interactive charts
- `pandas >= 1.5.0` — DataFrames

---

## 5. Project File Map

```
lopace/                         # Active Python package
  ├── __init__.py               # Public API exports
  ├── compressor.py             # Multi-method per-prompt compressor (701 lines)
  ├── parser.py                 # Structural prompt parser (282 lines)
  ├── corpus_store.py           # Corpus-level component dedup (375 lines)
  └── delta_store.py            # Delta compression (497 lines)

benchmark_corpus_dedup.py       # Corpus dedup benchmark (571 lines)
benchmark_full_evaluation.py    # Full evaluation suite (1498 lines)
generate_production_dataset.py  # Synthetic dataset generator (257 lines)

pyproject.toml                  # Package metadata
setup.py                        # Setuptools config
requirements.txt                # Dependencies
LICENSE                         # MIT license
README.md                       # Project README

legacy/                         # Archived code
  ├── lopace_graph/             # Graph pipeline modules (7 files)
  │   ├── hpgcs.py              # Pipeline orchestrator
  │   ├── graph.py              # Graph decomposition + node reuse
  │   ├── clustering.py         # Semantic clustering
  │   ├── tokenizer_module.py   # BPE tokenizer module
  │   ├── encoder.py            # Learned compression encoder
  │   ├── storage.py            # Graph storage database
  │   └── reconstruction.py     # Graph-based reconstruction
  ├── hpgcs_app.py              # Streamlit app (graph pipeline)
  ├── streamlit_app.py          # Streamlit app (v1 compressor)
  ├── verify_hpgcs.py           # Graph pipeline smoke test
  ├── notebooks/                # Old Jupyter notebooks
  ├── paper/                    # Old paper assets
  ├── scripts/                  # Old visualization scripts
  └── tests/                    # Old test suite
```

---

## 6. Losslessness Guarantee

All compression paths guarantee lossless reconstruction:
- **Corpus store:** SHA-256 hash of original text stored with blueprint; verified on retrieval
- **Delta store:** SHA-256 hash stored with each delta record; verified on patch
- **Compressor:** Direct byte-level round-trip (compress → decompress → assert equal)

Verification is embedded in both the stores and the benchmark scripts.