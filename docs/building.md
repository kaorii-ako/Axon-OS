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
    debootstrap squashfs-tools xorriso \
    grub-pc-bin grub-efi-amd64-bin \
    mtools dosfstools rsync
```

(Optionally add `qemu-system-x86 ovmf` for testing the ISO in a VM.)

## Build Steps

```bash
# 1. Clone the repository
git clone https://github.com/kaorii-ako/Axon-OS.git
cd Axon-OS

# 2. Run the main build script (root required for debootstrap/chroot)
sudo bash build/build.sh
```

The script will:
1. Bootstrap a minimal Ubuntu 24.04 (noble) root filesystem with `debootstrap`.
2. Install the kernel, `casper` (Ubuntu live-boot), GNOME, and all Axon OS components into the chroot (`build/config/chroot-setup.sh`).
3. Apply Axon branding: GTK theme, gschema defaults, Plymouth splash, wallpaper, Calamares installer.
4. Build a SquashFS image of the root filesystem.
5. Wrap everything in a hybrid BIOS + UEFI bootable ISO with GRUB and `xorriso`.

The finished ISO is written to `dist/axon-os-<version>-amd64.iso` with a `.sha256` checksum alongside.

Useful flags / environment:

| Option | Effect |
|--------|--------|
| `--compression=gzip` | Faster squashfs (larger ISO); default is `xz` |
| `--keep-chroot` | Reuse the existing chroot for iterative rebuilds |
| `AXON_BUILD_DIR=/path` | Work directory (default `/tmp/axon-build`, needs ~15 GB) |

## CI Builds (GitHub Actions)

Every push to `main` that touches `build/`, `apps/`, `services/`, `shell/`, `theme/`, `data/`, `installer/`, or `plymouth/` runs the **Build ISO** workflow (`.github/workflows/build-iso.yml`). Download the finished ISO from the workflow run's **Artifacts** section (`axon-os-iso`). Tagged pushes (`v*`) also attach the ISO to a GitHub Release when it fits the 2 GiB asset limit.

## Testing in QEMU

Boot the ISO directly without burning it to media:

```bash
qemu-system-x86_64 \
    -enable-kvm \
    -m 4G \
    -smp 4 \
    -cpu host \
    -drive file=dist/axon-os-0.1.0-amd64.iso,format=raw,if=virtio \
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
    -cdrom dist/axon-os-0.1.0-amd64.iso \
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

## Graphical Installer (Calamares)

Axon OS ships a fully configured [Calamares](https://calamares.io/) graphical installer so users can install the system from the live ISO without using a terminal.

### Installer layout

```
installer/
├── settings.conf                   # Calamares top-level config (module sequence, branding name)
├── branding/
│   └── axon/
│       ├── branding.desc           # Product strings, image paths, accent color (#8b5cf6)
│       ├── AxonSlideshow.qml       # QML slideshow shown during package install
│       ├── logo.png                # Product logo (add your own 256×256 PNG)
│       ├── icon.png                # Product icon  (add your own 64×64 PNG)
│       └── welcome.png             # Welcome screen image (add your own)
└── modules/
    ├── welcome.conf                # Requirement checks (storage ≥ 20 GiB, RAM ≥ 2 GiB)
    └── finished.conf               # Post-install restart command
```

### Install sequence

The installer walks the user through these steps in order:

| Step | Module | Description |
|------|--------|-------------|
| 1 | `welcome` | Requirement checks + language select |
| 2 | `locale` | Timezone and locale |
| 3 | `keyboard` | Keyboard layout |
| 4 | `partition` | Disk partitioning (auto or manual) |
| 5 | `users` | Create user account and hostname |
| 6 | `summary` | Review all choices before writing |
| — | *(exec)* | Partition, unpack, bootloader, locale hooks |
| 7 | `finished` | Done — reboot or stay in live session |

### Build copies Calamares config automatically

`build/build.sh` places the Calamares files in the correct locations inside the chroot overlay:

| Source | Destination in live system |
|--------|---------------------------|
| `installer/settings.conf` | `/etc/calamares/settings.conf` |
| `installer/branding/axon/` | `/usr/share/calamares/branding/axon/` |
| `installer/modules/` | `/etc/calamares/modules/` |

The `calamares` package is included in `build/config/packages.list` so it is installed into the live image automatically.

### Testing the installer in QEMU

Boot the ISO and launch the installer from the welcome app or run:

```bash
sudo calamares
```

Use the virtual-disk QEMU workflow described in the "Testing in QEMU" section below to perform a full end-to-end install test without touching real hardware.

### Customizing branding

1. Replace the placeholder image files (`logo.png`, `icon.png`, `welcome.png`) in `installer/branding/axon/` with your own artwork.
2. Edit `installer/branding/axon/branding.desc` to change `productName`, `version`, or the accent `highlightColor`.
3. Edit `installer/branding/axon/AxonSlideshow.qml` to add or change the slides shown during installation.

---

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
