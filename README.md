# Axon OS

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build & Lint](https://github.com/kaorii-ako/Axon-OS/actions/workflows/build.yml/badge.svg)](https://github.com/kaorii-ako/Axon-OS/actions/workflows/build.yml)

Axon OS is a local-first, AI-native Linux distribution built on Ubuntu 24.04 LTS. Every AI capability runs entirely on-device through Ollama — no cloud accounts, no API keys, no data leaving your machine. It ships a purpose-built GNOME Shell environment with named workspaces, an intent-driven command bar, and a persistent AI side panel, giving you a cohesive experience where the operating system understands natural language without ever phoning home.

## Screenshots

> Screenshots coming soon. ISO build and desktop preview images will be added here once the first release candidate is available.

## Features

- **Spaces (Super+1-9)** — Named workspaces let you organise open windows by project or context. Each space can be labelled (e.g. "Code", "Research", "Chat") and instantly switched with a single keyboard shortcut.
- **Intent Bar (Super+Space)** — A floating command bar that accepts natural-language input and maps it to system actions, app launches, and shell commands, powered by the local Ollama model.
- **AI Panel (Super+A)** — A slide-in side panel that exposes a persistent conversation with the local AI assistant. Use it for summarisation, drafting, code help, or any freeform query — all offline.
- **Local Ollama AI** — All inference runs locally via Ollama. The default model is `llama3.2:3b`, chosen for low VRAM requirements, but any Ollama-compatible model can be substituted in settings.
- **GTK4 + libadwaita theming** — Native GNOME components with a custom Axon theme built on libadwaita for crisp HiDPI rendering and smooth dark/light mode transitions.
- **Zero cloud dependency** — No telemetry, no mandatory accounts, no remote inference endpoints.

## Installation

### From ISO (recommended)

1. Download the latest `.iso` from the [Releases](https://github.com/kaorii-ako/Axon-OS/releases) page.
2. Flash to a USB drive (replace `/dev/sdX` with your device):
   ```bash
   sudo dd if=axon-os.iso of=/dev/sdX bs=4M status=progress oflag=sync
   ```
3. Boot from the USB and follow the guided installer.

### From Source (development / testing)

```bash
# Clone the repository
git clone https://github.com/kaorii-ako/Axon-OS.git
cd Axon-OS

# Install Python runtime dependency
pip install httpx

# Run the shell extensions in-place (requires GNOME session)
python3 -m shell.axon-shell
```

> Note: running from source requires an existing Ubuntu 24.04 GNOME session and Ollama installed separately (`curl -fsSL https://ollama.com/install.sh | sh`).

## Building

Full build instructions — including how to produce a bootable ISO with the custom installer and Plymouth splash — are documented in [docs/building.md](docs/building.md).

## Tech Stack

| Component | Version / Detail |
|-----------|-----------------|
| Base OS | Ubuntu 24.04 LTS |
| Desktop | GNOME Shell |
| UI Toolkit | GTK4 + libadwaita |
| Shell extensions | Python 3.11+ |
| AI runtime | Ollama |
| Default model | llama3.2:3b |

## Contributing

Contributions are welcome. Please open an issue first to discuss significant changes. For smaller fixes, a pull request with a clear description is sufficient. All Python code must pass `ruff check` and all shell scripts must pass `shellcheck` before merging (enforced by CI).

1. Fork the repository and create a feature branch.
2. Make your changes, ensuring CI passes locally where possible.
3. Open a pull request against `main`.

## License

Axon OS is released under the [MIT License](LICENSE).  
Copyright (c) 2024 Axon OS Contributors.
