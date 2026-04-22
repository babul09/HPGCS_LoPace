# Testing

## Frameworks
- Pytest is ostensibly expected based on the existence of `.pytest_cache`, however strict test files are missing from the root component hierarchy. 

## Structure
- Explicit testing is performed through end-to-end execution of `benchmark_full_evaluation.py` and verifying its JSON extraction payloads, rather than isolated TDD module tests.
- Internal tests consist of exact deterministic matching checks inside `lopace` engine tools (like the Assertions verifying `h(p_i)$` logic dynamically during runtime).

## Mocking & Coverage
- Lack of formalized unit tests results in negligible strict Coverage bounds. End-to-end integration drives 95%+ coverage on evaluation scripts manually via CLI operations.
