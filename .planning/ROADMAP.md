# ROADMAP

**3 phases** | **5 requirements mapped** | All v1 requirements covered ✓

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Foundation & Reliability | Establish formal tests and memory-safety parameters for the benchmark environment. | TEST-01, EVAL-03 | 2 |
| 2 | Algorithmic Refinement | Optimize the selector and stabilize dictionary compression metrics. | EVAL-01, EVAL-02 | 2 |
| 3 | Manuscript Update | Update the IEEE LaTeX paper with refined empirical data and logic updates. | PAPER-01 | 1 |

---

## Phase Details

### Phase 1: Foundation & Reliability
**Goal:** Establish formal tests and memory-safety parameters for the benchmark environment.
**Status:** Pending
**Requirements Mapped:**
- TEST-01: Pytest suite for Zstd/Centroid algorithms
- EVAL-03: Buffered streaming for large JSON payloads

**Success Criteria:**
1. A suite of unit tests runs automatically over math transformations passing safely via `pytest`.
2. Benchmark script executes over the `datasets/` JSON payloads without blowing past 2GB RAM limits on 10k nodes through buffered loading via `ijson` or lazy generators.

---

### Phase 2: Algorithmic Refinement
**Goal:** Optimize the selector and stabilize dictionary compression metrics.
**Status:** Pending
**Requirements Mapped:**
- EVAL-01: Refactor Zstd Dictionary Overhead
- EVAL-02: Optimize Adaptive Selector heuristic boundaries

**Success Criteria:**
1. Metric export for zero-reuse Zstd tracks *both* raw dict payload bounds and actual stream payloads (i.e., not penalizing short responses arbitrarily by entire dictionary string allocations over theoretical broadcast constraints).
2. The `evaluation/runner.py` adaptive strategy selects Brotli vs Zstd via immediate threshold metrics, reducing overall benchmark iteration loop times significantly.

---

### Phase 3: Manuscript Update
**Goal:** Update the IEEE LaTeX paper with refined empirical data and logic updates.
**Status:** Pending
**Requirements Mapped:**
- PAPER-01: Sync new empirical metrics to `paper/HPGCS_IEEE_2026.tex`

**Success Criteria:**
1. `paper/HPGCS_IEEE_2026.tex` is populated with revised graphs/metrics generated from passing Phase 1+2 datasets.

---

## Evolution

This document is the execution sequence.
- During phases, add steps to phase checklists.
- When phase completes, mark Status: Complete.
