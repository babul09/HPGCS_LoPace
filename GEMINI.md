<!-- GSD:project-start source:PROJECT.md -->
## Project

**PROJECT CONTEXT — HPGCS Audit, Fix, and Paper Update**
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Core Technologies
- **Language**: Python (>=3.8) for backend, JavaScript/React for frontend
- **Backend Framework**: Core libraries, FastAPI (`serve_api.py`)
- **Frontend Framework**: React 19 (`frontend/package.json`), Vite 8
## Compression & Processing
- **Zstandard (`zstandard>=0.22.0`)**: Used for dictionary, per-prompt, and component compression.
- **LZ4 (`lz4>=4.3.3`)**: Fast compression backend.
- **Brotli (`brotli>=1.1.0`)**: Quality-focused text compression backend.
- **Snappy (`python-snappy>=0.7.1`)**: Fast dictionary compression backend.
- **TikToken (`tiktoken>=0.5.0`)**: OpenAI tokenization scheme (BPE mapping for text).
- **Gzip/Deflate**: Built-in Python library use.
## Analytics & Visualisation
- **NetworkX (`networkx>=3.0`)**: Graph processing for prompt references.
- **NumPy (`numpy>=1.24.0`)**: Array manipulations and centroid calculations.
- **Streamlit (`streamlit>=1.28.0`)**: Alternative legacy UI.
- **Plotly & Pandas**: Experimental dataframe analysis and chart plotting.
## Frontend Infrastructure
- **Routing**: `react-router-dom`
- **Icons**: `lucide-react`
- **Build System**: Vite 
- **Linting**: ESLint with React hooks plugins
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Code Style
- Written using mostly Python Type Hinting semantics (e.g., `def _compress_payload(self, packed_tokens: bytes) -> bytes:`).
- `snake_case` utilized globally across the root application logic for functions and variable paths.
- Uses `_` suffix for internal private routing functions (e.g. `_print_scaling_table`).
## Error Handling
- Exceptions are loosely passed and bundled into `FastAPI` standard Error Exceptions with HTTP format triggers inside `serve_api.py`.
- Try-catch fallback chains are used globally for dependency loading (e.g. explicitly mapping missing native components like `zstd` out with `_ZSTD_AVAILABLE=False`). 
## Common Patterns
- Modular decomposition: Moving monolithic structures (like `benchmark_full_evaluation.py`) into smaller domains.
- Lossless verifications: Components strictly enforce integrity checks at runtime by parsing hashed reference outputs against original bytes to ensure true replication.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Core Patterns
## Data Flow
## Abstractions
- **PromptParser**: Transforms unstructured JSON strings into `Segment` hierarchies.
- **Blueprint Mapping**: A list composed of explicit bytes and pointer objects mapping to external nodes.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.agent/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
