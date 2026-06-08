"""Intent Bar main window."""

from __future__ import annotations

import json
import subprocess
import threading
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk  # noqa: E402

from ..ollama_client import OllamaClient  # noqa: E402
from ..spaces_manager import SpacesManager  # noqa: E402

_CSS = b"""
.intent-bar-window {
    background-color: #17171a;
    border-radius: 12px;
}

.intent-entry {
    background-color: #1e1e22;
    color: #e8e8f0;
    border: 1px solid #2e2e38;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 15px;
    caret-color: #a78bfa;
}

.intent-entry:focus {
    border-color: #a78bfa;
    box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.25);
}

.response-label {
    color: #c4c4d4;
    font-size: 13px;
}

.space-badge {
    color: #a78bfa;
    font-size: 11px;
    font-weight: bold;
    background-color: rgba(167, 139, 250, 0.12);
    border-radius: 6px;
    padding: 2px 8px;
}

.start-ollama-btn {
    background-color: transparent;
    color: #a78bfa;
    border: 1px solid #a78bfa;
    border-radius: 6px;
    font-size: 12px;
    padding: 4px 10px;
}

.start-ollama-btn:hover {
    background-color: rgba(167, 139, 250, 0.15);
}
"""

_SYSTEM_PROMPT_TEMPLATE = """You are an intelligent assistant embedded in Axon OS, a Linux desktop environment.
The user is currently in workspace: "{space_name}".

You can perform actions or answer questions.

When the user wants to open an application or run a command, respond ONLY with a JSON object (no markdown, no extra text):
  {{"action": "open_app", "app": "<application name>"}}
  or
  {{"action": "run_command", "command": "<shell command>"}}

For all other queries — information, explanations, conversation — respond with plain natural language text.
Keep responses concise and helpful.
"""


class IntentBarWindow(Adw.Window):
    """Floating intent bar window for Axon OS."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        spaces_manager: SpacesManager,
    ) -> None:
        super().__init__()
        self._ollama = ollama_client
        self._spaces = spaces_manager

        self.set_decorated(False)
        self.set_default_size(640, -1)
        self.set_resizable(False)
        self.add_css_class("intent-bar-window")

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Apply CSS
        provider = Gtk.CssProvider()
        provider.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Outer box with padding
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(16)
        outer.set_margin_end(16)
        self.set_content(outer)

        # Top row: space badge + start-ollama button
        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top_row.set_margin_bottom(8)
        outer.append(top_row)

        current_space = self._spaces.get_current_space()
        space_name = current_space.name if current_space else "No Space"

        self._space_badge = Gtk.Label(label=space_name)
        self._space_badge.add_css_class("space-badge")
        self._space_badge.set_halign(Gtk.Align.START)
        top_row.append(self._space_badge)

        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        top_row.append(spacer)

        self._start_ollama_btn = Gtk.Button(label="Start Ollama")
        self._start_ollama_btn.add_css_class("start-ollama-btn")
        self._start_ollama_btn.set_visible(not self._ollama.is_available())
        top_row.append(self._start_ollama_btn)

        # Entry row: text field + spinner
        entry_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.append(entry_row)

        self._entry = Gtk.Entry()
        self._entry.set_placeholder_text("Ask anything...")
        self._entry.set_hexpand(True)
        self._entry.add_css_class("intent-entry")
        entry_row.append(self._entry)

        self._spinner = Gtk.Spinner()
        self._spinner.set_valign(Gtk.Align.CENTER)
        self._spinner.set_size_request(24, 24)
        entry_row.append(self._spinner)

        # Response label
        self._response_label = Gtk.Label()
        self._response_label.set_wrap(True)
        self._response_label.set_xalign(0.0)
        self._response_label.set_selectable(True)
        self._response_label.add_css_class("response-label")
        self._response_label.set_margin_top(10)
        self._response_label.set_visible(False)
        outer.append(self._response_label)

    # ------------------------------------------------------------------
    # Signal connections
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._entry.connect("activate", self._on_activate)
        self._start_ollama_btn.connect("clicked", self._on_start_ollama)

        # Escape closes the window
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    # ------------------------------------------------------------------
    # Key handler
    # ------------------------------------------------------------------

    def _on_key_pressed(
        self,
        _ctrl: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        _state: Any,
    ) -> bool:
        from gi.repository import Gdk

        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    # ------------------------------------------------------------------
    # Query handling
    # ------------------------------------------------------------------

    def _on_activate(self, entry: Gtk.Entry) -> None:
        query = entry.get_text().strip()
        if not query:
            return

        if not self._ollama.is_available():
            self._show_response("[error] Ollama is not running. Click 'Start Ollama'.")
            self._start_ollama_btn.set_visible(True)
            return

        self._spinner.start()
        self._response_label.set_visible(False)
        entry.set_sensitive(False)

        thread = threading.Thread(
            target=self._do_query,
            args=(query,),
            daemon=True,
        )
        thread.start()

    def _do_query(self, query: str) -> None:
        """Run the Ollama query in a background thread."""
        system = self._build_system_prompt()
        response_text = self._ollama.generate(query, system=system)
        GLib.idle_add(self._on_response, response_text)

    def _on_response(self, text: str) -> bool:
        """Handle the response back on the GTK main thread."""
        self._spinner.stop()
        self._entry.set_sensitive(True)

        # Attempt to parse as an action dict
        stripped = text.strip()
        try:
            action: dict[str, Any] = json.loads(stripped)
            if isinstance(action, dict) and "action" in action:
                self._execute_action(action)
                self._show_response(f"[action] {action}")
            else:
                self._show_response(stripped)
        except (json.JSONDecodeError, ValueError):
            self._show_response(stripped)

        return False  # remove from idle queue

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(self, action: dict[str, Any]) -> None:
        """Dispatch an action returned by the model."""
        action_type: str = action.get("action", "")

        if action_type == "open_app":
            app_name: str = action.get("app", "")
            if app_name:
                subprocess.Popen(
                    [app_name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        elif action_type == "run_command":
            command: str = action.get("command", "")
            if command:
                subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self) -> str:
        current_space = self._spaces.get_current_space()
        space_name = current_space.name if current_space else "Default"
        return _SYSTEM_PROMPT_TEMPLATE.format(space_name=space_name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_response(self, text: str) -> None:
        self._response_label.set_text(text)
        self._response_label.set_visible(True)

    def _on_start_ollama(self, _btn: Gtk.Button) -> None:
        """Attempt to launch the Ollama daemon."""
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._start_ollama_btn.set_sensitive(False)
        self._show_response("Starting Ollama... please wait a moment and try again.")
