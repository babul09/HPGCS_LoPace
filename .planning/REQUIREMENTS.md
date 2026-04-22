# Requirements

## v1 Requirements

### Evaluation Algorithms
- [ ] **EVAL-01**: Refactor Zstd Dictionary Overhead. Isolate actual payload compression vs dictionary transfer bytes for valid zero-reuse scenario modeling.
- [ ] **EVAL-02**: Optimize Adaptive Selector. Remove geometric `O(N)` compressor testing loop and implement predictive heuristic boundaries.
- [ ] **EVAL-03**: Memory scaling. Implement buffered streaming iteration for reading large dataset JSON arrays rather than loading entirely to unpaged memory.

### Reliability & Testing
- [ ] **TEST-01**: Implement Pytest suite. Add mathematical unit assertions over centroid patching and dictionary deterministic generation steps.

### Documentation & Publishing
- [ ] **PAPER-01**: Latex Update. Sync new empirical benchmark results, data visualizations from runs, and algorithm explanations to `paper/HPGCS_IEEE_2026.tex`.

---

## Validated Requirements (Existing Codebase)

### Hybrid Prompt Evaluator
- ✓ Lossless, corpus-aware prompt compression framework (`lopace/`).
- ✓ Parsers & Stores: ParserLayer, CorpusStore, DeltaStore.
- ✓ Baseline execution (Zstd, gzip, Brotli).

## Out of Scope

- React UI changes (`frontend/`) unless strictly required to view the updated metric schema mapping.

---
*Last updated: 2026-04-22*
