# Phase 1: foundation-reliability - Validation Strategy

**Architecture:** Pytest Deterministic Bounds & Line-by-Line Streaming Generators
**Date:** 2026-04-22

## 1. Nyquist Baseline Generation

To prove this phase works, we need a baseline of "what it looks like when it's right" BEFORE making changes.

**Baseline Commands/Setup:**
- The existing evaluations return lossy dictionary results with no bounds matching. 
- Python `sys.getsizeof()` can be applied to `Prompts = [list of prompts]` from a dummy 50k line JSON dataset BEFORE transitioning to `.jsonl`.
- Memory peaks will be bounded, capturing exactly what baseline system caps at.

## 2. Test Execution Plan

### A. Manual / Setup Tests
- [ ] Create a dummy JSON file (`dummy.jsonl`) with 50,000 artificial prompts (string generation).
- [ ] Monitor standard baseline JSON array import RAM curve (confirm fail or heavy block).

### B. Automated / Scripted Tests
- [ ] `python -m pytest tests/test_math.py` — Verifies exactly 100% test coverage over internal component math hashing logic.
- [ ] `python benchmark_full_evaluation.py --real-data dummy.jsonl` — Must execute streaming evaluations sequentially over O(1) buffer logic to successfully conclude 50,000 points without maxing process memory.

## 3. Rollback Triggers

If any of these conditions are met during testing, we revert the implementation and reconsider the approach:

- **Trigger 1**: Memory usage still scales O(N) when evaluating `baseline_zstd` because of legacy code referencing the list instead of generator explicitly.
- **Trigger 2**: Pytest hash tests are inherently flaky because Zstd dictionaries train non-deterministically across seeds. (Require strict fixed seeds across training layers).
- **Trigger 3**: Execution speed crashes by 10x due to File I/O streaming latency blocking mathematical pipelining loops.
