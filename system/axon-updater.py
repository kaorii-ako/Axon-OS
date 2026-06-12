#!/usr/bin/env python3
"""
Axon OS Updater

A seamless, self-healing graphical update manager for Axon OS.
Takes a BTRFS snapshot via timeshift, updates system packages via APT,
updates sandboxed apps via Flatpak, and refreshes the GRUB bootloader.
"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk


class AxonUpdaterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Axon OS Updater")
        self.geometry("500x300")
        self.resizable(False, False)

        # Check root
        if os.geteuid() != 0:
            messagebox.showerror(
                "Permission Denied",
                "Axon Updater requires administrative privileges. Please run via sudo or pkexec.",
            )
            self.destroy()
            sys.exit(1)

        self.configure(bg="#2E3440")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        # Styles
        self.style.configure("TFrame", background="#2E3440")
        self.style.configure(
            "TLabel", background="#2E3440", foreground="#D8DEE9", font=("Inter", 12)
        )
        self.style.configure("Title.TLabel", font=("Inter", 16, "bold"), foreground="#88C0D0")
        self.style.configure(
            "TButton", font=("Inter", 11, "bold"), background="#5E81AC", foreground="white"
        )
        self.style.map("TButton", background=[("active", "#81A1C1")])
        self.style.configure(
            "TProgressbar", thickness=15, troughcolor="#4C566A", background="#A3BE8C"
        )

        # UI Elements
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)

        self.lbl_title = ttk.Label(frame, text="System Update Available", style="Title.TLabel")
        self.lbl_title.pack(pady=(10, 5))

        self.lbl_status = ttk.Label(
            frame,
            text="Ready to update core OS and sandboxed apps.",
            wraplength=450,
            justify=tk.CENTER,
        )
        self.lbl_status.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(frame, mode="determinate", length=400)
        self.progress.pack(pady=10)

        self.btn_start = ttk.Button(frame, text="Start Update", command=self.start_update)
        self.btn_start.pack(pady=20)

    def log(self, msg, progress_val=None):
        self.lbl_status.config(text=msg)
        if progress_val is not None:
            self.progress["value"] = progress_val
        self.update_idletasks()

    def run_cmd(self, cmd, extra_env=None):
        try:
            run_env = os.environ.copy()
            if extra_env:
                run_env.update(extra_env)

            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=run_env
            )
            if result.returncode != 0:
                print(f"Error running '{cmd_str}':\n{result.stdout}")
                return False
            return True
        except Exception as e:
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            print(f"Exception running '{cmd_str}': {e}")
            return False

    def start_update(self):
        self.btn_start.config(state=tk.DISABLED)
        self.progress["value"] = 0
        threading.Thread(target=self._update_process, daemon=True).start()

    def _update_process(self):
        # 1. Snapshot
        self.log("Phase 1/4: Creating Self-Healing Snapshot...", 10)
        if not self.run_cmd(
            ["timeshift", "--create", "--comments", "Axon OS Auto-Update Snapshot"]
        ):
            self.log(
                "Warning: Failed to create snapshot (Timeshift not configured?). Proceeding anyway.",
                20,
            )
        else:
            self.progress["value"] = 30

        # 2. APT Update
        self.log("Phase 2/4: Updating System Packages (APT)...", 35)
        self.run_cmd(["apt-get", "update"])
        self.progress["value"] = 45

        self.log("Phase 2/4: Installing System Upgrades...", 50)
        if not self.run_cmd(
            ["apt-get", "dist-upgrade", "-y", "-q"], extra_env={"DEBIAN_FRONTEND": "noninteractive"}
        ):
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Error", "System package update failed. Check terminal logs."
                ),
            )
            self.log("Update Failed.", 0)
            self.after(0, lambda: self.btn_start.config(state=tk.NORMAL))
            return

        self.progress["value"] = 70

        # 3. Flatpak Update
        self.log("Phase 3/4: Updating Sandboxed Apps (Flatpak)...", 75)
        if not self.run_cmd(["flatpak", "update", "-y"]):
            self.log("Warning: Flatpak update encountered an issue.", 85)
        else:
            self.progress["value"] = 90

        # 4. GRUB Update
        self.log("Phase 4/4: Updating Bootloader...", 95)
        self.run_cmd(["update-grub"])

        self.progress["value"] = 100
        self.log("Update Complete! Your system is fully up to date.")

        self.after(
            0, lambda: self.btn_start.config(text="Close", command=self.destroy, state=tk.NORMAL)
        )


if __name__ == "__main__":
    app = AxonUpdaterApp()
    app.mainloop()
