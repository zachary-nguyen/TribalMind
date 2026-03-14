"""Hatchling build hook — compiles the React frontend before building the wheel.

Runs automatically when executing: pip install . / pip install -e . / hatch build
Requires pnpm to be installed on the build machine (not on end-user machines).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict) -> None:
        ui_dir = Path(self.root) / "ui"

        if not ui_dir.exists():
            self.app.display_warning("ui/ directory not found, skipping frontend build")
            return

        pnpm = shutil.which("pnpm")
        if not pnpm:
            self.app.display_warning("pnpm not found, skipping frontend build")
            return

        self.app.display_info("Installing frontend dependencies...")
        subprocess.run([pnpm, "install", "--frozen-lockfile"], cwd=ui_dir, check=True)

        self.app.display_info("Building frontend...")
        subprocess.run([pnpm, "build"], cwd=ui_dir, check=True)

        self.app.display_info("Frontend built → lib/tribalmind/web/static/")
