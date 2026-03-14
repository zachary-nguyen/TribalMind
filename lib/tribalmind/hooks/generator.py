"""Shell hook generator - detects shell and installs/uninstalls hooks.

Supports: bash, zsh, powershell (pwsh), cmd.
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

SENTINEL_BEGIN = "# >>> TribalMind >>>"
SENTINEL_END = "# <<< TribalMind <<<"

SHELL_INFO = {
    "bash": {
        "rc_candidates": ["~/.bashrc", "~/.bash_profile"],
        "hook_file": "bash_hook.sh",
        "source_cmd": "source",
        "label": "Bash",
    },
    "zsh": {
        "rc_candidates": ["~/.zshrc"],
        "hook_file": "zsh_hook.zsh",
        "source_cmd": "source",
        "label": "Zsh",
    },
    "powershell": {
        "rc_candidates": [],  # handled specially
        "hook_file": "powershell_hook.ps1",
        "source_cmd": ". ",
        "label": "PowerShell",
    },
    "cmd": {
        "rc_candidates": [],  # handled via registry
        "hook_file": "cmd_hook.cmd",
        "source_cmd": "",
        "label": "CMD",
    },
}

# ── Detection ─────────────────────────────────────────────────────────


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


def list_available_shells() -> list[dict]:
    """Discover which shells are available on the system.

    Returns a list of dicts with keys: name, label, available, installed.
    """
    shells = []
    for name, info in SHELL_INFO.items():
        available = _is_shell_available(name)
        installed = _is_hook_installed(name) if available else False
        shells.append({
            "name": name,
            "label": info["label"],
            "available": available,
            "installed": installed,
        })
    return shells


def _is_shell_available(shell: str) -> bool:
    """Check if a shell is installed on the system."""
    if shell == "cmd":
        return sys.platform == "win32"

    if shell == "powershell":
        # Always available on Windows 10+; check for pwsh on Unix
        if sys.platform == "win32":
            return True
        return shutil.which("pwsh") is not None

    if shell == "bash":
        if sys.platform == "win32":
            # Check for Git Bash
            return _find_git_bash() is not None
        return shutil.which("bash") is not None

    if shell == "zsh":
        if sys.platform == "win32":
            return False  # Zsh is rare on Windows
        return shutil.which("zsh") is not None

    return False


def _find_git_bash() -> Path | None:
    """Find Git Bash on Windows."""
    if shutil.which("bash"):
        return Path(shutil.which("bash"))  # type: ignore[arg-type]

    # Common install locations
    candidates = [
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get(
            "ProgramFiles(x86)", "C:\\Program Files (x86)"
        )) / "Git" / "bin" / "bash.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Git" / "bin" / "bash.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _is_hook_installed(shell: str) -> bool:
    """Check if the hook is already installed for a given shell."""
    if shell == "cmd":
        return _is_cmd_hook_installed()

    rc_file = get_rc_file(shell)
    if rc_file is None or not rc_file.exists():
        return False
    return SENTINEL_BEGIN in rc_file.read_text(errors="replace")


# ── RC / profile file resolution ─────────────────────────────────────


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

    if shell == "cmd":
        return None  # CMD uses registry, not RC files

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
    """Get the PowerShell profile path by asking PowerShell itself."""
    import subprocess

    # Ask the running PowerShell for its $PROFILE path — works for both 5.1 and 7+
    for exe in ("powershell.exe", "pwsh.exe", "pwsh"):
        try:
            result = subprocess.run(
                [exe, "-NoProfile", "-NoLogo", "-Command", "Write-Host $PROFILE"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0 and result.stdout.strip():
                return Path(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue

    # Fallback to common locations
    if sys.platform == "win32":
        docs = Path.home() / "Documents"
        candidates = [
            docs / "WindowsPowerShell" / "Microsoft.PowerShell_profile.ps1",
            docs / "PowerShell" / "Microsoft.PowerShell_profile.ps1",
        ]
    else:
        config = Path.home() / ".config"
        candidates = [
            config / "powershell" / "Microsoft.PowerShell_profile.ps1",
        ]

    for c in candidates:
        if c.exists():
            return c

    return candidates[0] if candidates else None


# ── Install / uninstall ──────────────────────────────────────────────


def install_hook(shell: str) -> None:
    """Install the TribalMind hook into the shell's RC file."""
    if shell == "cmd":
        _install_cmd_hook()
        return

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
    if shell == "cmd":
        _uninstall_cmd_hook()
        return

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


# ── CMD-specific (registry AutoRun) ─────────────────────────────────

_CMD_REGISTRY_KEY = r"Software\Microsoft\Command Processor"
_CMD_SENTINEL = "TribalMind"


def _install_cmd_hook() -> None:
    """Install CMD hook via the AutoRun registry key."""
    if sys.platform != "win32":
        raise RuntimeError("CMD hooks are only supported on Windows")

    import winreg

    hook_path = get_hook_source_path("cmd")
    if not hook_path.exists():
        raise RuntimeError(f"Hook script not found: {hook_path}")

    hook_cmd = f'"{hook_path}"'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _CMD_REGISTRY_KEY,
            0, winreg.KEY_READ | winreg.KEY_WRITE,
        )
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, _CMD_REGISTRY_KEY)

    try:
        existing, _ = winreg.QueryValueEx(key, "AutoRun")
    except FileNotFoundError:
        existing = ""

    if _CMD_SENTINEL in str(existing):
        logger.info("CMD hook already installed in AutoRun")
        winreg.CloseKey(key)
        return

    # Append our hook (use & to chain with any existing AutoRun)
    if existing:
        new_value = f"{existing} & {hook_cmd}"
    else:
        new_value = hook_cmd

    winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_SZ, new_value)
    winreg.CloseKey(key)
    logger.info("Installed CMD hook via registry AutoRun")


def _uninstall_cmd_hook() -> None:
    """Remove CMD hook from the AutoRun registry key."""
    if sys.platform != "win32":
        return

    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _CMD_REGISTRY_KEY,
            0, winreg.KEY_READ | winreg.KEY_WRITE,
        )
    except FileNotFoundError:
        return

    try:
        existing, _ = winreg.QueryValueEx(key, "AutoRun")
    except FileNotFoundError:
        winreg.CloseKey(key)
        return

    if _CMD_SENTINEL not in str(existing):
        winreg.CloseKey(key)
        return

    # Remove our part from the AutoRun chain
    hook_path = get_hook_source_path("cmd")
    hook_cmd = f'"{hook_path}"'

    parts = [p.strip() for p in existing.split("&")]
    parts = [p for p in parts if _CMD_SENTINEL not in p and hook_cmd not in p]
    new_value = " & ".join(parts).strip()

    if new_value:
        winreg.SetValueEx(key, "AutoRun", 0, winreg.REG_SZ, new_value)
    else:
        try:
            winreg.DeleteValue(key, "AutoRun")
        except FileNotFoundError:
            pass

    winreg.CloseKey(key)
    logger.info("Removed CMD hook from registry AutoRun")


def _is_cmd_hook_installed() -> bool:
    """Check if CMD hook is installed in AutoRun."""
    if sys.platform != "win32":
        return False

    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _CMD_REGISTRY_KEY,
            0, winreg.KEY_READ,
        )
        existing, _ = winreg.QueryValueEx(key, "AutoRun")
        winreg.CloseKey(key)
        return _CMD_SENTINEL in str(existing)
    except (FileNotFoundError, OSError):
        return False
