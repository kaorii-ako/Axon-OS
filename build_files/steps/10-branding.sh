#!/usr/bin/env bash
set -euo pipefail

FEDORA_VERSION="$(rpm -E %fedora)"
IMAGE_REF="ostree-image-signed:docker://ghcr.io/${IMAGE_VENDOR}/${IMAGE_NAME}"
if [[ ! -s /ctx/keys/cosign.pub ]]; then
  IMAGE_REF="ostree-unverified-registry:ghcr.io/${IMAGE_VENDOR}/${IMAGE_NAME}"
fi

mkdir -p /usr/share/ublue-os /usr/share/axon
BASE_INFO="/usr/share/ublue-os/image-info.json"
BASE_NAME="bazzite"
if [[ -f "${BASE_INFO}" ]]; then
  BASE_NAME="$(jq -r '."image-name" // "bazzite"' "${BASE_INFO}")"
  cp "${BASE_INFO}" /usr/share/axon/base-image-info.json
fi

jq -n \
  --arg name "${IMAGE_NAME}" \
  --arg vendor "${IMAGE_VENDOR}" \
  --arg ref "${IMAGE_REF}" \
  --arg tag "${IMAGE_TAG}" \
  --arg base "${BASE_NAME}" \
  --arg base_ref "${BASE_IMAGE}" \
  --arg fedora "${FEDORA_VERSION}" \
  --arg version "${VERSION}" \
  --arg gpu "${GPU_VENDOR}" \
  --arg desktop "${DESKTOP}" \
  '{
    "image-name": $name,
    "image-vendor": $vendor,
    "image-ref": $ref,
    "image-tag": $tag,
    "image-branch": "stable",
    "base-image-name": $base,
    "base-image-ref": $base_ref,
    "fedora-version": $fedora,
    "version": $version,
    "version-pretty": ("Axon OS " + $version),
    "gpu-vendor": $gpu,
    "desktop": $desktop
  }' > "${BASE_INFO}"

OS_RELEASE=/usr/lib/os-release
set_field() {
  local key="$1" value="$2"
  if grep -q "^${key}=" "${OS_RELEASE}"; then
    sed -i "s|^${key}=.*|${key}=\"${value}\"|" "${OS_RELEASE}"
  else
    echo "${key}=\"${value}\"" >> "${OS_RELEASE}"
  fi
}

set_field NAME "Axon OS"
set_field PRETTY_NAME "Axon OS ${VERSION} (${DESKTOP^^}, ${GPU_VENDOR^^})"
set_field VARIANT "${DESKTOP^^} ${GPU_VENDOR^^}"
set_field VARIANT_ID "${IMAGE_NAME}"
set_field IMAGE_ID "${IMAGE_NAME}"
set_field IMAGE_VERSION "${VERSION}"
set_field HOME_URL "https://github.com/${IMAGE_VENDOR}/Axon-OS"
set_field DOCUMENTATION_URL "https://github.com/${IMAGE_VENDOR}/Axon-OS#readme"
set_field SUPPORT_URL "https://github.com/${IMAGE_VENDOR}/Axon-OS/issues"
set_field BUG_REPORT_URL "https://github.com/${IMAGE_VENDOR}/Axon-OS/issues"
set_field DEFAULT_HOSTNAME "axon"
set_field BOOTLOADER_NAME "Axon OS ${VERSION}"

echo "Axon OS release ${FEDORA_VERSION} (${DESKTOP^^})" > /etc/system-release

grep -E '^(NAME|PRETTY_NAME|ID|ID_LIKE|VARIANT_ID|IMAGE_ID)=' "${OS_RELEASE}"
