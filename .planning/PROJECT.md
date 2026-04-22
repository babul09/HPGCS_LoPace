# PROJECT CONTEXT — HPGCS Audit, Fix, and Paper Update

**What This Is:**
A milestone project to rigorously audit the existing HPGCS / LoPace benchmarking framework, resolve the known technical flaws mapped during our codebase analysis, and reflect those improvements directly within the formal IEEE LaTeX manuscript `HPGCS_IEEE_2026.tex`.

## Requirements

### Validated

- ✓ **Hybrid Prompt Evaluator**: Lossless, corpus-aware prompt compression framework (`lopace/`).
- ✓ **Parsers & Stores**: `ParserLayer`, `CorpusStore`, `DeltaStore`, and `PromptCompressor`. 
- ✓ **Evaluation System**: Iterative baselines including Zstd, Brotli, gzip, cascades (`evaluation/`).
- ✓ **UI & API Integration**: FastAPI backend and React frontend for executing analytical workflows.

### Active

- [ ] **Test Suite Implementation**: Implement a formalized unit test suite for the core mathematical models (Centroid handling, Zstd Dictionary generation) to prevent regressions, addressing the architectural gap in `TESTING.md`.
- [ ] **Adaptive Selector Optimization**: Refactor the Adaptive Selector in `evaluation/` to replace the naive oracle-tier exhaustive scaling logic with a heuristic predictor matrix or more efficient runtime path, resolving geometric complexity issues.
- [ ] **Dictionary Overhead Mitigation**: Verify, isolate, and formulate a fix for the Zstd Dictionary extraction overhead masking true compression payloads during zero-reuse bounds.
- [ ] **Large JSON Scaling**: Audit and resolve unpaged memory bounds when loading massive dataset evaluation logs (10k+ nodes).
- [ ] **Latex Manuscript Update**: Propagate new experimental methodologies, fixed proofs, and empirical benchmark revisions into `paper/HPGCS_IEEE_2026.tex`.

### Out of Scope

- [Full UI Rewrite] — Focus is entirely on the algorithmic layer, evaluation bounds, and the research paper, not the React UI.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Focus on Codebase first | The paper relies on empirical benchmarking; if the codebase logic is flawed or untested, the manuscript claims are invalid. | — Pending |

---
*Last updated: 2026-04-22 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
