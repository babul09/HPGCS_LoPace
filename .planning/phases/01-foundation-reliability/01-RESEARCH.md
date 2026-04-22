# Phase 1: Foundation & Reliability - Research

<objective>
Research how to implement Phase 1: Foundation & Reliability
Answer: "What do I need to know to PLAN this phase well?"
</objective>

## Domain Context
This phase establishes formal testing and memory-safe infrastructure needed before evaluating the Adaptive Selector algorithms. Currently, `benchmark_full_evaluation.py` loads the entire real dataset JSON array into memory before streaming them into `run_experiment()` which calls each baseline model systematically. This produces geometric memory consumption up to O(N^2), limiting benchmarks to <5k prompts.

### 1. Pytest Test Suites (Math Regression Models)
- LoPace's algorithmic confidence is mathematically sound (lossless reproduction) but lacks decoupled CI/automated tests.
- We need regression tests placed in `tests/test_math.py` or similar to strictly assert mathematical guarantees:
  - Zstd hashing predictability (same bytes -> same 64-bit digest hash output).
  - Centroid distance thresholds (`difflib.SequenceMatcher` or delta metric matches).
  - Component reconstruction verification.
- We are actively avoiding full database I/O mocking, strictly relying on mathematical logic constraints as decided in `01-CONTEXT.md`.

### 2. JSONL Native Streaming
- `evaluation/datasets.py` currently builds full lists: `prompts = _extract_prompts(...)`.
- We will transition this to a fully lazy Python Generator yielding one prompt at a time (`yield prompt`).
- `load_multiple_datasets` should be converted into a stream wrapper linking multiple generators without loading them entirely into list objects.
- Datasets structured as nested JSON arrays will be mapped using a custom chunked wrapper or required to be transformed into `.jsonl` directly.

### 3. Execution Pipeline Refactor
- In `evaluation/runner.py`, `run_experiment` currently accepts `prompts: List[str]` and executes:
  1. `baseline_zstd(prompts)` (loads all prompts -> extracts -> compresses).
  2. `baseline_gzip(prompts)`
  ... etc.
- This creates duplicated copies and isolates evaluations from one another, generating massive RAM caches.
- A Prompt-by-Prompt paradigm means we will pull 1 item from the generator, hand it to `baseline_zstd`, `baseline_gzip`, `corpus_dedup`, record metrics per single prompt to a persistent CSV sink, and garbage collect it. This enforces O(1) constraints.

## Validation Architecture
- We will construct the testing framework using `pytest` standard.
- Success requires `python -m pytest` running and verifying deterministic output assertions for components.
- Memory pipelines will be verified by benchmarking the runner over a 50k prompt dummy file without crossing a predefined 1GB memory cap.

*Completed 2026-04-22 — Ready for Planning*
