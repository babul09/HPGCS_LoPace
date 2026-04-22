# Phase 1: Foundation & Reliability - Context

**Gathered:** 2026-04-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Establish formal tests and memory-safety parameters for the benchmark environment. Specifically targeting Pytest suites for deterministic math validation and unpaged JSON memory bounds.
</domain>

<decisions>
## Implementation Decisions

### Testing Scope
- **Isolated math validations only** — The `pytest` suite will strictly cover regression tests purely for Zstd hash mapping, centroid patching, dictionary generations, and blueprint reconstructions. E2E simulated evaluations inside SQLite are deferred to manual CLI usage.

### JSON Streaming
- **Migrate to `.jsonl` natively** — We will rely on `.jsonl` line-by-line streaming using standard Python iterators. This avoids the heavy C-bindings of `ijson` and prevents 10k array memory overhead crashes.

### Evaluation Pipelining
- **Prompt-by-Prompt streaming** — Evaluate synchronously per prompt. Stream 1 prompt chunk -> pass through all comparison algorithms iteratively -> lock metrics -> stream next prompt. This solidifies absolute O(1) minimum memory footprint.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Foundational Documents
- `.planning/PROJECT.md` — Project definition
- `PROJECT_CONTEXT.md` — System architecture layout
</canonical_refs>

<deferred>
## Deferred Ideas

- Full simulated end-to-end SQLite integration tests nested inside pure automated CI/CD runners (deferred beyond Phase 1 testing scope focus).
</deferred>

---

*Phase: 01-foundation-reliability*
