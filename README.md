# Axon OS

Axon OS is a bootc image built on [Bazzite](https://bazzite.gg). It keeps Bazzite's gaming stack (Steam, Proton, HDR/VRR, gamescope) and its atomic updates and rollback, and adds GPU checks, local AI with GPU acceleration and Axon branding on top. Images rebuild every day from the latest Bazzite `stable` and are published to GHCR.

## Pick an image

| Image | Desktop | GPU |
|---|---|---|
| `ghcr.io/kaorii-ako/axon-os-nvidia` | KDE Plasma | NVIDIA GTX 16xx / RTX 20xx or newer |
| `ghcr.io/kaorii-ako/axon-os-gnome-nvidia` | GNOME | NVIDIA GTX 16xx / RTX 20xx or newer |
| `ghcr.io/kaorii-ako/axon-os` | KDE Plasma | AMD or Intel |
| `ghcr.io/kaorii-ako/axon-os-gnome` | GNOME | AMD or Intel |

The NVIDIA images use the open kernel modules (`nvidia-open`). RTX 50-series cards only work with these. Cards older than Turing (GTX 10xx and earlier) are not supported; use Bazzite's own `bazzite-nvidia` image for those.

Laptops with an Intel or AMD iGPU plus an NVIDIA dGPU should use an NVIDIA image. The desktop runs on the iGPU and the dGPU powers down when idle; start a game or app on the dGPU with `switcherooctl launch <app>` (Steam's launcher already asks for the dGPU).

## Install

From any Bazzite, Bluefin, Aurora or Fedora Atomic install:

```bash
sudo bootc switch ghcr.io/kaorii-ako/axon-os-nvidia:stable
systemctl reboot
```

Once the image is signed (see below), switch with `--enforce-container-sigpolicy` instead, so the machine refuses unsigned updates.

For a fresh install, run the "Build installer ISO" workflow (Actions tab) and download the ISO from the run's artifacts. The installer points the new system at the GHCR image, so updates come from there.

### Secure Boot

With Secure Boot on, the NVIDIA module will not load until the Universal Blue key is enrolled. Run this once and reboot; at the blue MOK screen choose "Enroll MOK" and type `universalblue`:

```bash
ujust enroll-secure-boot-key
```

## Commands

| Command | What it does |
|---|---|
| `ujust axon-gpu-doctor` | Checks the driver, nouveau, modeset, Secure Boot, CDI and suspend settings and tells you what to fix |
| `ujust axon-ai enable` | Runs Ollama as a system service on your GPU (CUDA on NVIDIA, ROCm on AMD), bound to `127.0.0.1:11434`, auto-updated |
| `ujust axon-ai disable` / `status` | Turns it off (models are kept) / shows state |
| `ujust axon-rebase <nvidia\|amd\|gnome-nvidia\|gnome>` | Switches to another Axon variant |
| `ujust axon-info` | Image, driver and deployment details |

Bazzite's own `ujust` recipes all still work. Updates install in the background; `ujust update` forces one, and `sudo bootc rollback` returns to the previous deployment.

## What the build guarantees

Every image build fails instead of publishing if:

- the base image has more or fewer than one kernel
- an NVIDIA image lacks `nvidia`, `nvidia_modeset`, `nvidia_drm` or `nvidia_uvm` for that kernel
- the kernel module and the userspace driver versions differ
- the module is the closed driver instead of `nvidia-open`
- an AMD image contains the NVIDIA module
- `bootc container lint` fails

NVIDIA images also get kernel arguments for any of these the base does not already set: nouveau blacklisted, `nvidia-drm.modeset=1`, and VRAM preserved across suspend (written to `/var/tmp`, not RAM). The NVIDIA suspend/resume units and CDI generation for GPU containers are enabled.

## Releasing (one-time setup)

1. Generate a signing key and store the private half as a repository secret:

   ```bash
   cosign generate-key-pair
   gh secret set SIGNING_SECRET < cosign.key
   ```

   If you set a key password, also store it: `gh secret set COSIGN_PASSWORD`.
2. Commit `cosign.pub` as `keys/cosign.pub`. Never commit `cosign.key`. From then on images trust only updates signed with that key, and CI refuses to publish if the secret is missing.
3. After the first push to `main`, open each package under your GitHub profile's Packages tab and set its visibility to public. GHCR creates new packages as private, and machines cannot pull private images.

## Building locally

```bash
just variants
just build axon-os-nvidia
just switch-local axon-os-nvidia   # boot your own build on this machine
just iso axon-os-nvidia
just lint
```

## Layout

```
Containerfile            one file for every variant
variants.json            the build matrix: name, base image, GPU, desktop
build_files/steps/       build steps, run in order
build_files/packages.txt extra Fedora packages
system_files/            copied into the image as-is
disk_config/             installer and disk image configs
keys/cosign.pub          image signing key (add it, see above)
```

Adding a variant means adding a row to `variants.json`. Adding a package means adding a line to `packages.txt`.

## License

Apache-2.0. Based on the Universal Blue [image-template](https://github.com/ublue-os/image-template).
