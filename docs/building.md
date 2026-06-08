# Building Axon OS

## Prerequisites

- **Host OS:** Ubuntu 24.04 LTS (other Debian-based distros may work but are untested)
- **Disk space:** 20 GB free in the build directory
- **RAM:** 8 GB minimum (16 GB recommended for parallel builds)
- **CPU:** x86-64, 4+ cores recommended
- **Network:** required for initial package fetch; subsequent builds are offline-capable

## Install Build Dependencies

```bash
sudo apt-get update
sudo apt-get install -y \
    git curl wget \
    build-essential meson ninja-build cmake \
    python3 python3-pip python3-venv \
    squashfs-tools xorriso isolinux \
    debootstrap schroot \
    qemu-system-x86 qemu-utils ovmf \
    grub-efi-amd64-bin grub-common \
    libgtk-4-dev libadwaita-1-dev \
    gjs gir1.2-gjs-1.0 \
    shellcheck ruff \
    parted dosfstools e2fsprogs
```

## Build Steps

```bash
# 1. Clone the repository
git clone https://github.com/axonos/axon-os.git
cd axon-os

# 2. Enter the build directory
cd build

# 3. Run the main build script
bash build.sh
```

The script will:
1. Bootstrap a minimal Debian/Ubuntu root filesystem with `debootstrap`.
2. Install GNOME, Ollama, and all Axon OS components into the chroot.
3. Copy the Plymouth splash theme.
4. Build a SquashFS image of the root filesystem.
5. Wrap everything in a bootable ISO with GRUB EFI and BIOS support.

The finished ISO is written to `build/output/axon-os-<date>.iso`.

## Testing in QEMU

Boot the ISO directly without burning it to media:

```bash
qemu-system-x86_64 \
    -enable-kvm \
    -m 4G \
    -smp 4 \
    -cpu host \
    -drive file=build/output/axon-os-$(date +%Y%m%d).iso,format=raw,if=virtio \
    -bios /usr/share/ovmf/OVMF.fd \
    -vga virtio \
    -display gtk,gl=on \
    -net nic,model=virtio \
    -net user \
    -boot d
```

For a persistent install test, create a virtual disk first:

```bash
qemu-img create -f qcow2 axon-test.qcow2 20G

qemu-system-x86_64 \
    -enable-kvm \
    -m 4G \
    -smp 4 \
    -cpu host \
    -drive file=axon-test.qcow2,format=qcow2,if=virtio \
    -cdrom build/output/axon-os-$(date +%Y%m%d).iso \
    -bios /usr/share/ovmf/OVMF.fd \
    -vga virtio \
    -display gtk,gl=on \
    -net nic,model=virtio \
    -net user \
    -boot d
```

## Docker Build (Reproducible)

A `Dockerfile` in the repository root provides a fully reproducible build environment:

```bash
# Build the image
docker build -t axonos-builder .

# Run the build inside the container
docker run --rm \
    --privileged \
    -v "$(pwd)/build/output:/output" \
    axonos-builder \
    bash build.sh

# The ISO is placed in ./build/output/
```

> Note: `--privileged` is required for `debootstrap` and loop-device operations inside the container. Rootless Docker is not supported for the build stage.

## Customization Guide

### Package List

Add or remove packages from the installed system by editing `build/packages.list`. Each non-empty, non-comment line is passed to `apt-get install` inside the chroot.

```
# Extra packages example
neovim
htop
ollama-model-mistral
```

### GTK Theme

The default dark stylesheet is at `theme/gtk-dark.css`. Override variables at the top of the file — all colors use CSS custom properties:

```css
:root {
  --accent-color: #a78bfa;   /* violet — change to taste */
  --bg-color:     #0d0d10;
}
```

### Default AI Model

Change the model that loads on first boot by setting `DEFAULT_MODEL` in `build/firstboot.sh`:

```bash
DEFAULT_MODEL="llama3"        # change to e.g. mistral, phi3, gemma2
```

The variable is written into `~/.axon/config.toml` for the default user during first-boot setup.

### First-Boot Script

`build/firstboot.sh` runs once as root on the installed system's first boot (via a systemd one-shot unit). Use it to seed configuration, pull additional Ollama models, or run post-install hooks:

```bash
# Pull an additional model on first boot
ollama pull nomic-embed-text
```
