#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE_NAME:?}" "${IMAGE_VENDOR:?}" "${GPU_VENDOR:?}" "${DESKTOP:?}" "${BASE_IMAGE:?}"
export IMAGE_NAME IMAGE_VENDOR GPU_VENDOR DESKTOP BASE_IMAGE
export IMAGE_TAG="${IMAGE_TAG:-stable}" VERSION="${VERSION:-dev}"

case "${GPU_VENDOR}" in
  nvidia | amd) ;;
  *) echo "GPU_VENDOR must be nvidia or amd, got '${GPU_VENDOR}'" >&2; exit 1 ;;
esac

for step in /ctx/build_files/steps/*.sh; do
  echo "::group::$(basename "${step}")"
  bash -euo pipefail "${step}"
  echo "::endgroup::"
done
