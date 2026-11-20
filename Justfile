vendor := "kaorii-ako"

[private]
default:
    @just --list

# List the image variants
variants:
    @jq -r '.[] | "\(.name)\t\(.gpu)\t\(.desktop)\t\(.base)"' variants.json | column -t

# Build one variant locally with podman, e.g. just build axon-os-nvidia
build variant="axon-os-nvidia":
    #!/usr/bin/env bash
    set -euo pipefail
    row="$(jq -ce --arg n "{{ variant }}" '.[] | select(.name == $n)' variants.json)" || { echo "unknown variant {{ variant }}" >&2; exit 1; }
    version="$(date -u +%Y%m%d)-$(git rev-parse --short HEAD)"
    podman build \
      --pull=newer \
      --build-arg BASE_IMAGE="$(jq -r .base <<<"$row")" \
      --build-arg IMAGE_NAME="{{ variant }}" \
      --build-arg IMAGE_VENDOR="{{ vendor }}" \
      --build-arg GPU_VENDOR="$(jq -r .gpu <<<"$row")" \
      --build-arg DESKTOP="$(jq -r .desktop <<<"$row")" \
      --build-arg VERSION="$version" \
      --tag "localhost/{{ variant }}:stable" \
      .

# Rebase this machine onto a locally built variant (testing only)
switch-local variant="axon-os-nvidia":
    sudo bootc switch --transport containers-storage "localhost/{{ variant }}:stable"

# Build an installer ISO from a published variant
iso variant="axon-os-nvidia":
    #!/usr/bin/env bash
    set -euo pipefail
    ref="ghcr.io/{{ vendor }}/{{ variant }}:stable"
    mkdir -p output
    flags=""
    [[ -s keys/cosign.pub ]] && flags="--enforce-container-sigpolicy"
    sed -e "s|@IMAGE_REF@|$ref|" -e "s|@SWITCH_FLAGS@|$flags|" disk_config/iso.toml > output/iso.toml
    sudo podman pull "$ref"
    sudo podman run --rm -it --privileged --pull=newer \
      --security-opt label=type:unconfined_t \
      -v ./output:/output \
      -v ./output/iso.toml:/config.toml:ro \
      -v /var/lib/containers/storage:/var/lib/containers/storage \
      quay.io/centos-bootc/bootc-image-builder:latest \
      --type anaconda-iso --use-librepo=True "$ref"

# Lint shell scripts, workflows and this Justfile
lint:
    shellcheck build_files/*.sh build_files/steps/*.sh system_files/usr/bin/axon-gpu-doctor system_files/usr/libexec/axon/*
    just --unstable --fmt --check -f Justfile
