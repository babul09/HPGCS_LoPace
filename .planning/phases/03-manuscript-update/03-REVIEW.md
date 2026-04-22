---
phase: 03-manuscript-update
reviewed: 2026-04-22T10:17:46Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - paper/compile.sh
  - .gitignore
  - evaluation_results.json
  - research_real_200.json
  - research_real_1000.json
  - research_real_2000.json
  - research_real_5000.json
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-04-22T10:17:46Z  
**Depth:** standard  
**Files Reviewed:** 7  
**Status:** issues_found

## Summary

Scope is mostly reproducibility tooling (`paper/compile.sh`), `.gitignore` hygiene, and exported/aggregated JSON results. No obvious injection primitives or hardcoded secrets were found. Main actionable issues are around (a) a `.gitignore` filename mismatch that can accidentally commit large/derived artifacts, and (b) execution of a repo-local `tectonic` binary without provenance signaling.

## Warnings

### WR-01: `.gitignore` misses `evaluation_results.json` due to filename mismatch

**File:** `.gitignore:89`  
**Issue:** The ignore entry is `eval_results.json`, but the Phase 3 artifact is `evaluation_results.json`. This can lead to accidentally committing a derived results file (and potentially large diffs) when users regenerate it.  
**Fix:** Add an ignore rule for the actual filename (and optionally keep the short alias).

Suggested patch:

```gitignore
# Generated evaluation outputs
evaluation_results.json
eval_results.json
```

### WR-02: `compile.sh` may execute a repo-local `tectonic` binary without trust/provenance guardrails

**File:** `paper/compile.sh:22-24`  
**Issue:** The script will fall back to executing `${ROOT_DIR}/.cargo-bin/bin/tectonic` if present. This is convenient for hermetic builds, but it also means “running whatever binary is in the repo directory”, which is a common footgun when building from an untrusted checkout or when artifacts are copied in from elsewhere.  
**Fix:** Prefer `command -v tectonic` first (already done), and add an explicit provenance check before executing a repo-local binary, for example:

- Require an opt-in env var, e.g. `ALLOW_LOCAL_TECTONIC=1`
- Or print a prominent warning and require user confirmation (non-interactive builds can use the env var)
- Or verify the binary via checksum stored in-repo (best if you want reproducibility)

Example (env-var gate):

```bash
elif [[ -x "${ROOT_DIR}/.cargo-bin/bin/tectonic" ]]; then
  : "${ALLOW_LOCAL_TECTONIC:=0}"
  if [[ "${ALLOW_LOCAL_TECTONIC}" != "1" ]]; then
    echo "ERROR: Refusing to run repo-local tectonic. Set ALLOW_LOCAL_TECTONIC=1 to override." >&2
    exit 1
  fi
  TECTONIC_BIN="${ROOT_DIR}/.cargo-bin/bin/tectonic"
fi
```

## Info

### IN-01: `compile.sh` does not guarantee stable multi-pass LaTeX output when using `pdflatex`

**File:** `paper/compile.sh:13-17`  
**Issue:** The `pdflatex` path runs a single pass. Some documents need multiple passes for references/TOC/labels to stabilize (and bibliographies may require separate tooling). This is not a security issue, but it can create “it built, but references are wrong” confusion.  
**Fix:** Consider either (a) always using `tectonic` for reproducible builds, or (b) running `pdflatex` twice (or until `.aux` stabilizes) when `pdflatex` is used.

### IN-02: Exported JSON result artifacts are large by nature; consider documenting regeneration + storage expectations

**File:** `research_real_*.json` and `evaluation_results.json` (all)  
**Issue:** These are derived artifacts. If they’re expected to change frequently or be very large, repos often either (a) compress them, (b) store them under a clearly named `artifacts/` directory ignored by default, or (c) use Git LFS.  
**Fix:** Add a short note (README or paper appendix) stating “how to regenerate these JSONs” and whether they should be committed, ignored, or tracked via LFS.

---

_Reviewed: 2026-04-22T10:17:46Z_  
_Reviewer: Claude (gsd-code-reviewer)_  
_Depth: standard_

