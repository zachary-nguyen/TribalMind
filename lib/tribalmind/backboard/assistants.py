"""Backboard assistant management.

Each project gets its own Backboard assistant (namespaced by project root hash).
An optional org-level assistant is used for team-wide knowledge sharing.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from tribalmind.backboard.client import BackboardClient

logger = logging.getLogger(__name__)


def project_hash(project_root: str) -> str:
    """Generate a short hash from the project root path for namespacing."""
    return hashlib.sha256(project_root.encode()).hexdigest()[:12]


def assistant_name(proj_hash: str) -> str:
    """Generate the standard assistant name for a project."""
    return f"tribalmind-{proj_hash}"


async def create_assistant(
    client: BackboardClient,
    name: str,
    system_prompt: str,
    embedding_provider: str = "openai",
    embedding_model: str = "text-embedding-3-small",
    embedding_dims: int = 1536,
) -> dict[str, Any]:
    """Create a new Backboard assistant."""
    return await client.post(
        "/assistants",
        json={
            "name": name,
            "system_prompt": system_prompt,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "embedding_dims": embedding_dims,
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
    embedding_provider: str = "openai",
    embedding_model: str = "text-embedding-3-small",
    embedding_dims: int = 1536,
) -> dict[str, Any]:
    """Find or create the Backboard assistant for a project.

    Uses the project root hash to generate a unique assistant name.
    """
    proj_hash = project_hash(project_root)
    name = assistant_name(proj_hash)

    # Search existing assistants
    assistants = await list_assistants(client)
    for a in assistants:
        if a.get("name") == name:
            logger.info("Found existing assistant %s for project %s", a.get("id"), project_root)
            return a

    # Create new assistant
    logger.info("Creating new assistant %s for project %s", name, project_root)
    system_prompt = (
        f"You are a developer knowledge agent for project at {project_root}. "
        "Store and retrieve error patterns, fixes, and contextual knowledge. "
        "When analyzing errors, identify the root cause, affected package, "
        "and suggest precise fixes."
    )
    return await create_assistant(
        client,
        name=name,
        system_prompt=system_prompt,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
        embedding_dims=embedding_dims,
    )
