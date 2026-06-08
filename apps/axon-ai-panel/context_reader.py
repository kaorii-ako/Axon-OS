"""
context_reader.py — ContextReader for Axon AI Panel.

Gathers ambient context from the running desktop session so that the AI
assistant has useful information without the user having to copy/paste.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Optional


class ContextReader:
    """Collects desktop-level context for the AI panel system prompt."""

    # ------------------------------------------------------------------ #
    #  Active window
    # ------------------------------------------------------------------ #

    def get_active_window_title(self) -> Optional[str]:
        """Return the title of the currently focused X11 window, or None."""
        try:
            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            title = result.stdout.strip()
            return title if title else None
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    #  Open files in text editors
    # ------------------------------------------------------------------ #

    def get_open_files_in_editors(self) -> list[str]:
        """
        Scan /proc for known editor processes and return up to 10 unique
        file paths that those processes have open.
        """
        editor_names: set[str] = {"gedit", "code", "vim", "nvim", "nano"}
        found_pids: list[int] = []

        try:
            proc_path = Path("/proc")
            for entry in proc_path.iterdir():
                if not entry.name.isdigit():
                    continue
                comm_file = entry / "comm"
                try:
                    comm = comm_file.read_text().strip()
                except OSError:
                    continue
                if comm in editor_names:
                    found_pids.append(int(entry.name))
        except Exception:
            return []

        unique_paths: list[str] = []
        seen: set[str] = set()

        for pid in found_pids:
            fd_dir = Path(f"/proc/{pid}/fd")
            try:
                for fd_entry in fd_dir.iterdir():
                    try:
                        target = os.readlink(str(fd_entry))
                    except OSError:
                        continue
                    if not target.startswith("/"):
                        continue
                    p = Path(target)
                    # Only include regular files (no sockets, pipes, etc.)
                    try:
                        if not p.is_file():
                            continue
                    except OSError:
                        continue
                    if target not in seen:
                        seen.add(target)
                        unique_paths.append(target)
                    if len(unique_paths) >= 10:
                        break
            except (PermissionError, OSError):
                continue
            if len(unique_paths) >= 10:
                break

        return unique_paths

    # ------------------------------------------------------------------ #
    #  Recent terminal commands
    # ------------------------------------------------------------------ #

    def get_recent_terminal_commands(self, n: int = 10) -> list[str]:
        """
        Return the last *n* shell commands from bash or fish history.
        Fish history entries use the format ``- cmd: <command>``.
        """
        # Try bash history first
        bash_history = Path.home() / ".bash_history"
        if bash_history.exists():
            try:
                lines = bash_history.read_text(errors="replace").splitlines()
                commands = [l.strip() for l in lines if l.strip() and not l.startswith("#")]
                return commands[-n:]
            except Exception:
                pass

        # Fall back to fish history
        fish_history = Path.home() / ".local" / "share" / "fish" / "fish_history"
        if fish_history.exists():
            try:
                text = fish_history.read_text(errors="replace")
                commands = re.findall(r"^- cmd: (.+)$", text, re.MULTILINE)
                return commands[-n:]
            except Exception:
                pass

        return []

    # ------------------------------------------------------------------ #
    #  Last terminal stderr
    # ------------------------------------------------------------------ #

    def get_last_terminal_stderr(self) -> Optional[str]:
        """
        Return the contents of ``~/.axon/last_stderr`` if it exists,
        otherwise None.
        """
        stderr_file = Path.home() / ".axon" / "last_stderr"
        try:
            if stderr_file.exists():
                content = stderr_file.read_text(errors="replace").strip()
                return content if content else None
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ #
    #  Space context
    # ------------------------------------------------------------------ #

    def get_space_context(self) -> dict[str, Optional[str]]:
        """
        Read ``~/.axon/spaces.json`` and ``~/.axon/current_space`` to
        return ``{"space_name": ..., "space_color": ...}``.
        """
        axon_dir = Path.home() / ".axon"
        result: dict[str, Optional[str]] = {"space_name": None, "space_color": None}

        current_space_file = axon_dir / "current_space"
        spaces_file = axon_dir / "spaces.json"

        try:
            space_name = current_space_file.read_text().strip()
            result["space_name"] = space_name or None
        except Exception:
            return result

        try:
            spaces_data = json.loads(spaces_file.read_text())
            if isinstance(spaces_data, dict):
                space_info = spaces_data.get(result["space_name"], {})
                result["space_color"] = space_info.get("color")
            elif isinstance(spaces_data, list):
                for item in spaces_data:
                    if isinstance(item, dict) and item.get("name") == result["space_name"]:
                        result["space_color"] = item.get("color")
                        break
        except Exception:
            pass

        return result

    # ------------------------------------------------------------------ #
    #  Assembled context string
    # ------------------------------------------------------------------ #

    def build_context_string(self) -> str:
        """
        Assemble all available context into a human-readable string
        suitable for injection into an LLM system prompt.
        """
        parts: list[str] = []

        # Active window
        title = self.get_active_window_title()
        if title:
            parts.append(f"Active window: {title}")

        # Space
        space = self.get_space_context()
        if space["space_name"]:
            space_line = f"Current space: {space['space_name']}"
            if space["space_color"]:
                space_line += f" (color: {space['space_color']})"
            parts.append(space_line)

        # Open files
        open_files = self.get_open_files_in_editors()
        if open_files:
            parts.append("Open files in editors:")
            for f in open_files:
                parts.append(f"  - {f}")

        # Recent commands
        cmds = self.get_recent_terminal_commands()
        if cmds:
            parts.append("Recent terminal commands:")
            for cmd in cmds:
                parts.append(f"  $ {cmd}")

        # Last stderr
        stderr = self.get_last_terminal_stderr()
        if stderr:
            parts.append(f"Last terminal error:\n{stderr}")

        if not parts:
            return "No desktop context available."

        return "\n".join(parts)
