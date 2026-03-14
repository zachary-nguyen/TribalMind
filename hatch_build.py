"""Hatchling build hook — compiles the React frontend before building the wheel.

Runs automatically when executing: pip install . / pip install -e . / hatch build
Requires pnpm to be installed on the build machine (not on end-user machines).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def _run_pnpm(ui_dir: Path, *args: str) -> None:
    """Run pnpm; on Windows use shell so .cmd/.bat/other launchers work."""
    if sys.platform == "win32":
        cmd = "pnpm " + " ".join(args)
        subprocess.run(cmd, cwd=ui_dir, check=True, shell=True)
    else:
        pnpm = shutil.which("pnpm")
        if not pnpm:
            raise FileNotFoundError("pnpm not found in PATH")
        subprocess.run([pnpm, *args], cwd=ui_dir, check=True)


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        ui_dir = Path(self.root) / "ui"

        if not ui_dir.exists():
            self.app.display_warning("ui/ directory not found, skipping frontend build")
            return

        if not shutil.which("pnpm") and sys.platform != "win32":
            self.app.display_warning("pnpm not found, skipping frontend build")
            return

        self.app.display_info("Installing frontend dependencies...")
        _run_pnpm(ui_dir, "install", "--frozen-lockfile")

        self.app.display_info("Building frontend...")
        _run_pnpm(ui_dir, "build")

        self.app.display_info("Frontend built → lib/tribalmind/web/static/")
