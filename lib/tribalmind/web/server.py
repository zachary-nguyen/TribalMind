"""Lightweight FastAPI server for the TribalMind UI.

Exposes:
  GET /api/logs    — SSE stream of daemon log lines
  GET /api/status  — daemon running status
  /api/backboard/* — proxy to Backboard REST API
  GET /           — serves the built React frontend (ui/dist/)
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from tribalmind.config.settings import get_settings

logger = logging.getLogger(__name__)

app = FastAPI(title="TribalMind UI", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Backboard proxy helpers ──────────────────────────────────────────────────

def _get_client():
    """Lazy-create a BackboardClient (import here to avoid startup crash if no key)."""
    from tribalmind.backboard.client import create_client
    return create_client()


async def _proxy(
    method: str,
    path: str,
    body: dict | None = None,
    params: dict | None = None,
) -> Any:
    """Forward a request to the Backboard API and return JSON."""
    from tribalmind.backboard.client import BackboardError

    client = _get_client()
    try:
        result = await client.request(method, path, json=body, params=params)
        return result
    except BackboardError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)
    finally:
        await client.close()


# ── Backboard proxy: Assistants ──────────────────────────────────────────────

@app.get("/api/backboard/assistants")
async def proxy_list_assistants(skip: int = 0, limit: int = 100):
    return await _proxy("GET", "/assistants", params={"skip": skip, "limit": limit})


@app.get("/api/backboard/assistants/{assistant_id}")
async def proxy_get_assistant(assistant_id: str):
    return await _proxy("GET", f"/assistants/{assistant_id}")


@app.delete("/api/backboard/assistants/{assistant_id}")
async def proxy_delete_assistant(assistant_id: str):
    return await _proxy("DELETE", f"/assistants/{assistant_id}")


# ── Backboard proxy: Memories ────────────────────────────────────────────────

@app.get("/api/backboard/assistants/{assistant_id}/memories")
async def proxy_list_memories(assistant_id: str):
    return await _proxy("GET", f"/assistants/{assistant_id}/memories")


@app.post("/api/backboard/assistants/{assistant_id}/memories")
async def proxy_add_memory(assistant_id: str, request: Request):
    body = await request.json()
    return await _proxy("POST", f"/assistants/{assistant_id}/memories", body=body)


@app.post("/api/backboard/assistants/{assistant_id}/memories/search")
async def proxy_search_memories(assistant_id: str, request: Request):
    body = await request.json()
    return await _proxy("POST", f"/assistants/{assistant_id}/memories/search", body=body)


@app.put("/api/backboard/assistants/{assistant_id}/memories/{memory_id}")
async def proxy_update_memory(assistant_id: str, memory_id: str, request: Request):
    body = await request.json()
    return await _proxy("PUT", f"/assistants/{assistant_id}/memories/{memory_id}", body=body)


@app.delete("/api/backboard/assistants/{assistant_id}/memories/{memory_id}")
async def proxy_delete_memory(assistant_id: str, memory_id: str):
    return await _proxy("DELETE", f"/assistants/{assistant_id}/memories/{memory_id}")


@app.delete("/api/backboard/assistants/{assistant_id}/memories")
async def proxy_clear_memories(assistant_id: str):
    """Delete ALL memories for an assistant."""
    from tribalmind.backboard.client import BackboardError

    client = _get_client()
    try:
        result = await client.get(f"/assistants/{assistant_id}/memories")
        memories = (
            result if isinstance(result, list)
            else result.get("memories", result.get("data", []))
        )
        deleted = 0
        for m in memories:
            mid = m.get("memory_id", m.get("id", ""))
            if mid:
                await client.delete(f"/assistants/{assistant_id}/memories/{mid}")
                deleted += 1
        return {"deleted": deleted}
    except BackboardError as exc:
        raise HTTPException(status_code=exc.status_code or 502, detail=exc.detail)
    finally:
        await client.close()


# ── Backboard proxy: Threads ────────────────────────────────────────────────

@app.get("/api/backboard/threads")
async def proxy_list_threads(skip: int = 0, limit: int = 100):
    return await _proxy("GET", "/threads", params={"skip": skip, "limit": limit})


@app.get("/api/backboard/threads/{thread_id}")
async def proxy_get_thread(thread_id: str):
    return await _proxy("GET", f"/threads/{thread_id}")


@app.delete("/api/backboard/threads/{thread_id}")
async def proxy_delete_thread(thread_id: str):
    return await _proxy("DELETE", f"/threads/{thread_id}")


@app.post("/api/backboard/assistants/{assistant_id}/threads")
async def proxy_create_thread(assistant_id: str):
    return await _proxy("POST", f"/assistants/{assistant_id}/threads")


# ── Existing: Logs SSE + Status ──────────────────────────────────────────────

async def _tail_log_file(history_lines: int = 200):
    """Async generator that streams new lines from the daemon log file via SSE."""
    settings = get_settings()
    log_file = settings.log_file

    # Wait for log file to appear (daemon may not be started yet)
    while not log_file.exists():
        yield _sse({"type": "waiting", "message": "Waiting for daemon to start..."})
        await asyncio.sleep(1.0)

    with open(log_file, encoding="utf-8", errors="replace") as f:
        # Send last N lines of history so the page isn't empty on load
        all_lines = f.readlines()
        for line in all_lines[-history_lines:]:
            line = line.rstrip()
            if line:
                yield _sse({"type": "log", "line": line})

        # Tail new lines as they arrive
        while True:
            line = f.readline()
            if line:
                line = line.rstrip()
                if line:
                    yield _sse({"type": "log", "line": line})
            else:
                await asyncio.sleep(0.1)


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@app.get("/api/logs")
async def stream_logs(history: int = 200):
    """SSE endpoint — connect once and receive log lines as they arrive."""
    return StreamingResponse(
        _tail_log_file(history_lines=max(1, min(history, 10000))),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/status")
async def get_status():
    """Return whether the daemon process is currently running."""
    from tribalmind.daemon.manager import is_running, read_pid

    running = is_running()
    pid = read_pid()
    return {"running": running, "pid": pid}


# Serve built frontend — bundled inside the package at web/static/
_dist = Path(__file__).parent / "static"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
else:
    @app.get("/", response_class=HTMLResponse)
    async def no_build():
        return (
            "<!doctype html><html><head><title>TribalMind UI</title>"
            "<style>"
            "body{font-family:monospace;background:#0f172a;color:#94a3b8;"
            "display:flex;align-items:center;justify-content:center;"
            "height:100vh;margin:0;}"
            ".box{border:1px solid #1e293b;border-radius:8px;"
            "padding:2rem 2.5rem;max-width:480px;}"
            "h2{color:#f1f5f9;margin:0 0 1rem;}"
            "code{background:#1e293b;padding:2px 6px;"
            "border-radius:4px;color:#7dd3fc;}"
            "</style></head><body><div class='box'>"
            "<h2>Frontend not built</h2>"
            "<p>The React frontend hasn't been built yet. Run:</p>"
            "<pre><code>cd ui &amp;&amp; pnpm build</code></pre>"
            "<p>Or for dev mode with hot reload, open "
            "<code>http://localhost:5173</code> after running:</p>"
            "<pre><code>cd ui &amp;&amp; pnpm dev</code></pre>"
            "<p>The API is running — "
            "<a href='/api/status' style='color:#7dd3fc'>/api/status</a>"
            " is live.</p>"
            "</div></body></html>"
        )
