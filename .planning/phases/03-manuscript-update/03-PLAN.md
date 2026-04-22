---
wave: 1
depends_on: []
files_modified: ["paper/HPGCS_IEEE_2026.tex"]
autonomous: true
---

# Phase 3: Manuscript Update

<task>
  <read_first>
    - paper/HPGCS_IEEE_2026.tex
    - benchmark_full_evaluation.py
  </read_first>
  <action>
    Run the real-data baseline evaluations recursively using `benchmark_full_evaluation.py` targeting `datasets/eval_results.json` strictly to output CSV/JSON bounds. Run the benchmark across `--max-prompts 200`, `1000`, `2000` and `5000` arrays and collect the metrics printed. Use these metrics to overwrite Table 1 (Real Data Summary), Table 2 (Synthetic Scenarios) and Table 4 (Complete Method Comparison) inside `paper/HPGCS_IEEE_2026.tex`. Replace legacy oracle terms with the predictive `baseline_adaptive_router` references within the text discussion. Introduce the new separated `Zstd + Dict (Isolated)` vs `Zstd + Dict (Cached Edge)` split directly mapping against baseline array outputs in all metric references. Keep unchanged rows where relevant.
  </action>
  <acceptance_criteria>
    - `paper/HPGCS_IEEE_2026.tex` contains new explicit table labels (`Zstd + Dict (Cached Edge)` and `Zstd + Dict (Isolated)`).
    - `paper/HPGCS_IEEE_2026.tex` contains modified empirical ratio floats corresponding to generated benchmark exports rather than old metrics.
    - Adaptive selector mechanism is described logically omitting oracle legacy definitions.
  </acceptance_criteria>
</task>

<task>
  <read_first>
    - paper/HPGCS_IEEE_2026.tex
  </read_first>
  <action>
    Execute pdf compilation targeting `paper/HPGCS_IEEE_2026.tex` using `pdflatex` or similar environment constraints ensuring structural tables align losslessly. 
  </action>
  <acceptance_criteria>
    - pdf compilation exits with `0` guaranteeing matrix alignment and strict code blocks exist securely without syntax breaks.
  </acceptance_criteria>
</task>

## Verification
1. `paper/HPGCS_IEEE_2026.tex` must be fully documented and updated with Phase 2 capabilities.
2. Ensure there are no LaTeX syntax formatting errors caused by multi-line column replacements.
