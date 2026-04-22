#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAPER_DIR="${ROOT_DIR}/paper"
TEX_FILE="${PAPER_DIR}/HPGCS_IEEE_2026.tex"

if [[ ! -f "${TEX_FILE}" ]]; then
  echo "ERROR: Missing TeX file: ${TEX_FILE}" >&2
  exit 1
fi

if command -v pdflatex >/dev/null 2>&1; then
  cd "${PAPER_DIR}"
  pdflatex -interaction=nonstopmode -halt-on-error "HPGCS_IEEE_2026.tex"
  exit 0
fi

TECTONIC_BIN=""
if command -v tectonic >/dev/null 2>&1; then
  TECTONIC_BIN="$(command -v tectonic)"
elif [[ -x "${ROOT_DIR}/.cargo-bin/bin/tectonic" ]]; then
  TECTONIC_BIN="${ROOT_DIR}/.cargo-bin/bin/tectonic"
fi

if [[ -z "${TECTONIC_BIN}" ]]; then
  cat >&2 <<'EOF'
ERROR: Neither pdflatex nor tectonic is available.

Install one of:
  - TeX Live (pdflatex), or
  - tectonic (recommended for hermetic builds):
      export CARGO_HOME="$PWD/.cargo"
      cargo install tectonic --locked --root "$PWD/.cargo-bin"
EOF
  exit 1
fi

mkdir -p "${ROOT_DIR}/.tectonic-cache" "${ROOT_DIR}/.tectonic-home"
HOME="${ROOT_DIR}/.tectonic-home" \
XDG_CACHE_HOME="${ROOT_DIR}/.tectonic-cache" \
TECTONIC_CACHE_DIR="${ROOT_DIR}/.tectonic-cache" \
  "${TECTONIC_BIN}" -X compile "${TEX_FILE}"

