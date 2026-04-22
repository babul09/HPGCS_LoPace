---
wave: 1
depends_on: []
files_modified:
  - tests/test_math.py
  - evaluation/datasets.py
  - evaluation/baselines.py
  - evaluation/runner.py
  - benchmark_full_evaluation.py
autonomous: true
---

# Phase 1: Foundation & Reliability - Plan

## Goal
Establish formal tests and memory-safety parameters for the benchmark environment. Specifically targeting Pytest suites for deterministic math validation and unpaged JSON memory bounds.

## Requirements Addressed
- TEST-01: Establish robust test-suites using explicit mathematical parameters to assure system predictability over lossy centroids (pytest).
- EVAL-03: Refactor the evaluation bench marker to use stream memory structures (avoid 10k array memory scale limits).

## Tasks

### 1. Create Pytest Math Regressions
Establish strict validation boundaries on system math to prove components act deterministically.

<read_first>
- lopace/adaptive_store.py
- lopace/delta_store.py
- lopace/corpus_store.py
</read_first>
<action>
Create `tests/test_math.py`. Add Pytest fixtures to mathematically assert the behavior of core logic without spinning up full databases. Specifically assert:
1. `zstandard` hashing logic (does a fixed bytes string hash to the expected fixed 64-bit output).
2. Delta diff metrics (mock arrays to see if they yield expected float overlap logic).
3. Component dictionary generation logic boundaries.
</action>
<acceptance_criteria>
- `tests/test_math.py` contains `def test_zstd_hashing(`
- `python -m pytest tests/test_math.py` exits 0 (all assert limits pass)
</acceptance_criteria>

### 2. Stream Data Using JSONL Native Yield Iterators
Refactor data pipelines from eager memory-loaded arrays into O(1) Generators.

<read_first>
- evaluation/datasets.py
</read_first>
<action>
Modify `_extract_prompts` and `load_real_dataset` inside `evaluation/datasets.py` to `yield` extracted prompts using generators to bypass in-memory structures. Return the Generator iterators correctly. Provide a conversion utility to quickly transform legacy JSON arrays to `.jsonl` directly. Change `prompts` type from `List[str]` to `Iterator[str]`.
</action>
<acceptance_criteria>
- `evaluation/datasets.py` contains `yield from` or `yield` specifically referencing the lazy loading pipeline limits.
</acceptance_criteria>

### 3. Pipeline O(1) Stream Benchmarks
Update runner logic to benchmark iterators linearly.

<read_first>
- evaluation/baselines.py
- evaluation/runner.py
- benchmark_full_evaluation.py
</read_first>
<action>
Update signatures in `evaluation/baselines.py` (e.g. `baseline_zstd`, `corpus_dedup_method`) to consume generators instead of arrays. Update `run_experiment()` inside `evaluation/runner.py` to lock metrics incrementally and pipeline the stream rather than processing all benchmarks against a loaded memory `List`. Allow generators to loop or be recreated per experiment inside `benchmark_full_evaluation.py`.
</action>
<acceptance_criteria>
- `baseline_zstd` explicitly reads values linearly and applies the prompt evaluation synchronously.
- `benchmark_full_evaluation.py` memory size stays <200MB natively while traversing `.jsonl` outputs via memory dumps.
</acceptance_criteria>

## Verification
- Run `python -m pytest tests/test_math.py`.
- Run `benchmark_full_evaluation.py --real-data <dummy_large.jsonl>`.
- Assert O(1) bound RAM limit holds properly for 50k line inputs limit.
