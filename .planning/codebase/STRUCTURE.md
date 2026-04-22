# Repository Structure

## Directory Layout
- **`.planning/`**: Agentic operation logic and architectural mapping records.
- **`datasets/`**: Input corpora containing real-world conversational prompt data (e.g., `eval_results.json`).
- **`evaluation/`**: Synthetic load generators, schema parsers, runners, and benchmarking baselines cleanly abstracted from the core algorithm.
- **`frontend/`**: Standard React/Vite client codebase containing Dashboard analytics components (`src/pages/*`).
- **`legacy/`**: Old codebase files and prototype algorithms (e.g., prior `lopace_graph` structures).
- **`lopace/`**: The core production algorithm repository. Handles the core content chunking, deduplication storage logic, delta patches, and parser utilities.
- **`paper/`**: LaTeX repository containing manuscript files, figure images, and references.

## Key Files
- `benchmark_full_evaluation.py`: The CLI application serving as the primary standalone script to execute complete evaluation runs. It depends on `evaluation/` modules.
- `serve_api.py`: FastAPI backend integrating `evaluation/` routes to expose analysis payloads locally.
- `benchmark_corpus_dedup.py`: A supplementary script that targets isolated tests specifically for `CorpusStore`.
- `paper_visualizations.ipynb`: Jupyter file dedicated to rendering Matplotlib figures and graphs extracted from JSON execution runs for paper figures.
- `research_*.csv`/`.json`: Various output artifact metrics capturing previous baseline experiment states.

## Naming Conventions
- Root Python packages are explicitly modularized (`evaluation`, `lopace`).
- Files are primarily named utilizing strictly `snake_case`.
- React UI classes remain strictly Pascal/Camel scaled as standard components.
