"""
panel.py — AIPanelWindow for Axon AI Panel.

A side-panel GTK4/libadwaita window that streams responses from a local
Ollama instance and is aware of the user's desktop context.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk, Pango  # noqa: E402

# ---------------------------------------------------------------------------
# Import OllamaClient from the intent-bar app, falling back to a built-in
# stub if the module is not yet populated.
# ---------------------------------------------------------------------------
_intent_bar_path = str(Path(__file__).resolve().parents[2] / "intent-bar")
if _intent_bar_path not in sys.path:
    sys.path.insert(0, _intent_bar_path)

try:
    from ollama_client import OllamaClient  # type: ignore[import]
except ImportError:
    # Fallback stub so the panel at least launches even without the real
    # client present.
    import urllib.request
    import json as _json
    import urllib.error

    class OllamaClient:  # type: ignore[no-redef]
        """Minimal Ollama client used when intent-bar's module is absent."""

        BASE_URL: str = "http://localhost:11434"

        def __init__(self, model: str = "llama3") -> None:
            self.model = model

        def is_available(self) -> bool:
            try:
                urllib.request.urlopen(f"{self.BASE_URL}/api/tags", timeout=2)
                return True
            except Exception:
                return False

        def chat_stream(
            self,
            prompt: str,
            system: Optional[str] = None,
        ):
            """Yield text chunks from the Ollama /api/generate endpoint."""
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
            }
            if system:
                payload["system"] = system

            data = _json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.BASE_URL}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    for raw_line in resp:
                        line = raw_line.decode().strip()
                        if not line:
                            continue
                        try:
                            obj = _json.loads(line)
                            chunk = obj.get("response", "")
                            if chunk:
                                yield chunk
                            if obj.get("done"):
                                break
                        except _json.JSONDecodeError:
                            continue
            except Exception as exc:
                yield f"\n[Error: {exc}]"


PANEL_WIDTH: int = 380


# ---------------------------------------------------------------------------
# MessageBubble
# ---------------------------------------------------------------------------

class MessageBubble(Gtk.Box):
    """A single chat message displayed as a styled bubble."""

    def __init__(self, role: str, text: str = "") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_margin_top(4)
        self.set_margin_bottom(4)
        self.set_margin_start(8)
        self.set_margin_end(8)

        self._role = role
        self._label = Gtk.Label(label=text)
        self._label.set_wrap(True)
        self._label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self._label.set_xalign(0.0)
        self._label.set_selectable(True)
        self._label.set_max_width_chars(42)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        inner.set_margin_top(8)
        inner.set_margin_bottom(8)
        inner.set_margin_start(12)
        inner.set_margin_end(12)
        inner.append(self._label)

        if role == "user":
            # Right-aligned, slightly lighter background
            self.set_halign(Gtk.Align.END)
            inner.add_css_class("bubble-user")
        else:
            # Left-aligned, darker background
            self.set_halign(Gtk.Align.START)
            inner.add_css_class("bubble-assistant")

        self.append(inner)

    def append_text(self, chunk: str) -> None:
        """Append *chunk* to the bubble label (used during streaming)."""
        current = self._label.get_text()
        self._label.set_text(current + chunk)


# ---------------------------------------------------------------------------
# AIPanelWindow
# ---------------------------------------------------------------------------

class AIPanelWindow(Adw.Window):
    """Main side-panel window for the Axon AI assistant."""

    _CSS = b"""
    .bubble-user {
        background-color: #1e1e23;
        border-radius: 12px 12px 2px 12px;
        color: #e0e0e0;
    }
    .bubble-assistant {
        background-color: #17171a;
        border-radius: 12px 12px 12px 2px;
        color: #d0d0d0;
    }
    .model-badge {
        background-color: #6c3fa8;
        border-radius: 999px;
        color: #ffffff;
        font-size: 11px;
        padding: 2px 10px;
    }
    .quick-action-btn {
        font-size: 12px;
    }
    .panel-header {
        background-color: #111113;
        border-bottom: 1px solid #2a2a2e;
    }
    .panel-input-row {
        background-color: #111113;
        border-top: 1px solid #2a2a2e;
        padding: 8px;
    }
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        context_reader,  # ContextReader — avoid circular import typing
    ) -> None:
        super().__init__()

        self._client = ollama_client
        self._ctx_reader = context_reader
        self._streaming = False
        self._stream_bubble: Optional[MessageBubble] = None

        # Apply CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(self._CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        self.set_default_size(PANEL_WIDTH, 800)
        self.set_resizable(True)
        self.set_decorated(False)

        # Root layout
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(root)

        # -- Header --
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("panel-header")
        header.set_margin_top(0)
        header.set_spacing(8)
        header.set_margin_start(16)
        header.set_margin_end(16)
        header.set_margin_top(12)
        header.set_margin_bottom(12)

        title_label = Gtk.Label(label="Axon AI")
        title_label.set_markup("<b>Axon AI</b>")
        title_label.set_hexpand(True)
        title_label.set_xalign(0.0)

        model_badge = Gtk.Label(label="local")
        model_badge.add_css_class("model-badge")

        header.append(title_label)
        header.append(model_badge)
        root.append(header)

        # -- Quick actions --
        qa_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        qa_row.set_spacing(6)
        qa_row.set_margin_start(8)
        qa_row.set_margin_end(8)
        qa_row.set_margin_top(8)
        qa_row.set_margin_bottom(4)

        btn_error = Gtk.Button(label="Explain last error")
        btn_error.add_css_class("quick-action-btn")
        btn_error.add_css_class("flat")
        btn_error.connect("clicked", lambda _: self._on_explain_error())

        btn_ctx = Gtk.Button(label="Summarize context")
        btn_ctx.add_css_class("quick-action-btn")
        btn_ctx.add_css_class("flat")
        btn_ctx.connect("clicked", lambda _: self._on_summarize_context())

        qa_row.append(btn_error)
        qa_row.append(btn_ctx)
        root.append(qa_row)

        # -- Chat history --
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._messages_box.set_spacing(2)
        self._messages_box.set_margin_top(8)
        self._messages_box.set_margin_bottom(8)
        self._scroll.set_child(self._messages_box)
        root.append(self._scroll)

        # -- Spinner --
        self._spinner = Gtk.Spinner()
        self._spinner.set_visible(False)
        self._spinner.set_margin_top(4)
        self._spinner.set_margin_bottom(4)
        root.append(self._spinner)

        # -- Input row --
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        input_row.add_css_class("panel-input-row")
        input_row.set_spacing(8)

        self._entry = Gtk.Entry()
        self._entry.set_hexpand(True)
        self._entry.set_placeholder_text("Ask anything…")
        self._entry.connect("activate", self._on_entry_activate)

        send_btn = Gtk.Button(label="Send")
        send_btn.add_css_class("suggested-action")
        send_btn.connect("clicked", self._on_send_clicked)

        input_row.append(self._entry)
        input_row.append(send_btn)
        root.append(input_row)

        # Escape key hides the window
        esc_ctrl = Gtk.EventControllerKey()
        esc_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(esc_ctrl)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state,
    ) -> bool:
        from gi.repository import Gdk
        if keyval == Gdk.KEY_Escape:
            self.set_visible(False)
            return True
        return False

    # ------------------------------------------------------------------
    # Input handlers
    # ------------------------------------------------------------------

    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        self._send_message(entry.get_text())

    def _on_send_clicked(self, btn: Gtk.Button) -> None:
        self._send_message(self._entry.get_text())

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def _add_bubble(self, role: str, text: str = "") -> MessageBubble:
        bubble = MessageBubble(role, text)
        self._messages_box.append(bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        def _do_scroll() -> bool:
            adj = self._scroll.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            return False

        GLib.idle_add(_do_scroll)

    def _send_message(self, text: str) -> None:
        text = text.strip()
        if not text or self._streaming:
            return

        self._entry.set_text("")
        self._add_bubble("user", text)

        if not self._client.is_available():
            self._add_bubble(
                "assistant",
                "Ollama is not running. Start it with: ollama serve",
            )
            return

        ctx_string = self._ctx_reader.build_context_string()
        self._set_streaming(True)
        self._stream_bubble = self._add_bubble("assistant", "")

        thread = threading.Thread(
            target=self._stream_response,
            args=(text, ctx_string),
            daemon=True,
        )
        thread.start()

    def _set_streaming(self, active: bool) -> None:
        self._streaming = active
        self._spinner.set_visible(active)
        if active:
            self._spinner.start()
        else:
            self._spinner.stop()

    def _stream_response(self, text: str, ctx: str) -> None:
        system_prompt = (
            "You are Axon AI, a helpful desktop assistant integrated into Axon OS. "
            "Be concise and practical. Here is the user's current desktop context:\n\n"
            + ctx
        )

        try:
            for chunk in self._client.chat_stream(text, system=system_prompt):
                GLib.idle_add(self._on_chunk, chunk)
        except Exception as exc:
            GLib.idle_add(self._on_chunk, f"\n[Error: {exc}]")
        finally:
            GLib.idle_add(self._on_stream_done)

    def _on_chunk(self, chunk: str) -> bool:
        if self._stream_bubble is not None:
            self._stream_bubble.append_text(chunk)
            self._scroll_to_bottom()
        return False

    def _on_stream_done(self) -> bool:
        self._set_streaming(False)
        self._stream_bubble = None
        return False

    # ------------------------------------------------------------------
    # Quick actions
    # ------------------------------------------------------------------

    def _on_explain_error(self) -> None:
        stderr = self._ctx_reader.get_last_terminal_stderr()
        if stderr:
            query = f"Explain this error and suggest a fix:\n\n{stderr}"
        else:
            query = "There is no recorded terminal error. What common errors should I watch for?"
        self._send_message(query)

    def _on_summarize_context(self) -> None:
        ctx = self._ctx_reader.build_context_string()
        query = (
            "Here is my current desktop context. Please summarise what I appear "
            "to be working on and suggest what I might need help with:\n\n" + ctx
        )
        self._send_message(query)

    # ------------------------------------------------------------------
    # Visibility toggle
    # ------------------------------------------------------------------

    def toggle(self) -> None:
        """Show the window if hidden, hide it if visible."""
        if self.get_visible():
            self.set_visible(False)
        else:
            self.present()
