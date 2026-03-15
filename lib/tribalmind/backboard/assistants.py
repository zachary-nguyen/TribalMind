"""Backboard assistant management.

Each project gets its own Backboard assistant (namespaced by project root hash).
An optional org-level assistant is used for team-wide knowledge sharing.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from tribalmind.backboard.client import BackboardClient

logger = logging.getLogger(__name__)


def _get_project_identifier(project_root: str) -> str:
    """Derive a stable project identifier that is the same across machines.

    Uses the git remote URL if available, otherwise falls back to the
    directory name. This ensures team members sharing a Backboard API key
    land on the same assistant regardless of local path.
    """
    import subprocess
    from pathlib import Path

    # Special case for global init
    if project_root == "global":
        return "global"

    root = Path(project_root)

    # Try git remote origin URL (most reliable for teams)
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass

    # Fall back to directory name (stable across machines if repos are named the same)
    return root.name


def project_hash(project_root: str) -> str:
    """Generate a short hash for namespacing, stable across machines."""
    identifier = _get_project_identifier(project_root)
    return hashlib.sha256(identifier.encode()).hexdigest()[:12]


def _get_repo_name(project_root: str) -> str:
    """Extract a short repo name for display in assistant names."""
    from pathlib import Path

    if project_root == "global":
        return "global"

    identifier = _get_project_identifier(project_root)

    # If it's a git URL, extract the repo name from it
    # e.g. "https://github.com/user/MyRepo.git" -> "MyRepo"
    # e.g. "git@github.com:user/MyRepo.git" -> "MyRepo"
    name = identifier.rstrip("/").rsplit("/", 1)[-1]
    name = name.rsplit(":", 1)[-1]  # handle git@...:user/repo
    name = name.removesuffix(".git")

    if not name:
        name = Path(project_root).name

    return name


def assistant_name(project_root: str) -> str:
    """Generate the standard assistant name for a project.

    Uses just the repo name. If there's a collision (checked at creation time),
    a short hash suffix is appended.
    """
    return _get_repo_name(project_root)


async def create_assistant(
    client: BackboardClient,
    name: str,
    system_prompt: str,
) -> dict[str, Any]:
    """Create a new Backboard assistant.

    Embedding config (provider, model, dims) is determined server-side
    and cannot be overridden via the API.
    """
    return await client.post(
        "/assistants",
        json={
            "name": name,
            "system_prompt": system_prompt,
        },
    )


async def list_assistants(
    client: BackboardClient,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List all assistants."""
    result = await client.get("/assistants", params={"skip": skip, "limit": limit})
    # API may return a list directly or wrapped in a key
    if isinstance(result, list):
        return result
    return result.get("assistants", result.get("data", []))


async def get_assistant(client: BackboardClient, assistant_id: str) -> dict[str, Any]:
    """Get a single assistant by ID."""
    return await client.get(f"/assistants/{assistant_id}")


async def delete_assistant(client: BackboardClient, assistant_id: str) -> None:
    """Delete an assistant and all its threads/documents."""
    await client.delete(f"/assistants/{assistant_id}")


async def get_or_create_project_assistant(
    client: BackboardClient,
    project_root: str,
) -> dict[str, Any]:
    """Find or create the Backboard assistant for a project.

    Uses the repo name as the assistant name. If a collision is detected
    at creation time, a short hash suffix is appended.
    """
    name = assistant_name(project_root)
    proj_hash = project_hash(project_root)

    # Check all possible names (current + legacy formats)
    name_with_hash = f"{name}-{proj_hash}"
    legacy_names = {f"tribalmind-{proj_hash}", f"tribal-{name}-{proj_hash}"}
    match_names = {name, name_with_hash} | legacy_names

    assistants = await list_assistants(client)
    for a in assistants:
        if a.get("name") in match_names:
            logger.info(
                "Found existing assistant %s for project %s",
                a.get("assistant_id"), project_root,
            )
            return a

    # Check for name collision (same name, different project)
    existing_names = {a.get("name") for a in assistants}
    if name in existing_names:
        name = name_with_hash
        logger.info("Name collision, using %s for project %s", name, project_root)

    # Create new assistant
    logger.info("Creating new assistant %s for project %s", name, project_root)
    identifier = _get_project_identifier(project_root)
    from tribalmind.backboard.memory import MEMORY_SCHEMA

    schema_str = json.dumps(MEMORY_SCHEMA, indent=2)
    system_prompt = (
        f"You are a developer knowledge agent for project '{identifier}'. "
        "Store and retrieve developer knowledge including: error patterns and fixes, "
        "codebase conventions and patterns, tips and best practices, architectural "
        "decisions, environment quirks, and any other knowledge that helps the team "
        "work effectively.\n\n"
        f"All memories conform to this schema:\n{schema_str}"
    )
    return await create_assistant(
        client,
        name=name,
        system_prompt=system_prompt,
    )
