#!/usr/bin/env python3
<<<<<<< HEAD
import os
import sys
import json
import subprocess
=======
"""Axon GUI Agent — the desktop drives itself (org.axonos.GuiAgent).

Takes a natural-language instruction ("turn on night light and make the
font bigger"), asks the Brain to compile it into a JSON plan of atomic
desktop operations, validates every operation against a strict allowlist
(plan.py), then executes them through `gsettings`/`gtk-launch` in
milliseconds — no screenshot pipelines, no synthetic clicks.
"""

import json
import shutil
import subprocess
import sys
>>>>>>> origin/main
import threading
from pathlib import Path

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

<<<<<<< HEAD
# Ensure we can load axon_logger
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from axon_logger import configure_app_logger
    logger = configure_app_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("axon-gui-agent")
=======
sys.path.insert(0, str(Path(__file__).resolve().parent))
import plan as plan_mod

PLANNER_PROMPT = """\
You are the desktop automation planner for Axon OS (GNOME). Convert the
user's request into a JSON array of operations. Allowed operation shapes:

  {"type": "gsettings_set", "schema": "<schema>", "key": "<key>", "value": <value>}
  {"type": "launch_app", "app": "<desktop-file-or-executable-name>"}
  {"type": "notify", "message": "<text shown to the user>"}

Useful schemas: org.gnome.desktop.interface (font-name, color-scheme,
text-scaling-factor, enable-animations, clock-show-seconds),
org.gnome.desktop.background (picture-uri, picture-uri-dark),
org.gnome.settings-daemon.plugins.color (night-light-enabled,
night-light-temperature), org.gnome.desktop.wm.preferences (button-layout,
num-workspaces), org.gnome.desktop.peripherals.touchpad (tap-to-click,
natural-scroll), org.gnome.mutter (edge-tiling, dynamic-workspaces).

Respond with ONLY the JSON array. No markdown, no commentary.

User request: """

>>>>>>> origin/main

class GuiAgentService(dbus.service.Object):
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.session_bus = dbus.SessionBus()
<<<<<<< HEAD
        
        try:
            self.bus_name = dbus.service.BusName('org.axonos.GuiAgent', bus=self.session_bus)
        except dbus.exceptions.NameExistsException:
            logger.error("org.axonos.GuiAgent service is already running.")
            sys.exit(1)
            
        dbus.service.Object.__init__(self, self.session_bus, '/org/axonos/GuiAgent')
        logger.info("Axon GUI Agent registered successfully at /org/axonos/GuiAgent")

    @dbus.service.method('org.axonos.GuiAgent', in_signature='s', out_signature='b')
    def ExecuteInstruction(self, instruction):
        """Asynchronously translates and executes natural language instruction."""
        logger.info(f"Received GUI Agent instruction: '{instruction}'")
        threading.Thread(target=self._do_execute, args=(instruction,), daemon=True).start()
        return True

    def _do_execute(self, instruction):
        try:
            # Query Brain D-Bus service
            brain_obj = self.session_bus.get_object('org.axonos.Brain', '/org/axonos/Brain')
            brain_interface = dbus.Interface(brain_obj, 'org.axonos.Brain')
            
            system_prompt = (
                "You are the desktop automation engine for Axon OS. Convert the user's natural language request "
                "into a JSON list of configuration steps to execute. Valid actions are:\n"
                "1. {'action': 'gsettings', 'schema': '<schema_name>', 'key': '<key_name>', 'value': '<value_string_or_boolean>'}\n"
                "2. {'action': 'dbus', 'destination': '<service>', 'path': '<path>', 'interface': '<iface>', 'method': '<method>', 'args': [<args>]}\n"
                "3. {'action': 'shell', 'command': '<executable_or_shell_command>'}\n\n"
                "Respond ONLY with a valid JSON array of these objects. Do not include markdown codeblocks or explanations. "
                "Example: [{\"action\": \"gsettings\", \"schema\": \"org.gnome.desktop.interface\", \"key\": \"font-name\", \"value\": \"'Inter 11'\"}]"
            )
            
            resp = brain_interface.Generate(instruction, "", "", False)
            clean_resp = resp.strip()
            if clean_resp.startswith("```"):
                clean_resp = clean_resp.replace("```json", "").replace("```", "").strip()
                
            actions = json.loads(clean_resp)
            if not isinstance(actions, list):
                logger.warning("GUI Agent received non-list output from Brain.")
                return

            for act in actions:
                action_type = act.get("action")
                if action_type == "gsettings":
                    schema = act.get("schema")
                    key = act.get("key")
                    val = str(act.get("value"))
                    logger.info(f"Running GSettings: set {schema} {key} {val}")
                    subprocess.run(["gsettings", "set", schema, key, val], capture_output=True)
                elif action_type == "shell":
                    cmd = act.get("command")
                    logger.info(f"Running shell command: {cmd}")
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                elif action_type == "dbus":
                    dest = act.get("destination")
                    path = act.get("path")
                    iface = act.get("interface")
                    method = act.get("method")
                    args = act.get("args", [])
                    logger.info(f"Invoking D-Bus call: {dest} {path} {iface}.{method}({args})")
                    try:
                        obj = self.session_bus.get_object(dest, path)
                        dbus_iface = dbus.Interface(obj, iface)
                        getattr(dbus_iface, method)(*args)
                    except Exception as de:
                        logger.error(f"D-Bus call execution failed: {de}")

        except Exception as e:
            logger.exception("Error executing GUI Agent instruction:")

if __name__ == '__main__':
=======
        try:
            self.bus_name = dbus.service.BusName(
                "org.axonos.GuiAgent", bus=self.session_bus
            )
        except dbus.exceptions.NameExistsException:
            print("org.axonos.GuiAgent service is already running.")
            sys.exit(1)
        dbus.service.Object.__init__(
            self, self.session_bus, "/org/axonos/GuiAgent"
        )
        print("Axon GUI Agent registered at /org/axonos/GuiAgent")

    # ------------------------------------------------------------------
    # D-Bus API
    # ------------------------------------------------------------------

    @dbus.service.method("org.axonos.GuiAgent", in_signature="s", out_signature="s")
    def Execute(self, instruction):
        """Plan + run a desktop instruction synchronously; JSON report."""
        return json.dumps(self._run(str(instruction)))

    @dbus.service.method("org.axonos.GuiAgent", in_signature="s", out_signature="s")
    def ExecuteAsync(self, instruction):
        """Fire-and-forget variant; completion announced via ActionsDone."""
        text = str(instruction)

        def worker():
            report = self._run(text)
            GLib.idle_add(self.ActionsDone, json.dumps(report))

        threading.Thread(target=worker, daemon=True).start()
        return "started"

    @dbus.service.signal("org.axonos.GuiAgent", signature="s")
    def ActionsDone(self, report_json):
        pass

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def _run(self, instruction):
        raw = self._ask_brain(instruction)
        if raw is None:
            return {"ok": False, "error": "AI brain unavailable",
                    "executed": [], "skipped": []}
        ops, errors = plan_mod.validate_plan(raw)
        executed, failed = [], []
        for op in ops:
            ok, detail = self._apply(op)
            (executed if ok else failed).append(detail)
        report = {"ok": bool(executed) and not failed,
                  "executed": executed, "failed": failed, "skipped": errors}
        summary = f"{len(executed)} change(s) applied"
        if failed or errors:
            summary += f", {len(failed) + len(errors)} skipped"
        self._notify("Axon GUI Agent", summary)
        return report

    def _ask_brain(self, instruction):
        try:
            obj = self.session_bus.get_object(
                "org.axonos.Brain", "/org/axonos/Brain"
            )
            brain = dbus.Interface(obj, "org.axonos.Brain")
            return str(brain.Generate(
                PLANNER_PROMPT + instruction, "", "", False, timeout=60
            ))
        except dbus.exceptions.DBusException:
            return None

    def _apply(self, op):
        op_type = op["type"]
        try:
            if op_type == "gsettings_set":
                value = plan_mod.to_gvariant(op["value"])
                proc = subprocess.run(
                    ["gsettings", "set", str(op["schema"]),
                     str(op["key"]), value],
                    capture_output=True, text=True, timeout=10,
                )
                detail = f"gsettings {op['schema']} {op['key']} = {value}"
                if proc.returncode != 0:
                    return False, f"{detail} ({proc.stderr.strip()[:120]})"
                return True, detail
            if op_type == "launch_app":
                app = str(op["app"])
                launcher = (["gtk-launch", app]
                            if shutil.which("gtk-launch") else [app])
                subprocess.Popen(launcher, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return True, f"launched {app}"
            if op_type == "notify":
                self._notify("Axon", str(op["message"]))
                return True, "notified"
        except Exception as exc:
            return False, f"{op_type}: {exc}"
        return False, f"unhandled op {op_type}"

    def _notify(self, title, body):
        if shutil.which("notify-send"):
            subprocess.Popen(
                ["notify-send", "-i", "preferences-system", title, body[:300]],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )


if __name__ == "__main__":
>>>>>>> origin/main
    loop = GLib.MainLoop()
    service = GuiAgentService()
    try:
        loop.run()
    except KeyboardInterrupt:
<<<<<<< HEAD
        logger.info("Stopping Axon GUI Agent...")
=======
>>>>>>> origin/main
        loop.quit()
