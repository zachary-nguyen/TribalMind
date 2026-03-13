"""Shell hook generator - detects shell and installs/uninstalls hooks.

Supports: bash, zsh, powershell (pwsh).
"""

from __future__ import annotations

import logging
import os
import sys
from importlib import resources
from pathlib import Path

logger = logging.getLogger(__name__)

SENTINEL_BEGIN = "# >>> TribalMind >>>"
SENTINEL_END = "# <<< TribalMind <<<"

SHELL_INFO = {
    "bash": {
        "rc_candidates": ["~/.bashrc", "~/.bash_profile"],
        "hook_file": "bash_hook.sh",
        "source_cmd": "source",
    },
    "zsh": {
        "rc_candidates": ["~/.zshrc"],
        "hook_file": "zsh_hook.zsh",
        "source_cmd": "source",
    },
    "powershell": {
        "rc_candidates": [],  # handled specially
        "hook_file": "powershell_hook.ps1",
        "source_cmd": ". ",
    },
}


def detect_shell() -> str | None:
    """Auto-detect the user's shell."""
    # Check SHELL env var (Unix)
    shell_env = os.environ.get("SHELL", "")
    if "zsh" in shell_env:
        return "zsh"
    if "bash" in shell_env:
        return "bash"

    # Check for PowerShell indicators
    if os.environ.get("PSModulePath"):
        return "powershell"

    # Check parent process on Windows
    if sys.platform == "win32":
        return "powershell"  # Default to PowerShell on Windows

    # Fallback: check /etc/shells or default
    if "bash" in shell_env or shell_env == "":
        return "bash"

    return None


def get_hook_source_path(shell: str) -> Path:
    """Get the path to the hook script file bundled with tribalmind."""
    info = SHELL_INFO.get(shell)
    if not info:
        raise ValueError(f"Unsupported shell: {shell}")

    # Get the hooks directory from the package
    hooks_dir = Path(__file__).parent
    return hooks_dir / info["hook_file"]


def get_rc_file(shell: str) -> Path | None:
    """Get the appropriate RC/profile file for the shell."""
    if shell == "powershell":
        return _get_powershell_profile()

    info = SHELL_INFO.get(shell)
    if not info:
        return None

    for candidate in info["rc_candidates"]:
        path = Path(candidate).expanduser()
        if path.exists():
            return path

    # Return first candidate even if it doesn't exist (we'll create it)
    if info["rc_candidates"]:
        return Path(info["rc_candidates"][0]).expanduser()
    return None


def _get_powershell_profile() -> Path | None:
    """Get the PowerShell profile path."""
    # Try common profile locations
    if sys.platform == "win32":
        docs = Path.home() / "Documents"
        candidates = [
            docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
            docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
        ]
    else:
        config = Path.home() / ".config"
        candidates = [
            config / "powershell" / "Microsoft.PowerShell_profile.ps1",
        ]

    for c in candidates:
        if c.exists():
            return c

    # Return the first candidate (will be created)
    return candidates[0] if candidates else None


def install_hook(shell: str) -> None:
    """Install the TribalMind hook into the shell's RC file."""
    rc_file = get_rc_file(shell)
    if rc_file is None:
        raise RuntimeError(f"Could not determine RC file for {shell}")

    hook_source = get_hook_source_path(shell)
    if not hook_source.exists():
        raise RuntimeError(f"Hook script not found: {hook_source}")

    # Check if already installed
    if rc_file.exists():
        content = rc_file.read_text()
        if SENTINEL_BEGIN in content:
            logger.info("Hook already installed in %s", rc_file)
            return
    else:
        rc_file.parent.mkdir(parents=True, exist_ok=True)
        content = ""

    # Build the source line
    info = SHELL_INFO[shell]
    hook_path_str = str(hook_source).replace("\\", "/")

    if shell == "powershell":
        source_line = f'. "{hook_path_str}"'
    else:
        source_line = f'{info["source_cmd"]} "{hook_path_str}"'

    # Append to RC file
    block = f"\n{SENTINEL_BEGIN}\n{source_line}\n{SENTINEL_END}\n"
    with open(rc_file, "a") as f:
        f.write(block)

    logger.info("Installed %s hook in %s", shell, rc_file)


def uninstall_hook(shell: str) -> None:
    """Remove the TribalMind hook from the shell's RC file."""
    rc_file = get_rc_file(shell)
    if rc_file is None or not rc_file.exists():
        return

    content = rc_file.read_text()
    if SENTINEL_BEGIN not in content:
        return

    # Remove the block between sentinels (inclusive)
    lines = content.splitlines(keepends=True)
    new_lines = []
    in_block = False
    for line in lines:
        if SENTINEL_BEGIN in line:
            in_block = True
            continue
        if SENTINEL_END in line:
            in_block = False
            continue
        if not in_block:
            new_lines.append(line)

    rc_file.write_text("".join(new_lines))
    logger.info("Uninstalled %s hook from %s", shell, rc_file)
