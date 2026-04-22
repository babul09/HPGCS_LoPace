# Coding Conventions

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
