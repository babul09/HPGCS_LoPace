---
phase: 03-manuscript-update
plan: 03
subsystem: docs
tags: [latex, benchmark, real-data, synthetic, tectonic]

# Dependency graph
requires:
  - phase: 02-algorithmic-refinement
    provides: benchmark runner outputs used for manuscript tables
provides:
  - Updated Tables I/II/IV in IEEE manuscript from freshly regenerated benchmarks
  - Predictive adaptive-router discussion updated to match current baseline outputs
  - Manuscript now compiles in a non-root environment via Tectonic
affects: [paper, evaluation, reproducibility]

# Tech tracking
tech-stack:
  added: []
  patterns: [benchmark artifacts regenerated via benchmark_full_evaluation.py]

key-files:
  created:
    - research_scaling_synthetic.csv
  modified:
    - evaluation/datasets.py
    - evaluation_results.json
    - research_real_200.json
    - research_real_1000.json
    - research_real_2000.json
    - research_real_5000.json
    - paper/HPGCS_IEEE_2026.tex
    - .gitignore

key-decisions:
  - "Treat the adaptive selector as a predictive baseline (baseline_adaptive_router), not a best-of-measured oracle, and align manuscript claims to its actual ratios."
  - "Make LaTeX figure inclusion robust by using \\graphicspath and filename-only \\includegraphics targets."

patterns-established:
  - "Real-data prompt caps are regenerated from datasets/eval_results.json for {200,1000,2000,5000} and directly drive Table I values."
  - "Synthetic scenario table values are regenerated with --n 100 and drive Table II values."

requirements-completed: []

# Metrics
duration: 1h 34m
completed: 2026-04-22
---

# Phase 03 Plan 03: Manuscript Update Summary

**Regenerated real/synthetic benchmark artifacts and updated the IEEE manuscript tables/discussion to match current baseline outputs; also made the manuscript buildable in this environment using Tectonic.**

## Performance

- **Duration:** 1h 34m
- **Started:** 2026-04-22T13:57:27+05:30
- **Completed:** 2026-04-22T15:31:18+05:30
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Updated Table~I (real prompt caps) using regenerated results for \(N\in\{200,1000,2000,5000\}\), including the corrected Adaptive Router ratios (3.02x–3.17x) and dedup plateau near 2.0x.
- Updated Table~II (synthetic scenarios, \(n=100\)) and ensured terminology reflects the predictive router baseline (\texttt{baseline\_adaptive\_router}) rather than an oracle/best-of-measured selector.
- Made the manuscript compile successfully (exit code 0) using a non-root toolchain by adding `\graphicspath{...}` and removing hardcoded `paper/figures/...` paths from `\includegraphics`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rerun benchmarks + update manuscript tables/text** - `6fda4b4` (feat)
2. **Task 2: Compile/build verification (tectonic) + build robustness** - `6593d9e` (docs)

## Benchmark Commands Used

Real-data prompt caps (ShareGPT format, `datasets/eval_results.json`):

- `./.venv/bin/python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 200  --output research_real_200.json  --csv research_real_scaling_200.csv`
- `./.venv/bin/python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 1000 --output research_real_1000.json --csv research_real_scaling_1000.csv`
- `./.venv/bin/python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 2000 --output research_real_2000.json --csv research_real_scaling_2000.csv`
- `./.venv/bin/python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 5000 --output research_real_5000.json --csv research_real_scaling_5000.csv`

Synthetic scenarios:

- `./.venv/bin/python benchmark_full_evaluation.py --n 100 --output evaluation_results.json --csv research_scaling_synthetic.csv`

Manuscript compilation:

- `tectonic -X compile paper/HPGCS_IEEE_2026.tex` (using a workspace-local cache directory)

## Files Created/Modified

- `evaluation/datasets.py` - Fix real dataset extraction for JSON arrays (ShareGPT) by removing accidental generator behavior in `_extract_prompts`.
- `paper/HPGCS_IEEE_2026.tex` - Update Table~I/II/IV values and adaptive-router discussion; add `\graphicspath` and normalize `\includegraphics` paths so compilation works from different working directories.
- `evaluation_results.json`, `research_real_*.json`, `research_scaling_synthetic.csv` - Regenerated benchmark artifacts used as the source of truth for manuscript tables.
- `.gitignore` - Ignore workspace-local Rust/Tectonic caches and LaTeX PDF output.

## Decisions Made

- **Adaptive router language**: Treated the adaptive selector as a predictive router baseline (\texttt{baseline\_adaptive\_router}) and updated text to avoid oracle/best-of-measured claims in results discussion.
- **Build portability**: Added `\graphicspath` and removed directory-qualified `\includegraphics` paths to avoid build failures depending on the compile working directory.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed real-dataset prompt extraction (ShareGPT JSON arrays)**
- **Found during:** Task 1 (benchmark reruns)
- **Issue:** `evaluation/datasets.py::_extract_prompts` contained `yield` in a conditional path, making it a generator function and causing list-based JSON extraction to yield no prompts (leading to a hard failure).
- **Fix:** Refactored streaming handling to return an inner iterator without using `yield` in the outer function; list-based JSON now returns concrete lists correctly.
- **Files modified:** `evaluation/datasets.py`
- **Verification:** Re-ran all 4 real-data benchmarks successfully; loader reports non-zero prompt counts.
- **Committed in:** `6fda4b4`

**2. [Rule 3 - Blocking] Installed a local LaTeX engine to satisfy compilation requirement**
- **Found during:** Task 2 (PDF compilation)
- **Issue:** `pdflatex` was not available in the environment.
- **Fix:** Installed `tectonic` locally and compiled with a workspace-local cache directory; updated `\includegraphics` handling to resolve figure paths robustly.
- **Files modified:** `paper/HPGCS_IEEE_2026.tex`, `.gitignore`
- **Verification:** `tectonic -X compile` exits with `0`.
- **Committed in:** `6593d9e`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both were required to execute the planned verification steps and keep the benchmark pipeline runnable on the real dataset.

## Issues Encountered

- **Tectonic bundle download required expanded network access**: The compile required fetching the default bundle. After enabling network access, compilation succeeded.
- **TeX warnings (underfull/overfull boxes, a UTF-8 warning in `algorithm.sty`)**: These did not prevent successful PDF generation (exit 0).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Manuscript tables and adaptive-router discussion now match the regenerated benchmark artifacts.
- Benchmark pipeline can re-run on `datasets/eval_results.json` without manual `--json-field` overrides.

---
*Phase: 03-manuscript-update*
*Completed: 2026-04-22*

