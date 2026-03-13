"""Backboard thread and message management.

Threads are persistent conversation sessions. Messages can be sent with
configurable LLM provider and model, leveraging Backboard's 2200+ model catalog.
"""

from __future__ import annotations

from typing import Any

from tribalmind.backboard.client import BackboardClient


async def create_thread(
    client: BackboardClient,
    assistant_id: str,
) -> dict[str, Any]:
    """Create a new thread for an assistant."""
    return await client.post(f"/assistants/{assistant_id}/threads")


async def get_thread(
    client: BackboardClient,
    thread_id: str,
) -> dict[str, Any]:
    """Get thread details including message history."""
    return await client.get(f"/threads/{thread_id}")


async def delete_thread(
    client: BackboardClient,
    thread_id: str,
) -> None:
    """Delete a thread."""
    await client.delete(f"/threads/{thread_id}")


async def send_message(
    client: BackboardClient,
    thread_id: str,
    content: str,
    *,
    memory_mode: str = "Auto",
    llm_provider: str | None = None,
    model_name: str | None = None,
    stream: bool = False,
) -> dict[str, Any]:
    """Send a message to a thread and get an LLM response.

    Uses Backboard's multi-provider model selection. If provider/model are not
    specified, the assistant's defaults are used.
    """
    payload: dict[str, Any] = {
        "content": content,
        "stream": stream,
        "memory": memory_mode,
    }
    if llm_provider:
        payload["llm_provider"] = llm_provider
    if model_name:
        payload["model_name"] = model_name

    return await client.post(
        f"/threads/{thread_id}/messages",
        data=payload,
    )


async def list_threads(
    client: BackboardClient,
    skip: int = 0,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List all threads."""
    result = await client.get("/threads", params={"skip": skip, "limit": limit})
    if isinstance(result, list):
        return result
    return result.get("threads", result.get("data", []))
