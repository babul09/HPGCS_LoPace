# Phase 2: Algorithmic Refinement - Research

<objective>
Research how to implement Phase 2: Algorithmic Refinement
Targeting zero-reuse Zstd overhead tracking (EVAL-01) and heuristic boundary implementation in the Meta-Selector (EVAL-02).
</objective>

## 1. Zstd Dictionary Overhead (EVAL-01)

*Current State*:
In `baseline_zstd_dictionary`, the dictionary cost is explicitly `131,072 bytes (128KB)` and appended to the final ratio logic:
`ratio_with_dict = total_orig / (total_comp + dict_overhead)`
The evaluation runner explicitly extracts `total_compressed` rather than `total_with_dict_overhead` causing a misalignment where the table indicates high stored efficiency but low saving percentages. Additionally, it penalizes *small* or zero-reuse domains heavily because 128KB overrides total payload footprints entirely. 

*Refinement*:
We must track "amortized payload bounds". If evaluating broadcast logic (where dictionary is cached at the edge), dictionary byte requirements should NOT reduce iterative `savings_pct` artificially. The runner should explicitly decouple `zstd_dict_cached` vs `zstd_dict_isolated` logic, reporting the cached broadcast cost (ignoring dict overhead) alongside the standard raw transmission overhead.

## 2. Meta-Selector Heuristics (EVAL-02)

*Current State*:
`evaluation/runner.py`'s `[7/7] Adaptive Strategy Selector` is a "Magic Oracle". It retrospectively parses the `results` array and just outputs whichever algorithm scored highest at the very end.
This is logically cheating: A real system cannot compress via every method and *then* pick the best without running latency costs to the ground.

*Refinement*:
The Adaptive Meta-Selector must use predictive threshold bounds (measured off string sizes or subset features) without testing compressions.
For instance:
- `size < 200`: Route to `brotli`
- `200 < size < 1500`: Route to `zstd`
- `size > 1500`: Route to `corpus_dedup` chunking logic.

This requires defining `adaptive_fast_heuristic(prompt)` inside `baselines.py` that processes the prompt directly, bypassing array sweeping evaluations.
