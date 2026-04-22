---
phase: 03-manuscript-update
completed: 2026-04-22
status: complete
artifacts:
  manuscript:
    - paper/HPGCS_IEEE_2026.tex
    - paper/compile.sh
  benchmark_exports:
    - research_real_200.json
    - research_real_1000.json
    - research_real_2000.json
    - research_real_5000.json
    - evaluation_results.json
plans:
  - 03-03-SUMMARY.md
  - 03-manuscript-update-03-SUMMARY.md
---

# Phase 3: Manuscript Update — Summary

Phase 3 refreshed the empirical artifacts that back the paper’s key tables and ensured the manuscript can be rebuilt reproducibly in this environment.

## What changed (high-level)

- **Benchmarks refreshed**: Regenerated real-data exports at prompt caps \(200, 1000, 2000, 5000\) and refreshed synthetic scenario outputs.
- **Manuscript alignment**: Confirmed the LaTeX manuscript contains the updated method naming and the `Zstd + Dict (Isolated)` vs `Zstd + Dict (Cached Edge)` split, and that table values match the regenerated JSON exports (within the paper’s rounding).
- **Reproducible compilation**: Added `paper/compile.sh` to compile via `pdflatex` when present, otherwise via `tectonic` with workspace-local cache/home directories.

## Traceability (paper ↔ artifacts)

- **Table I (real caps)** is backed by:
  - `research_real_200.json`
  - `research_real_1000.json`
  - `research_real_2000.json`
  - `research_real_5000.json`
- **Table II (synthetic scenarios)** is backed by:
  - `evaluation_results.json`
- **Table IV (method comparison, dict split)** uses:
  - `research_real_5000.json` (`zstd_dict` split fields)

## How to reproduce

- Rebuild the paper:
  - `./paper/compile.sh`
  - If using the repo-local tectonic binary, set `ALLOW_LOCAL_TECTONIC=1`.

For exact commands used during execution and per-task commits, see the plan summaries listed above.

