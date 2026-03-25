# HPGCS / LoPace — Full Project Context Document

Last updated: 25 March 2026

## 1) What this repository is

This repository implements **LoPace v2 / HPGCS** (Hybrid Prompt Graph Compression System):
- A modular, lossless prompt-compression framework for LLM prompt corpora.
- A classic per-prompt compression API (`PromptCompressor`) retained for compatibility.
- A newer pipeline API (`HPGCS`) that combines structure-aware parsing, graph/node reuse, semantic clustering, BPE token packing, backend compression, persistence, and reconstruction.
- Research workflows for **corpus-level deduplication** and **delta compression** against multiple baselines.

This document covers the **current project surface** (top-level files + `lopace/` package). Legacy content is intentionally omitted from core behavior.

---

## 2) Repository map (current project)

### Core Python package (`lopace/`)

- `lopace/__init__.py`
  - Public export surface for both legacy (`PromptCompressor`) and v2 (`HPGCS` + module classes).
  - Declares package `__all__` and version sourcing (`setuptools-scm` generated `_version.py` fallback).

- `lopace/hpgcs.py`
  - Main v2 orchestrator class `HPGCS`.
  - Integrates all pipeline modules plus corpus-dedup extension.

- `lopace/parser.py`
  - Rule-based structural parser.
  - Lossless segment parser with optional chunking for finer dedup granularity.

- `lopace/graph.py`
  - `PromptGraph` data model.
  - `ReusableNodeManager` (content-hash dedup + stable node IDs).
  - `PromptGraphDecomposer` for component-path graph creation and summary metrics.

- `lopace/clustering.py`
  - Semantic clustering module with two backends:
    - sentence-transformers embeddings (if available)
    - n-gram cosine fallback (always available)

- `lopace/tokenizer_module.py`
  - BPE tokenization via `tiktoken`.
  - Compact binary packing format with uint16/uint32 selection.

- `lopace/encoder.py`
  - Prototype “learned” encoder:
    - compresses packed tokens using selectable backend
    - computes/quantizes latent vectors for analysis metadata

- `lopace/storage.py`
  - SQLite persistence for prompt records, reusable nodes, and clusters.

- `lopace/reconstruction.py`
  - Prompt reconstruction engine from storage + node registry.
  - Integrity verification via SHA-256 and exact string match.

- `lopace/corpus_store.py`
  - Content-addressable corpus dedup store (shared component nodes + compressed blueprints).

- `lopace/delta_store.py`
  - Delta compression store using centroids + diffs for similar-but-not-identical prompts.

- `lopace/compressor.py`
  - Legacy multi-method compressor API (`CompressionMethod`, `PromptCompressor`).
  - Supports zstd/lz4/brotli/snappy/gzip/deflate/lzma/token/hybrid.

### Executables / app entry points (top-level)

- `hpgcs_app.py`
  - Streamlit app for v2 HPGCS pipeline and method comparisons.

- `streamlit_app.py`
  - Streamlit app for legacy `PromptCompressor` and detailed metric visualizations.

- `verify_hpgcs.py`
  - Smoke test script validating imports + compress/reconstruct invariants.

- `benchmark_corpus_dedup.py`
  - Focused benchmark: per-prompt baselines vs corpus-level dedup.

- `benchmark_full_evaluation.py`
  - Full experiment runner: synthetic + real data, multiple methods, scaling outputs.

- `generate_production_dataset.py`
  - Generates synthetic production-like dataset (`datasets/production_simulation.json`).

### Packaging/config/docs/data artifacts

- Packaging/config:
  - `pyproject.toml`, `setup.py`, `MANIFEST.in`, `requirements.txt`, `requirements-dev.txt`
- Governance/docs:
  - `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`
- Result artifacts (generated experiment outputs):
  - `evaluation_results.json`, `eval_results.json`, `results_*.json`, `scaling*.csv`, `scaling_results_real_*.csv`
- Dataset folder:
  - `datasets/` (includes production simulation JSON, large eval JSON, and `wildchat/` parquet shards)

---

## 3) Runtime surfaces and how to run

### A) Library API (canonical programmatic surface)

```python
from lopace import HPGCS

hpgcs = HPGCS(db_path=":memory:", tokenizer_model="cl100k_base", zstd_level=15)
r = hpgcs.compress_and_reconstruct("System: ...\nUser: ...")
print(r["compression_ratio"], r["exact_match"])
```

Key API groups:
- Standard pipeline:
  - `compress`, `compress_batch`, `reconstruct`, `compress_and_reconstruct`
- Analytics:
  - `database_stats`, `list_prompts`, `list_nodes`, `list_clusters`
- Corpus extension:
  - `compress_corpus`, `compress_corpus_batch`, `reconstruct_corpus`, `corpus_stats`, `corpus_node_report`

### B) Streamlit apps

- HPGCS app:
  - `streamlit run hpgcs_app.py`
  - Includes pipeline stage views, reusable node registry, semantic clusters, per-prompt and aggregate metrics.
- Legacy app:
  - `streamlit run streamlit_app.py`
  - Runs selected compression methods and computes CR/SS/BPC/throughput/hash/exact-match metrics.

### C) CLI evaluation scripts

- Corpus benchmark:
  - `python benchmark_corpus_dedup.py --n 1000 --system-reuse 0.8`
- Full evaluation:
  - `python benchmark_full_evaluation.py --n 5000`
  - `python benchmark_full_evaluation.py --real-data dataset.json --json-field prompt`
  - `python benchmark_full_evaluation.py --real-data-dir ./datasets/`

### D) Verification

- `python verify_hpgcs.py`
  - Validates importability and pipeline reconstruction assumptions.

---

## 4) End-to-end system flow (HPGCS standard pipeline)

`HPGCS.compress(text)` in `lopace/hpgcs.py` executes:

1. **Parse** (`PromptParser.parse`)
   - Splits by role delimiters (`System:`, `Instruction:`, `User:`, etc.).
   - Produces typed components + structure flag.

2. **Graph decomposition + node dedup** (`PromptGraphDecomposer`, `ReusableNodeManager`)
   - Each component is converted into a node reference.
   - Node dedup key = SHA-256(content).
   - Reused content increments node frequency instead of creating duplicates.

3. **Semantic clustering** (`VectorSimilarityClusterer.assign`)
   - Embeds prompt and compares to cluster centroids.
   - If best similarity >= threshold -> joins existing cluster; else creates new cluster `Cxxx`.

4. **Tokenization and packing** (`ResidualTextTokenizer`)
   - BPE tokenize entire prompt text.
   - Pack token IDs to binary format:
     - 1-byte format flag (0=uint16, 1=uint32)
     - followed by packed integer sequence.

5. **Encoding / compression** (`LearnedCompressionEncoder.encode`)
   - Compress packed bytes with selected backend (zstd/lz4/brotli/snappy/gzip/deflate/lzma).
   - Compute latent vector (hash-based embedding mean pool) and quantize to int8 bytes.

6. **Persistence** (`GraphStorageDatabase.insert_prompt` + node/cluster upserts)
   - Stores prompt record in `prompts` table.
   - Stores reusable nodes in `nodes` table.
   - Stores cluster metadata in `clusters` table.

`HPGCS.compress_and_reconstruct(text)` then calls:
- `HPGCS.reconstruct(prompt_id)` -> `PromptReconstructionEngine.reconstruct_from_db`
- Returns merged metrics including `exact_match`, `hash_match`, and decompression timing.

---

## 5) Reconstruction behavior and integrity guarantees

### Standard reconstruction (`lopace/reconstruction.py`)

- Reads `graph_json` and iterates ordered `node_ids`.
- If node exists in in-memory node manager, its content is reused directly.
- Otherwise decodes stored compressed blob via encoder + tokenizer.
- Reassembles with component label prefixes (`System:`, `User:`, ...).
- Validates with SHA-256 and direct string equality.

Important implementation note:
- Residual fallback path decodes from the full prompt blob and marks component as `unstructured`; this is acceptable in current pipeline usage where graphs typically reference managed nodes.

### Corpus reconstruction (`lopace/corpus_store.py`)

- Loads prompt blueprint from `prompt_blueprints`.
- Blueprint segments:
  - literal segment (`{"t":"l","v":...}`)
  - reference segment (`{"t":"r","f":full_hash,...}`)
- Resolves referenced content nodes from `content_nodes`, decompresses, concatenates.
- Compares rebuilt hash to stored original hash.

### Delta reconstruction (`lopace/delta_store.py`)

- Loads stored centroid text.
- If mode is `delta`, decompresses unified diff and applies `_apply_delta`.
- If mode is `centroid`, centroid text itself is prompt text.
- Verifies SHA-256 identity.

---

## 6) Detailed module mechanics

### 6.1 `PromptParser` (`lopace/parser.py`)

- Supports delimiter keywords: system, instruction, context, tool, assistant, user, human, question, answer, gpt.
- `parse(text)`:
  - Returns `ParsedPrompt(components, raw_text)`.
  - Handles repeated component types using suffixes (`system_2`, etc.).
- `parse_segments(text)` (lossless corpus mode):
  - Returns alternation of literal delimiters and referenceable content segments.
  - Enforces reconstruction invariant; if violated, falls back to single unstructured ref segment.
- `parse_segments_chunked(text, min_chunk_bytes, max_chunk_bytes)`:
  - Splits large content segments into paragraph/line-aligned chunks.
  - Intended to improve dedup opportunities on partial reuse.

### 6.2 Graph + node reuse (`lopace/graph.py`)

- Node model: `PromptNode(node_id, component_type, content, content_hash, frequency)`.
- Node IDs use component-type prefixes (`SYS`, `USR`, `CTX`, etc.) plus counters.
- `ReusableNodeManager.get_or_create`:
  - Dedup by SHA-256(content).
  - Increments `frequency` on reuse.
- `PromptGraphDecomposer.decompose`:
  - Builds ordered node path and adjacent directed edges.
- `graph_summary` returns reuse metrics:
  - reused node count/rate and bytes saved by reuse.

### 6.3 Clustering (`lopace/clustering.py`)

- Backends:
  - sentence-transformers (`all-MiniLM-L6-v2`) if available/enabled.
  - fallback hashed char n-gram vectors with cosine similarity.
- `assign(prompt_id, text)`:
  - nearest centroid search
  - threshold-based join-or-create policy
  - incremental centroid update (running mean)
- Outputs cluster IDs (`C001`, ...), similarity scores, and summary statistics.

### 6.4 Tokenization (`lopace/tokenizer_module.py`)

- Requires `tiktoken` encoding model (default `cl100k_base`).
- `pack` selects uint16 if IDs fit, else uint32; prepends 1-byte flag.
- `unpack` validates payload divisibility (2/4-byte alignment).
- Utility metrics include token count and text-to-packed compression ratio.

### 6.5 Encoding (`lopace/encoder.py`)

- `available_base_compressors` returns supported installed backends.
- `encode(packed_tokens, token_ids)` returns:
  - compressed payload (storage data)
  - quantized latent bytes (analysis metadata)
- `decode` reverses backend compression.
- Latent embedding is deterministic hash-based prototype, not a trained model.

### 6.6 Graph storage (`lopace/storage.py`)

SQLite tables:
- `prompts`: full prompt record + blob + latent + graph JSON + size metrics.
- `nodes`: reusable component registry with content hash and frequency.
- `clusters`: centroid JSON, representative text, member count.

`stats()` aggregates:
- total prompts/original/compressed bytes
- overall CR and savings
- unique node count and cluster count

### 6.7 Corpus dedup store (`lopace/corpus_store.py`)

SQLite tables:
- `content_nodes`: unique component blobs keyed by full content hash.
- `prompt_blueprints`: compressed reconstruction plans and per-prompt reuse counters.

Store path (`store`):
- For each `ref` segment:
  - existing hash -> increment `ref_count`
  - new hash -> compress and insert new node
- Compress and save blueprint JSON.
- Returns marginal economics:
  - `marginal_bytes`, `new_bytes_stored`, `reused_refs`, `marginal_ratio`, etc.

Analytics (`corpus_stats`):
- corpus-stored bytes = `sum(node compressed)` + `sum(blueprint bytes)`
- reports corpus CR, savings %, average refs per node, and blueprint overhead %.

### 6.8 Delta store (`lopace/delta_store.py`)

- Maintains centroid set and samples candidates for speed.
- Similarity metric uses fast line-set Jaccard-like overlap with length-ratio guard.
- `store`:
  - if best similarity >= threshold -> store compressed unified diff (`delta` mode)
  - else store prompt as new centroid (`centroid` mode)
- Stats include centroid counts, delta fraction, and corpus-level CR/savings.

### 6.9 Legacy compressor (`lopace/compressor.py`)

- Maintains pre-v2 API.
- Provides algorithm selection via enum and method-specific compress/decompress operations.
- Used heavily by legacy app and baseline comparisons.

---

## 7) Evaluation framework internals

## 7.1 `benchmark_corpus_dedup.py`

Purpose:
- Focused comparison among:
  - Per-prompt Zstd
  - Per-prompt Hybrid (BPE+Zstd)
  - Corpus-level dedup

Key behavior:
- Generates synthetic corpora with controllable reuse rates and optional tools/context sections.
- Verifies losslessness during benchmark loops.
- Computes scaling curve across corpus sizes.
- Optionally writes JSON output with config + method results + scaling data.

## 7.2 `benchmark_full_evaluation.py`

Purpose:
- Comprehensive experiment runner with synthetic and real-dataset modes.

Methods evaluated per experiment:
1. `zstd` (per-prompt)
2. `hybrid` (per-prompt)
3. `zstd_dict` (dictionary-trained zstd with overhead accounting)
4. `corpus_dedup`
5. `corpus_dedup_chunked`
6. `delta`

Real dataset handling:
- Supports JSON, JSONL/NDJSON, and Parquet.
- Auto-detects common dataset schemas (ShareGPT, OpenAI messages, Alpaca, common text fields).
- Supports directory aggregation across multiple files.
- Includes redundancy analysis (exact duplicates, prefix sharing, line-level reuse).

Outputs:
- JSON summary (`evaluation_results.json` by default)
- scaling CSV (`scaling_results.csv` with optional real-data name suffix)

---

## 8) Streamlit application behavior

### 8.1 `hpgcs_app.py`

- Multi-tab interface:
  - HPGCS pipeline run
  - method comparison
  - architecture explanation
- Sidebar controls:
  - tokenizer model
  - zstd level
  - base compressor backend
  - cluster threshold
- Caches `HPGCS` instance via `@st.cache_resource`.
- For each prompt:
  - runs `compress_and_reconstruct`
  - displays CR/savings/hash/exact-match and stage-level artifacts
- Aggregate views:
  - DB stats, node reuse registry, cluster assignments, charts (Plotly/Pandas optional)

### 8.2 `streamlit_app.py`

- Legacy compressor UI with selectable methods.
- Computes comprehensive metrics per method:
  - CR, SS, BPC, throughput, timing, SHA-256 match, exact match
  - optional entropy/theoretical-limit metrics via compressor helper methods
- Stores per-run results in Streamlit session state for comparative rendering.

---

## 9) Data generation and artifacts

### 9.1 Dataset generation (`generate_production_dataset.py`)

- Simulates 3 production app patterns:
  - customer support
  - code review assistant
  - RAG assistant
- Injects realistic repeated structures (fixed system/tool/context blocks) + user variability.
- Writes JSON array to `datasets/production_simulation.json`.

### 9.2 Data and results in repo root

Observed artifact patterns:
- `results_*.json`, `evaluation_results.json`, `eval_results.json`
  - serialized benchmark outputs from prior runs.
- `scaling*.csv` and `scaling_results_real_*.csv`
  - checkpointed scaling curves comparing dedup and baselines.

Notable metadata example:
- `evaluation_results.json` references very large real dataset file sizes (hundreds of MB), indicating large-scale experiments.

---

## 10) Dependencies, packaging, and build model

### Runtime dependencies (`requirements.txt` + `pyproject.toml`)

Core:
- `zstandard`, `lz4`, `brotli`, `python-snappy`, `tiktoken`, `streamlit`
- `networkx`, `numpy`
- visuals: `plotly`, `pandas`

Optional/high-value:
- `sentence-transformers` for stronger semantic clustering backend.

### Dev dependencies (`requirements-dev.txt`)

- Includes runtime dependencies plus:
  - `pytest`, `pytest-cov`, `black`, `flake8`, `mypy`, and plotting stack.

### Packaging

- PEP 517 build backend: `setuptools.build_meta`.
- Dynamic version from `setuptools-scm`.
- Python support: `>=3.8`.
- `MANIFEST.in` includes package python files + readme/license/requirements.

---

## 11) Storage schemas and persistence boundaries

### Standard pipeline DB (`GraphStorageDatabase`)

Tables:
- `prompts`
- `nodes`
- `clusters`

Persistence semantics:
- Prompt inserts are `INSERT OR REPLACE` by `prompt_id`.
- Node upsert updates frequency on conflict.
- Cluster upsert updates centroid/member_count on conflict.

### Corpus DB (`CorpusStore`)

Tables:
- `content_nodes`
- `prompt_blueprints`

Persistence semantics:
- Content hashes are canonical IDs (unique content-addressed nodes).
- Prompt blueprint keyed by `prompt_id` (replaceable).

### Delta DB (`DeltaStore`)

Tables:
- `centroids`
- `delta_prompts`

Persistence semantics:
- Each prompt gets a storage-mode row (`delta` or `centroid`).
- Centroids tracked with reference counts.

---

## 12) Typical workflows

### Workflow A — API-level compression service prototype

1. Initialize `HPGCS` with chosen tokenizer/base compressor.
2. Ingest prompts via `compress` or `compress_batch`.
3. Use `database_stats/list_nodes/list_clusters` for analytics.
4. Reconstruct as needed and enforce `exact_match/hash_match` assertions.

### Workflow B — Corpus optimization experiment

1. Generate or load dataset (`generate_production_dataset.py` / real JSON).
2. Run `benchmark_full_evaluation.py` with target flags.
3. Compare method ratios and overhead from generated JSON/CSV artifacts.
4. Inspect dedup reuse metrics (`unique_nodes`, `avg_reuse`, marginal bytes).

### Workflow C — Interactive exploration

1. Launch `hpgcs_app.py` for stage-by-stage behavior.
2. Launch `streamlit_app.py` for legacy method-level comparisons.

---

## 13) Important implementation assumptions and caveats

- Losslessness is central and repeatedly asserted in benchmark and verification paths.
- Semantic clustering gracefully degrades to n-gram cosine if ST model is unavailable.
- Encoder latent vector is prototype/analysis metadata; storage correctness depends on compressed packed tokens.
- `.gitignore` excludes `/datasets`, but dataset directory exists in workspace: treat data tracking policy as environment-dependent.
- `CONTRIBUTING.md` references `pytest tests/` while active tests are not in top-level `tests/` in this workspace snapshot.
- Real-data schema extraction in benchmarks is broad and heuristic; field auto-detection may require explicit `--json-field` for atypical datasets.

---

## 14) Quick symbol-to-responsibility index

- `HPGCS` → orchestrates all standard and corpus-aware operations.
- `PromptParser` → structural split + lossless segmentation/chunking.
- `ReusableNodeManager` / `PromptGraphDecomposer` → content dedup graph modeling.
- `VectorSimilarityClusterer` → semantic grouping.
- `ResidualTextTokenizer` → BPE IDs + binary packing.
- `LearnedCompressionEncoder` → backend compression + latent metadata.
- `GraphStorageDatabase` → standard pipeline SQLite persistence.
- `PromptReconstructionEngine` → rebuild + verification.
- `CorpusStore` → content-addressable cross-prompt dedup.
- `DeltaStore` → centroid+diff partial-redundancy compression.
- `PromptCompressor` → legacy per-prompt compression interface.

---

## 15) What to read first (onboarding path)

1. `lopace/hpgcs.py` (pipeline contract and public methods)
2. `lopace/parser.py` + `lopace/corpus_store.py` (dedup methodology)
3. `lopace/graph.py`, `lopace/clustering.py`, `lopace/tokenizer_module.py`, `lopace/encoder.py`
4. `lopace/storage.py` + `lopace/reconstruction.py`
5. `benchmark_full_evaluation.py` (evaluation methodology and outputs)
6. `hpgcs_app.py` (interactive interpretation of pipeline outputs)

This order provides the fastest route from conceptual model to execution and measurement.