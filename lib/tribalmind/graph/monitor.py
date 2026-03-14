"""Monitor Node - intercepts shell execution and classifies errors.

Uses lightweight regex patterns to classify the ~80% of common errors locally
(free, instant). Unrecognized errors are left for the LLM in the inference node.
"""

from __future__ import annotations

import hashlib
import re

from tribalmind.graph.state import TribalState

# ── Common error patterns (fast, local, free) ───────────────────────

_PATTERNS: list[tuple[re.Pattern, str, int | None]] = [
    # (regex, error_type, group index for package or None)
    (re.compile(
        r"ModuleNotFoundError: No module named ['\"](\w[\w.]*)"
    ), "ModuleNotFoundError", 1),
    (re.compile(
        r"ImportError: cannot import name ['\"](\w+)['\"] from ['\"](\w+)"
    ), "ImportError", 2),
    (re.compile(r"(\w+Error|\w+Exception):\s*(.+)"), "_python_generic", None),
    (re.compile(r"Error:\s+Cannot find module ['\"]([^'\"]+)"), "NodeModuleNotFound", 1),
    (re.compile(r"(?:npm ERR!|npm error)\s+404"), "NpmPackageNotFound", None),
    (re.compile(r"(?:npm ERR!|npm error)\s+(.+)"), "NpmError", None),
    (re.compile(r"error\[E(\d+)\]:\s*(.+)"), "RustError", None),
    (re.compile(r"panic:\s*(.+)"), "GoPanic", None),
    (re.compile(r"cannot find package \"([^\"]+)\""), "GoPackageError", 1),
    (re.compile(r"(\S+):\s*command not found"), "CommandNotFound", 1),
    (re.compile(r"The term '(\S+)' is not recognized"), "CommandNotFound", 1),
    (re.compile(r"Permission denied"), "PermissionDenied", None),
    (re.compile(
        r"ERROR: (?:Could not find a version|No matching distribution)"
        r" found for (\S+)"
    ), "PipInstallError", 1),
]

# Extract package from npm 404 registry URL
_NPM_404_PKG = re.compile(r"registry\.npmjs\.org/(\S+?)(?:\s|$)")
# Extract package from npm resource line
_NPM_RESOURCE_PKG = re.compile(r"resource\s+['\"](\S+?)[@'\"]")


def _try_classify(stderr: str) -> tuple[str | None, str | None]:
    """Attempt fast local classification of stderr.

    Returns (error_type, package) or (None, None) if unrecognized.
    """
    if not stderr:
        return None, None

    for pattern, error_type, pkg_group in _PATTERNS:
        m = pattern.search(stderr)
        if not m:
            continue

        # Handle Python generic traceback — extract actual error type
        if error_type == "_python_generic":
            actual_type = m.group(1)
            # Try to extract package from traceback file paths
            pkg = None
            file_match = re.search(r'File ".*?[\\/](?:site-packages|lib)[\\/](\w+)', stderr)
            if file_match:
                pkg = file_match.group(1)
            return actual_type, pkg

        # Extract package from the match if a group is specified
        pkg = m.group(pkg_group) if pkg_group and pkg_group <= len(m.groups()) else None

        # Special handling for npm 404: try to extract package name
        if error_type == "NpmPackageNotFound" and not pkg:
            url_m = _NPM_404_PKG.search(stderr)
            if url_m:
                pkg = url_m.group(1).strip("/")
            else:
                res_m = _NPM_RESOURCE_PKG.search(stderr)
                if res_m:
                    pkg = res_m.group(1)

        # Clean up Node module package name
        if error_type == "NodeModuleNotFound" and pkg:
            pkg = pkg.split("/")[0].lstrip("@")

        return error_type, pkg

    return None, None


def _classify_from_command(command: str) -> tuple[str | None, str | None]:
    """Best-effort inference from the command when stderr is empty/unrecognized."""
    # python -c "import foo" or python -m foo
    m = re.search(r"python[3]?\s+(?:-c\s+[\"']import\s+(\w+)|(?:-m\s+(\w+)))", command)
    if m:
        return "PythonError", m.group(1) or m.group(2)

    # pip install foo
    m = re.search(r"pip[3]?\s+install\s+(\S+)", command)
    if m and not m.group(1).startswith("-"):
        return "PipInstallError", m.group(1)

    # npm install <package>
    m = re.search(r"npm\s+(?:install|i|add)\s+(\S+)", command)
    if m and not m.group(1).startswith("-"):
        return "NpmError", m.group(1)

    # npm run/start/test/build (no package)
    m = re.search(r"npm\s+(run|start|test|build)", command)
    if m:
        return "NpmError", None

    # cargo build/run/test
    m = re.search(r"cargo\s+(build|run|test|check)", command)
    if m:
        return "CargoError", None

    return None, None


def _generate_signature(command: str, stderr: str) -> str:
    """Generate a stable fingerprint for deduplication."""
    text = f"{command}\n{stderr[:500]}".lower()
    text = re.sub(r"\d+\.\d+\.\d+", "X.X.X", text)
    text = re.sub(r"(/[\w./\\]+)", "<path>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}[T_]\d{2}[_:]\d{2}[_:]\d{2}", "<ts>", text)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


async def monitor_node(state: TribalState) -> dict:
    """LangGraph node: detect and classify errors from shell events.

    Uses fast regex for common patterns. Leaves error_type/error_package as None
    for unrecognized errors so the inference node can call the LLM.
    """
    event = state["event"]

    is_error = event.exit_code != 0
    error_signature = ""
    error_type: str | None = None
    error_package: str | None = None

    if is_error:
        error_signature = _generate_signature(event.command, event.stderr)

        # Fast local classification
        error_type, error_package = _try_classify(event.stderr)

        # Fallback: infer from command when stderr is empty/unrecognized
        if not error_type:
            error_type, error_package = _classify_from_command(event.command)

    return {
        "is_error": is_error,
        "error_signature": error_signature,
        "error_package": error_package,
        "error_type": error_type,
        "log": [
            f"monitor: cmd='{event.command[:50]}'"
            f" exit={event.exit_code}"
            f" error={is_error} type={error_type}"
        ],
    }
