# Architecture

## Core Patterns
The Hybrid Prompt Graph Compression System (HPGCS/LoPace) pipeline follows a strict Data Flow transformation pattern designed to de-duplicate sequences of token structures across independent requests.

1. **Parser Layer (`lopace/parser.py`)**: Responsible for segmenting raw text inputs into logical reference chunks (like system instructions and templates) vs unique chunks (like immediate user data).
2. **Component Stores Layer (`lopace/*_store.py`)**: 
   - `corpus_store.py`: Centralized Content Addressed Deduplication logic mapping segments to hash-references and building literal-reference blueprints.
   - `delta_store.py`: Centroid-based relative difference engine to store strings via sequence patch overlays.
   - `adaptive_store.py`: Router analyzing prompt traits to route towards baseline compressors or dedup.
3. **Compression Engine (`lopace/compressor.py`)**: A generalized wrapper providing unified execution pipelines across Zstandard, Brotli, gzip, etc.
4. **Evaluation Wrapper (`evaluation/*.py`)**: 
   - `datasets.py` & `data_generators.py`: Simulation systems executing generation of artificial load and dataset parsing.
   - `runner.py` & `baselines.py`: Unified interface measuring empirical storage performance.
5. **Presentation Layer**: Exposes analysis metrics as an HTTP API via FastAPI `serve_api.py`, which is dynamically ingested by a `React` frontend in `frontend/`.

## Data Flow
`User Input` -> `serve_api.BenchmarkRequest` -> `evaluation.runner` -> `Parser/Compressor variants` -> `Storage Engine Metrics` -> `Evaluation JSON` -> `React UI`

## Abstractions
- **PromptParser**: Transforms unstructured JSON strings into `Segment` hierarchies.
- **Blueprint Mapping**: A list composed of explicit bytes and pointer objects mapping to external nodes.
