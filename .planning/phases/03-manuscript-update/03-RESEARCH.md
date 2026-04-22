# Phase 3: Manuscript Update Research

**Objective:**
Update the IEEE LaTeX manuscript (`paper/HPGCS_IEEE_2026.tex`) with the empirical data resulting from our refined benchmark pipelines in Phase 2.

**What needs to happen?**
1. **Benchmark Re-execution**: We must run the formal benchmark (which is now $O(1)$ memory-safe and functionally stable for arrays > 10,000 prompts) on the actual `datasets/eval_results.json` corpus using the exact commands in the Reproducibility section of the paper, generating the formal `.json` and `.csv` metrics.
   - `python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 200`
   - `python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 1000`
   - `python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 2000`
   - `python benchmark_full_evaluation.py --real-data datasets/eval_results.json --max-prompts 5000`
   - `python benchmark_full_evaluation.py --n 100` (Synthetic)
2. **Manuscript Data Merge**: Open `paper/HPGCS_IEEE_2026.tex` and update Table I (Real Caps), Table II (Synthetic Scenarios), Table III (Scaling), and Table IV (Methods Summary) with the new outputs.
   - Importantly, **Zstd + Dict** must be split into `Zstd + Dict (Isolated)` and `Zstd + Dict (Cached Edge)`.
   - The discussion paragraphs regarding the "Adaptive Selector" must be rewritten to reflect its new predictive bound logic rather than the legacy Oracular Array approach.
3. **Data Verification**: Ensure the exact metric floats match what outputs from step 1.

**Validation Architecture (Nyquist):**
- **Validation**: Read `paper/HPGCS_IEEE_2026.tex` using regex to verify `Zstd + Dict (Cached Edge)` exists within the LaTeX table matrix.
- Verify `pdflatex` compilation does not raise format errors (zero syntax collisions).
