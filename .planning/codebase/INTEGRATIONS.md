# Integrations

## External Services
There are no external SaaS systems actively deployed other than what may be needed for data generation (e.g. if OpenAI/Anthropic APIs are used for real-data parsing context). The primary workload runs purely locally as an evaluation suite.

## Data Sources
- **WildChat Dataset**: Evaluated on `datasets/eval_results.json` which contains large JSON-structured LLM conversation logs (system templates, tool parameters, user responses).
- **ShareGPT & Alpaca Formats**: Parsers implicitly rely on these JSON schemas for extracting sequential turns.

## Framework Integrations
- **FastAPI / Uvicorn**: Local server runs via `serve_api.py` exposing the evaluation endpoints.
- **REST APIs**: `serve_api.py` operates a `/api/benchmark` integration used by the React Dashboard frontend to issue dynamic workloads.
