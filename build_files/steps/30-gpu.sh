#!/usr/bin/env bash
set -euo pipefail

fail() { echo "::error::$*" >&2; exit 1; }
warn() { echo "::warning::$*" >&2; }

mapfile -t KERNELS < <(find /usr/lib/modules -mindepth 1 -maxdepth 1 -type d -printf '%f\n')
((${#KERNELS[@]} == 1)) || fail "expected exactly one kernel in the image, found: ${KERNELS[*]:-none}"
KVER="${KERNELS[0]}"
echo "Kernel: ${KVER}"

has_kmod() { modinfo -k "${KVER}" "$1" >/dev/null 2>&1; }

if [[ "${GPU_VENDOR}" == "amd" ]]; then
  if has_kmod nvidia; then
    fail "GPU_VENDOR=amd but the base image ships the nvidia kernel module; check BASE_IMAGE (${BASE_IMAGE})"
  fi
  jq -n --arg k "${KVER}" '{gpu: "amd", kernel: $k}' > /usr/share/axon/gpu.json
  echo "AMD/Intel variant: Mesa from the base image, no NVIDIA module present."
  exit 0
fi

for mod in nvidia nvidia_modeset nvidia_drm nvidia_uvm; do
  has_kmod "${mod}" || fail "kernel module ${mod} missing for ${KVER}; the base image's akmods do not match its kernel"
done

KMOD_VERSION="$(modinfo -k "${KVER}" -F version nvidia)"
KMOD_LICENSE="$(modinfo -k "${KVER}" -F license nvidia)"
[[ "${KMOD_LICENSE}" == "Dual MIT/GPL" ]] ||
  fail "expected the open NVIDIA kernel modules (Dual MIT/GPL), got '${KMOD_LICENSE}'. RTX 50-series GPUs only work with nvidia-open."

GLCORE="$(find /usr/lib64 -maxdepth 1 -name 'libnvidia-glcore.so.*' -printf '%f\n' | head -n1)"
[[ -n "${GLCORE}" ]] || fail "NVIDIA userspace (libnvidia-glcore) not found"
USER_VERSION="${GLCORE#libnvidia-glcore.so.}"
[[ "${KMOD_VERSION}" == "${USER_VERSION}" ]] ||
  fail "NVIDIA kernel module ${KMOD_VERSION} does not match userspace ${USER_VERSION}"

GLCORE32="$(find /usr/lib -maxdepth 1 -name 'libnvidia-glcore.so.*' -printf '%f\n' | head -n1)"
[[ -n "${GLCORE32}" ]] || warn "32-bit NVIDIA libraries missing; Steam and Proton games will fall back or fail"

command -v nvidia-smi >/dev/null || fail "nvidia-smi missing"

if [[ -e /usr/share/vulkan/icd.d/nouveau_icd.x86_64.json ]]; then
  warn "nouveau Vulkan ICD still present; removing it so Vulkan picks the NVIDIA driver"
  rm -f /usr/share/vulkan/icd.d/nouveau_icd.*.json
fi

INITRAMFS="/usr/lib/modules/${KVER}/initramfs.img"
if [[ -f "${INITRAMFS}" ]] && command -v lsinitrd >/dev/null; then
  if INITRD_LIST="$(lsinitrd "${INITRAMFS}" 2>/dev/null)" && [[ -n "${INITRD_LIST}" ]]; then
    if grep -qE 'nvidia[-_]drm\.ko' <<<"${INITRD_LIST}"; then
      echo "initramfs carries nvidia-drm (early KMS)"
    else
      echo "initramfs does not carry nvidia-drm; the driver loads after switch-root (normal for Bazzite)"
    fi
  else
    echo "could not list the initramfs; skipping the early-KMS check"
  fi
fi

karg_known() {
  grep -rqsF -- "$1" /usr/lib/bootc/kargs.d /usr/lib/modprobe.d /etc/modprobe.d /usr/libexec 2>/dev/null
}

ADD_KARGS=()
for karg in rd.driver.blacklist=nouveau modprobe.blacklist=nouveau nvidia-drm.modeset=1; do
  karg_known "${karg}" || ADD_KARGS+=("${karg}")
done
if ! karg_known PreserveVideoMemoryAllocations; then
  ADD_KARGS+=("nvidia.NVreg_PreserveVideoMemoryAllocations=1" "nvidia.NVreg_TemporaryFilePath=/var/tmp")
fi

if ((${#ADD_KARGS[@]})); then
  mkdir -p /usr/lib/bootc/kargs.d
  {
    printf 'kargs = ['
    printf '"%s", ' "${ADD_KARGS[@]}" | sed 's/, $//'
    printf ']\nmatch-architectures = ["x86_64"]\n'
  } > /usr/lib/bootc/kargs.d/50-axon-nvidia.toml
  echo "Added kargs:"; cat /usr/lib/bootc/kargs.d/50-axon-nvidia.toml
else
  echo "Base image already sets the NVIDIA kernel arguments."
fi

for unit in nvidia-suspend nvidia-resume nvidia-hibernate nvidia-suspend-then-hibernate; do
  if [[ -f "/usr/lib/systemd/system/${unit}.service" ]]; then
    systemctl enable "${unit}.service"
  fi
done

if [[ -x /usr/bin/nvidia-ctk ]]; then
  if [[ -f /usr/lib/systemd/system/ublue-nvctk-cdi.service ]]; then
    systemctl enable ublue-nvctk-cdi.service
  else
    systemctl enable axon-nvidia-cdi.service
  fi
else
  warn "nvidia-container-toolkit missing; GPU containers (axon-ai) will not see the GPU"
fi

jq -n \
  --arg k "${KVER}" \
  --arg kmod "${KMOD_VERSION}" \
  --arg user "${USER_VERSION}" \
  --arg lic "${KMOD_LICENSE}" \
  '{gpu: "nvidia", kernel: $k, kmod_version: $kmod, userspace_version: $user, kmod_license: $lic}' \
  > /usr/share/axon/gpu.json

echo "NVIDIA ${KMOD_VERSION} (open modules) verified for kernel ${KVER}"
