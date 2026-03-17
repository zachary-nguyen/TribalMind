"""CLI command for adding knowledge to project memory via natural language.

Accepts free-form text (argument or stdin), uses the LLM to parse it into
structured memory fields, and stores it in the project's Backboard assistant.

Designed for both humans and agents:
    tribal remember "numpy 1.26 breaks with Python 3.13, pin to <1.26"
    echo "redis ECONNREFUSED means the container is down" | tribal remember
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys

import typer
from rich.console import Console

from tribalmind.backboard.memory import VALID_CATEGORIES

logger = logging.getLogger(__name__)
console = Console()

_PARSE_PROMPT = """\
You are a developer knowledge parser. Convert the following free-form text into
a structured JSON object for storage in a team knowledge base.

Text: {text}

Respond with ONLY a JSON object (no markdown, no explanation) with these three
fields:
  "category" — one of the values listed below
  "subject"  — short label for what this knowledge is about
  "content"  — the actual insight, fix, pattern, or description

Categories (pick the single best fit):
  fix          = error pattern, workaround, or gotcha
  convention   = codebase pattern, naming rule, or style decision
  architecture = how modules connect, why things are built a certain way
  context      = project description, team info, onboarding knowledge
  decision     = trade-off considered, what was chosen and why
  tip          = best practice, useful trick, or shortcut
  workflow     = multi-step process, runbook, or repeatable procedure

Rules:
- subject should be a short label (e.g. "auth module", "CI pipeline")
- content is the most important field — always extract the key insight
- If the text is already structured, preserve the original meaning exactly"""


def _parse_llm_response(content: str) -> dict | None:
    """Extract JSON from an LLM response, stripping markdown fences.

    Handles multiple response formats:
    - Plain JSON string
    - Markdown-fenced JSON
    - Gemini-style content blocks: [{"type": "text", "text": "..."}]
    """
    if not content:
        return None

    cleaned = content.strip()

    # Handle content-block arrays: [{"type":"text","text":"..."}]
    # Backboard may return these as Python repr strings (single-quoted) rather
    # than JSON, so try ast.literal_eval as a fallback.
    if cleaned.startswith("["):
        import ast

        for loader in (json.loads, ast.literal_eval):
            try:
                maybe_list = loader(cleaned)
                if isinstance(maybe_list, list) and maybe_list:
                    first = maybe_list[0]
                    if isinstance(first, dict) and "text" in first:
                        cleaned = first["text"].strip()
                        break
            except (json.JSONDecodeError, ValueError, TypeError, SyntaxError):
                continue

    # Strip markdown fences
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        return None


async def _parse_with_llm(text: str) -> dict | None:
    """Send text to the LLM for structured parsing."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.threads import create_thread, delete_thread, send_message
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    assistant_id = settings.project_assistant_id
    if not assistant_id:
        return None

    prompt = _PARSE_PROMPT.format(text=text)
    thread_id = None

    async with create_client() as client:
        thread = await create_thread(client, assistant_id)
        thread_id = thread.get("thread_id", "")

        response = await send_message(
            client,
            thread_id,
            prompt,
            llm_provider=settings.llm_provider,
            model_name=settings.model_name,
        )

        # Extract content from response
        logger.debug("LLM raw response: %s", response)
        content = response.get("content", "")
        if not content:
            messages = response.get("messages", [])
            if messages:
                last = messages[-1] if isinstance(messages, list) else messages
                content = last.get("content", "") if isinstance(last, dict) else str(last)

        logger.debug("Extracted content for parsing: %r", content)
        result = _parse_llm_response(content)

        if thread_id:
            try:
                await delete_thread(client, thread_id)
            except Exception:
                pass

        return result


async def _store_memory(text: str) -> dict:
    """Parse text with LLM and store as a new Backboard memory."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.memory import add_memory, encode_memory
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    assistant_id = settings.project_assistant_id
    if not assistant_id:
        console.print("[red]No project assistant configured.[/red]")
        console.print("Run [bold]tribal init[/bold] first to set up your project.")
        raise typer.Exit(1)

    # Parse with LLM
    parsed = await _parse_with_llm(text)

    if not parsed or not parsed.get("content"):
        # Fallback: store raw text as a 'context' memory
        logger.debug("LLM parsing failed or returned no content; using fallback")
        console.print(
            "[yellow]LLM parsing failed — storing as raw context.[/yellow]"
        )
        parsed = {
            "category": "context",
            "subject": "",
            "content": text,
        }
    else:
        # Validate the category returned by the LLM
        cat = parsed.get("category", "").lower().strip()
        if cat not in VALID_CATEGORIES:
            logger.debug("LLM returned invalid category %r; defaulting to 'context'", cat)
            parsed["category"] = "context"

    encoded = encode_memory(
        parsed["category"],
        subject=parsed.get("subject", ""),
        content=parsed.get("content", ""),
    )

    metadata = {
        "category": parsed["category"],
        "subject": parsed.get("subject", ""),
    }

    async with create_client() as client:
        await add_memory(client, assistant_id, encoded, metadata=metadata)

    return parsed


def remember(
    text: list[str] | None = typer.Argument(  # noqa: UP007
        default=None,
        help="Knowledge to remember (or pipe via stdin).",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output result as JSON (for agent consumption).",
    ),
) -> None:
    """Add knowledge to project memory using natural language.

    The LLM parses your input into structured fields (category, subject,
    content) and stores it in Backboard.

    \b
    Examples:
        tribal remember "numpy 1.26 breaks on Python 3.13 — pin to <1.26"
        tribal remember "if redis gives ECONNREFUSED, restart the container"
        tribal remember "our staging DB is on port 5433, not 5432"
        echo "use --legacy-peer-deps for React 18 installs" | tribal remember
    """
    # Collect input from args or stdin
    if text:
        input_text = " ".join(text)
    elif not sys.stdin.isatty():
        input_text = sys.stdin.read().strip()
    else:
        console.print(
            "[yellow]No input provided.[/yellow]"
            " Pass text as an argument or pipe via stdin."
        )
        raise typer.Exit(1)

    if not input_text:
        console.print("[yellow]Empty input — nothing to remember.[/yellow]")
        raise typer.Exit(1)

    # LLM-powered parsing
    if not json_output:
        with console.status("[bold #a78bfa]Parsing with LLM...[/bold #a78bfa]"):
            parsed = asyncio.run(_store_memory(input_text))
    else:
        parsed = asyncio.run(_store_memory(input_text))

    from tribalmind.activity import log_activity
    log_activity(
        "remember",
        parsed.get("content", input_text[:120]),
        query=input_text,
        metadata={
            "category": parsed.get("category", "context"),
            "subject": parsed.get("subject", ""),
        },
    )

    if json_output:
        typer.echo(json.dumps({"stored": True, **parsed}))
        return

    category = parsed.get("category", "context")
    subject = parsed.get("subject", "")
    content = parsed.get("content", input_text[:80])
    console.print(f"[green]Remembered:[/green] [{category}]", end="")
    if subject:
        console.print(f" [#a78bfa]{subject}[/#a78bfa]", end="")
    console.print()
    console.print(f"  {content}")
