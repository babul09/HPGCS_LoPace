---
phase: 03-manuscript-update
plan: 03
subsystem: docs
tags: [latex, benchmark, evaluation, tectonic, brotli, zstandard]

# Dependency graph
requires: []
provides:
  - Refreshed real-data (200/1k/2k/5k) and synthetic (n=100) benchmark export artifacts used by manuscript tables
  - Reproducible manuscript compilation helper with pdflatex→tectonic fallback
affects: [paper, reproducibility, evaluation]

# Tech tracking
tech-stack:
  added: []
  patterns: ["Workspace-local tooling via cache/home redirection for sandboxed builds"]

key-files:
  created:
    - paper/compile.sh
  modified:
    - evaluation_results.json
    - research_real_200.json
    - research_real_1000.json
    - research_real_2000.json
    - research_real_5000.json
    - .gitignore

key-decisions:
  - "Use workspace-local caches/home when running tectonic in restricted environments"

patterns-established:
  - "Manuscript builds: prefer system pdflatex, fallback to tectonic when unavailable"

requirements-completed: []

# Metrics
duration: 21m
completed: 2026-04-22
---

# Phase 3 Plan 03: Manuscript Update Summary

**Re-ran real/synthetic benchmarks and refreshed the exported JSON artifacts backing Tables I/II/IV; added a hermetic LaTeX compilation helper for environments without `pdflatex`.**

## Performance

- **Duration:** 21m
- **Started:** 2026-04-22T09:55:00Z
- **Completed:** 2026-04-22T10:16:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Re-executed the benchmark runner against `datasets/eval_results.json` for prompt caps 200/1000/2000/5000 and synthetic `n=100`, regenerating the paper-facing JSON exports.
- Verified the manuscript already reflects the refreshed ratios (including `Zstd + Dict (Isolated)` vs `Zstd + Dict (Cached Edge)` and the `baseline_adaptive_router` terminology) without needing LaTeX edits.
- Ensured the manuscript can be compiled in this environment by adding a `pdflatex`→`tectonic` fallback script.

## Task Commits

Each task was committed atomically:

1. **Task 1: Re-run benchmarks and refresh table exports** - `f4cce8d` (chore)
2. **Task 2: Compile manuscript (pdflatex or equivalent)** - `8b0334c` (chore)

## Files Created/Modified

- `evaluation_results.json` - Refreshed synthetic evaluation export (n=100)
- `research_real_200.json` - Refreshed real-data export (max-prompts=200)
- `research_real_1000.json` - Refreshed real-data export (max-prompts=1000)
- `research_real_2000.json` - Refreshed real-data export (max-prompts=2000)
- `research_real_5000.json` - Refreshed real-data export (max-prompts=5000)
- `paper/compile.sh` - Manuscript compilation helper with `tectonic` fallback
- `.gitignore` - Ignore workspace-local tool/cache directories used by tectonic

## Decisions Made

- Use workspace-local cache/home redirection for `tectonic` so LaTeX builds work in sandboxed/restricted environments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added workspace-local tooling to satisfy missing build dependencies**
- **Found during:** Task 1 (benchmark execution) and Task 2 (PDF compilation)
- **Issue:** Python environment lacked `brotli`/`zstandard`; `pdflatex` was not available.
- **Fix:** Created a local `.venv` to install required Python deps and installed `tectonic` as an equivalent LaTeX engine (used via `paper/compile.sh`).
- **Verification:** Benchmark scripts ran successfully; tectonic compilation completed with exit code 0.
- **Committed in:** `f4cce8d`, `8b0334c`

---

**Total deviations:** 1 auto-fixed (Rule 3 blocking)
**Impact on plan:** All auto-fixes were required to complete the planned tasks in the current environment; no scope creep.

## Issues Encountered

- `pdflatex` not installed in the environment; resolved by using `tectonic` with workspace-local cache directories.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Benchmark exports are refreshed and manuscript compilation is reproducible via `paper/compile.sh`.

---
*Phase: 03-manuscript-update*
*Completed: 2026-04-22*

