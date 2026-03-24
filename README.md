# HPGCS / LoPace — Project Changes & Corpus Data Methodology

Last updated: 25 March 2026

## Purpose

This document summarizes the major project changes introduced in LoPace v2/HPGCS and explains the **new corpus-aware methodology** for prompt compression using shared corpus data.

---

## What Changed in the Project

### 1) Architecture evolved from single-prompt compression to a modular pipeline

The project now includes the HPGCS pipeline (`lopace/hpgcs.py`) with dedicated modules for:
- parsing (`lopace/parser.py`)
- graph decomposition + node reuse (`lopace/graph.py`)
- semantic clustering (`lopace/clustering.py`)
- tokenization (`lopace/tokenizer_module.py`)
- backend encoding (`lopace/encoder.py`)
- persistence (`lopace/storage.py`)
- reconstruction (`lopace/reconstruction.py`)

### 2) Corpus-level deduplication added as a research extension

A new content-addressable store (`lopace/corpus_store.py`) was added to support **cross-prompt reuse**:
- unique component content is stored once
- each prompt is stored as a compact reconstruction blueprint
- repeated content across prompts is referenced instead of duplicated

### 3) New corpus-aware APIs in `HPGCS`

`HPGCS` now exposes corpus-centric methods:
- `compress_corpus(text, prompt_id=None)`
- `compress_corpus_batch(texts)`
- `reconstruct_corpus(prompt_id)`
- `corpus_stats()`
- `corpus_node_report()`

### 4) Evaluation scripts expanded for corpus experiments

New/updated benchmark tooling compares corpus dedup vs baselines:
- `benchmark_corpus_dedup.py`
- `benchmark_full_evaluation.py`

These scripts evaluate reuse rates, dataset size scaling, and real-world-like prompt structure.

---

## New Methodology: Corpus Data Compression

## Problem with per-prompt compression

Even strong per-prompt compressors (e.g., Zstd/Hybrid) repeatedly compress the same shared sections (system prompts, tool schemas, RAG context) for every prompt.

## Corpus-aware approach

The new method treats a prompt corpus as a shared dataset and separates each prompt into:
1. **Literal segments** (delimiters/formatting such as `System: `, `User: `)
2. **Referenceable content segments** (component payloads)

Component payloads are content-hashed (SHA-256) and stored once in `content_nodes`.
Each prompt stores a compressed **blueprint** in `prompt_blueprints` containing a sequence of literals and references.

### Storage model

- `content_nodes`: unique compressed components + metadata (`ref_count`, sizes, type)
- `prompt_blueprints`: prompt-level reconstruction plans + original hash + stats

### Compression workflow

1. Parse prompt into lossless segments (`PromptParser.parse_segments`).
2. For each `ref` segment:
   - compute content hash
   - if hash exists: increment `ref_count`
   - else: compress and insert as new node
3. Persist compressed blueprint for the prompt.
4. Return **marginal storage metrics** (bytes newly added for this prompt).

### Reconstruction workflow

1. Load compressed blueprint.
2. Iterate blueprint sequence:
   - append literal text directly
   - resolve referenced node by hash and decompress
3. Concatenate all parts.
4. Verify with SHA-256 (`exact_match` / `hash_match`).

This guarantees lossless recovery while enabling corpus-level reuse.

---

## Why This Method Improves Results

When reuse exists in the corpus, only the first occurrence pays full storage cost.
Subsequent prompts often add mostly blueprint bytes, producing strong marginal savings.

Typical high-reuse components in LLM workloads:
- system instructions
- tool/function schemas
- policy blocks
- repeated retrieval context passages

---

## Key Metrics Introduced

### Per-prompt marginal metrics
- `marginal_bytes`
- `new_bytes_stored`
- `reused_refs` / `new_refs`
- `marginal_ratio`
- `marginal_savings_pct`

### Corpus-level metrics
- `n_prompts`
- `n_unique_nodes`
- `total_refs`
- `corpus_stored_bytes`
- `corpus_compression_ratio`
- `corpus_space_savings_pct`
- `storage_overhead_pct` (blueprint overhead)

---

## Practical Usage

```python
from lopace import HPGCS

hpgcs = HPGCS(db_path=":memory:", zstd_level=15)

# Corpus-aware compression
r1 = hpgcs.compress_corpus("System: You are helpful.\nUser: Explain entropy.")
r2 = hpgcs.compress_corpus("System: You are helpful.\nUser: Explain KL divergence.")

# Reconstruct one prompt
text, verify = hpgcs.reconstruct_corpus(r1["prompt_id"])
assert verify["exact_match"]

# Corpus analytics
stats = hpgcs.corpus_stats()
report = hpgcs.corpus_node_report()
print(stats["corpus_compression_ratio"], stats["corpus_space_savings_pct"])
```

---

## Methodology Notes and Trade-offs

- Best gains appear when prompts share large repeated components.
- Low-reuse corpora may reduce benefit; blueprint overhead still applies.
- Node-level dedup improves with corpus size and recurring templates.
- Hash-based addressing provides deterministic reuse and integrity checks.

---

## Recommended Evaluation Procedure

1. Run baseline per-prompt compression (Zstd / Hybrid).
2. Run corpus-aware compression on the same dataset.
3. Compare:
   - total bytes stored (not just per-item compressed size)
   - corpus-level ratio and space savings
   - reconstruction fidelity (must remain 100%).

Commands:

```bash
python benchmark_corpus_dedup.py
python benchmark_full_evaluation.py --n 5000
```

---

## Compatibility

- Legacy API (`PromptCompressor`) remains available.
- HPGCS standard pipeline remains available.
- Corpus-aware path is additive and can be used selectively per workload.

---

## Summary

The project now supports both classic per-prompt compression and a corpus-data methodology that deduplicates shared prompt components across the dataset. This change targets real production LLM workloads where repeated system/tool/context blocks dominate storage cost, while preserving strict lossless reconstruction.
