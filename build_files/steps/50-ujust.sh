#!/usr/bin/env bash
set -euo pipefail

JUSTFILE=/usr/share/ublue-os/justfile
IMPORT='import "/usr/share/ublue-os/just/60-axon.just"'

if [[ ! -f "${JUSTFILE}" ]]; then
  echo "::warning::${JUSTFILE} not found; ujust axon-* recipes will not be available"
  exit 0
fi

grep -qxF "${IMPORT}" "${JUSTFILE}" || echo "${IMPORT}" >> "${JUSTFILE}"

if command -v just >/dev/null; then
  just --justfile "${JUSTFILE}" --summary | tr ' ' '\n' | grep -q '^axon-gpu-doctor$' ||
    { echo "::error::axon recipes did not load into ${JUSTFILE}" >&2; exit 1; }
fi
