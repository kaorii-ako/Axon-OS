# Axon OS recipes

# Show which Axon image, driver and kernel this machine runs
[group("Axon")]
axon-info:
    #!/usr/bin/env bash
    jq . /usr/share/ublue-os/image-info.json
    jq . /usr/share/axon/gpu.json 2>/dev/null || true
    bootc status --booted 2>/dev/null | head -20 || rpm-ostree status --booted

# Check the GPU driver, Secure Boot, CDI and suspend setup
[group("Axon")]
axon-gpu-doctor:
    /usr/bin/axon-gpu-doctor

# Local AI with GPU acceleration: enable, disable or status
[group("Axon")]
axon-ai action="status":
    #!/usr/bin/env bash
    if [[ "{{ action }}" == "status" ]]; then
        /usr/libexec/axon/axon-ai status
    else
        sudo /usr/libexec/axon/axon-ai "{{ action }}"
    fi

# Switch to another Axon variant: nvidia, amd, gnome-nvidia or gnome
[group("Axon")]
axon-rebase variant:
    #!/usr/bin/env bash
    set -euo pipefail
    case "{{ variant }}" in
        nvidia) NAME=axon-os-nvidia ;;
        amd) NAME=axon-os ;;
        gnome-nvidia) NAME=axon-os-gnome-nvidia ;;
        gnome) NAME=axon-os-gnome ;;
        *) echo "Unknown variant '{{ variant }}'. Use nvidia, amd, gnome-nvidia or gnome." >&2; exit 2 ;;
    esac
    VENDOR="$(jq -r '."image-vendor"' /usr/share/ublue-os/image-info.json)"
    TAG="$(jq -r '."image-tag"' /usr/share/ublue-os/image-info.json)"
    if [[ -f "/etc/pki/containers/${VENDOR}-axon.pub" ]]; then
        sudo bootc switch --enforce-container-sigpolicy "ghcr.io/${VENDOR}/${NAME}:${TAG}"
    else
        sudo bootc switch "ghcr.io/${VENDOR}/${NAME}:${TAG}"
    fi
    echo "Reboot to finish switching to ${NAME}."
