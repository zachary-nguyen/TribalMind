"""Lightweight FastAPI server for the TribalMind live log UI.

Exposes:
  GET /api/logs    — SSE stream of daemon log lines
  GET /api/status  — daemon running status
  GET /           — serves the built React frontend (ui/dist/)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from tribalmind.config.settings import get_settings

app = FastAPI(title="TribalMind UI", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


async def _tail_log_file():
    """Async generator that streams new lines from the daemon log file via SSE."""
    settings = get_settings()
    log_file = settings.log_file

    # Wait for log file to appear (daemon may not be started yet)
    while not log_file.exists():
        yield _sse({"type": "waiting", "message": "Waiting for daemon to start..."})
        await asyncio.sleep(1.0)

    with open(log_file) as f:
        # Send last 200 lines of history so the page isn't empty on load
        all_lines = f.readlines()
        for line in all_lines[-200:]:
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
async def stream_logs():
    """SSE endpoint — connect once and receive log lines as they arrive."""
    return StreamingResponse(
        _tail_log_file(),
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
        return """<!doctype html>
<html><head><title>TribalMind UI</title>
<style>body{font-family:monospace;background:#0f172a;color:#94a3b8;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}
.box{border:1px solid #1e293b;border-radius:8px;padding:2rem 2.5rem;max-width:480px;}
h2{color:#f1f5f9;margin:0 0 1rem;}code{background:#1e293b;padding:2px 6px;border-radius:4px;color:#7dd3fc;}</style>
</head><body><div class="box">
<h2>Frontend not built</h2>
<p>The React frontend hasn't been built yet. Run:</p>
<pre><code>cd ui &amp;&amp; pnpm build</code></pre>
<p>Or for dev mode with hot reload, open <code>http://localhost:5173</code> after running:</p>
<pre><code>cd ui &amp;&amp; pnpm dev</code></pre>
<p>The API is running — <a href="/api/status" style="color:#7dd3fc">/api/status</a> is live.</p>
</div></body></html>"""
