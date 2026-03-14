"""Monitor Node - intercepts shell execution and classifies errors.

Parses stderr output to identify error types, affected packages, and generates
error fingerprints for deduplication and matching.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from tribalmind.graph.state import TribalState


@dataclass
class ParsedError:
    """Result of parsing an error from stderr output."""

    error_type: str = ""
    package: str = ""
    message: str = ""
    signature: str = ""


# Regex patterns for common error types
PYTHON_TRACEBACK = re.compile(
    r"(?:Traceback \(most recent call last\):.*?)?(\w+Error|\w+Exception|\w+Warning):\s*(.+)",
    re.DOTALL,
)
PYTHON_MODULE_NOT_FOUND = re.compile(
    r"ModuleNotFoundError: No module named ['\"](\w[\w.]*)['\"]"
)
PYTHON_IMPORT_ERROR = re.compile(
    r"ImportError: cannot import name ['\"](\w+)['\"] from ['\"](\w[\w.]*)['\"]"
)

NODE_ERROR = re.compile(r"Error:\s+Cannot find module ['\"]([^'\"]+)['\"]")
NODE_ERR = re.compile(r"npm ERR!\s+(.+)")

RUST_ERROR = re.compile(r"error\[E(\d+)\]:\s*(.+)")

GO_PANIC = re.compile(r"panic:\s*(.+)")
GO_ERROR = re.compile(r"cannot find package \"([^\"]+)\"")

COMMAND_NOT_FOUND = re.compile(r"(\S+):\s*command not found")
PERMISSION_DENIED = re.compile(r"Permission denied")

PIP_ERROR = re.compile(
    r"ERROR: (?:Could not find a version|No matching distribution).+?(\S+)"
)
NPM_INSTALL_ERROR = re.compile(r"npm ERR! 404\s+Not Found.+?(\S+)")


def _generate_signature(error_type: str, package: str, message: str) -> str:
    """Generate a stable fingerprint for deduplication."""
    # Normalize: lowercase, strip version numbers, strip paths
    normalized = f"{error_type}:{package}:{message[:100]}".lower()
    normalized = re.sub(r"\d+\.\d+\.\d+", "X.X.X", normalized)
    normalized = re.sub(r"(/[\w./]+)", "<path>", normalized)
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


def parse_error(stderr: str) -> ParsedError:
    """Parse stderr output to extract error information."""
    result = ParsedError()

    if not stderr:
        return result

    # Python: ModuleNotFoundError
    m = PYTHON_MODULE_NOT_FOUND.search(stderr)
    if m:
        result.error_type = "ModuleNotFoundError"
        result.package = m.group(1).split(".")[0]
        result.message = f"No module named '{m.group(1)}'"
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Python: ImportError
    m = PYTHON_IMPORT_ERROR.search(stderr)
    if m:
        result.error_type = "ImportError"
        result.package = m.group(2).split(".")[0]
        result.message = f"cannot import name '{m.group(1)}' from '{m.group(2)}'"
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Python: general traceback
    m = PYTHON_TRACEBACK.search(stderr)
    if m:
        result.error_type = m.group(1)
        result.message = m.group(2).strip()
        # Try to extract package from the traceback file paths
        file_match = re.search(r'File ".*?/(?:site-packages|lib)/(\w+)', stderr)
        if file_match:
            result.package = file_match.group(1)
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Node.js: module not found
    m = NODE_ERROR.search(stderr)
    if m:
        result.error_type = "ModuleNotFoundError"
        result.package = m.group(1).split("/")[0].lstrip("@")
        result.message = f"Cannot find module '{m.group(1)}'"
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # npm error
    m = NODE_ERR.search(stderr)
    if m:
        result.error_type = "NpmError"
        result.message = m.group(1)
        npm_pkg = NPM_INSTALL_ERROR.search(stderr)
        if npm_pkg:
            result.package = npm_pkg.group(1)
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Rust compiler error
    m = RUST_ERROR.search(stderr)
    if m:
        result.error_type = f"RustError[E{m.group(1)}]"
        result.message = m.group(2)
        result.signature = _generate_signature(result.error_type, "", result.message)
        return result

    # Go panic
    m = GO_PANIC.search(stderr)
    if m:
        result.error_type = "GoPanic"
        result.message = m.group(1)
        result.signature = _generate_signature(result.error_type, "", result.message)
        return result

    # Go package error
    m = GO_ERROR.search(stderr)
    if m:
        result.error_type = "GoPackageError"
        result.package = m.group(1)
        result.message = f"cannot find package '{m.group(1)}'"
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Command not found
    m = COMMAND_NOT_FOUND.search(stderr)
    if m:
        result.error_type = "CommandNotFound"
        result.package = m.group(1)
        result.message = f"{m.group(1)}: command not found"
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # pip install error
    m = PIP_ERROR.search(stderr)
    if m:
        result.error_type = "PipInstallError"
        result.package = m.group(1)
        result.message = stderr.strip()[:200]
        result.signature = _generate_signature(result.error_type, result.package, result.message)
        return result

    # Permission denied
    if PERMISSION_DENIED.search(stderr):
        result.error_type = "PermissionDenied"
        result.message = stderr.strip()[:200]
        result.signature = _generate_signature(result.error_type, "", result.message)
        return result

    # Generic error (non-zero exit but unknown pattern)
    result.error_type = "UnknownError"
    result.message = stderr.strip()[:200]
    result.signature = _generate_signature(result.error_type, "", result.message)
    return result


async def monitor_node(state: TribalState) -> dict:
    """LangGraph node: parse shell event and classify errors."""
    event = state["event"]

    is_error = event.exit_code != 0
    error_signature = ""
    error_package: str | None = None
    error_type: str | None = None

    if is_error:
        parsed = parse_error(event.stderr)
        error_signature = parsed.signature
        error_package = parsed.package or None
        error_type = parsed.error_type or None

    return {
        "is_error": is_error,
        "error_signature": error_signature,
        "error_package": error_package,
        "error_type": error_type,
        "log": [f"monitor: cmd='{event.command[:50]}' exit={event.exit_code} error={is_error}"],
    }
