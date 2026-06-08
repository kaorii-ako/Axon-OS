# Axon OS Architecture

## Overview

Axon OS is a minimal, AI-native desktop operating system built on top of a standard Linux base with GNOME Shell as the display environment. The system is designed around three primary user-facing primitives — Spaces, the Intent Bar, and the AI Panel — all of which communicate with a locally-running Ollama inference server that drives on-device language model capabilities. Hardware acceleration is provided directly through the GPU without requiring cloud connectivity, keeping user data entirely on-device.

## Component Diagram

```
┌─────────────────────────────────────────────────────┐
│                      User                           │
└───────────────────────┬─────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │        GNOME Shell         │
          │  ┌──────────┐  ┌────────┐  │
          │  │Intent Bar│  │AI Panel│  │
          │  └────┬─────┘  └───┬────┘  │
          │       │    Spaces  │       │
          │  ┌────▼────────────▼────┐  │
          │  │   Space Manager     │  │
          │  └──────────┬──────────┘  │
          └─────────────┼─────────────┘
                        │  REST / HTTP
          ┌─────────────▼─────────────┐
          │      Ollama Daemon        │
          │   (localhost:11434)       │
          └─────────────┬─────────────┘
                        │  llama.cpp / CUDA / ROCm
          ┌─────────────▼─────────────┐
          │            GPU            │
          └───────────────────────────┘
```

## Spaces

Spaces are persistent, named workspaces that go beyond traditional virtual desktops. Each Space carries its own context: open applications, associated projects, AI conversation history, and a descriptive title set by the user or inferred by the AI Panel. The Space Manager GNOME Shell extension (`shell/space-manager/`) handles creation, switching, and lifecycle of Spaces, persisting state to `~/.axon/spaces.json`.

## Intent Bar

The Intent Bar (`apps/intent-bar/`) is a keyboard-driven command palette that replaces the traditional application launcher. Users type natural-language intents ("open a terminal in the project folder", "summarise my notes") and the bar routes them to either a conventional application action or to the AI Panel backend. It is implemented as a GTK4 popover activated globally via a configurable keybind (default: `Super+Space`).

## AI Panel

The AI Panel (`apps/ai-panel/`) is a persistent sidebar that provides a conversational interface to the locally-running language model. It maintains per-Space conversation threads and can take context-aware actions such as reading the clipboard, summarising the active window title, or executing shell commands after user confirmation. The panel communicates with Ollama over HTTP using the `/api/chat` streaming endpoint.

## Ollama Integration

Axon OS ships Ollama as a systemd user service (`~/.config/systemd/user/ollama.service`). The default model is configured in `~/.axon/config.toml` under the key `DEFAULT_MODEL` (default: `llama3`). Additional models can be pulled with `ollama pull <model>` and will be surfaced automatically in the AI Panel model picker. GPU offloading is auto-detected at runtime; the service falls back to CPU-only inference when no compatible GPU is present.

## Config Directory (`~/.axon/`)

| Path | Purpose |
|------|---------|
| `~/.axon/config.toml` | Primary user configuration (model, keybinds, theme) |
| `~/.axon/spaces.json` | Persisted Space state and conversation history |
| `~/.axon/extensions/` | Third-party GNOME Shell extension overrides |
| `~/.axon/themes/` | Custom GTK / GNOME Shell theme fragments |
| `~/.axon/logs/` | Application and AI Panel debug logs |
