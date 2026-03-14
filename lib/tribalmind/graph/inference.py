"""Inference Node - classifies errors and proposes solutions.

Three-stage approach:
1. Memory match (free, instant) — extract fix from known memories
2. Local classification (free, instant) — if monitor already classified the error,
   generate a fix from known patterns without calling the LLM
3. LLM fallback (paid, slow) — only for errors that couldn't be classified locally
   and have no memory match. Results are cached by error signature.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import OrderedDict

from tribalmind.graph.state import TribalState

logger = logging.getLogger(__name__)

# Confidence levels
LLM_FIX_CONFIDENCE = 0.6
LOCAL_FIX_CONFIDENCE = 0.7

# ── LLM response cache ──────────────────────────────────────────────
# Keyed by error_signature -> (result_dict, timestamp)
# Avoids calling the LLM for the same error twice in one daemon session.

_MAX_CACHE_SIZE = 256
_CACHE_TTL = 3600  # 1 hour
_llm_cache: OrderedDict[str, tuple[dict, float]] = OrderedDict()

# ── Rate limiting ────────────────────────────────────────────────────
_MAX_LLM_CALLS_PER_HOUR = 30
_llm_call_timestamps: list[float] = []

# ── Debounce ─────────────────────────────────────────────────────────
_DEBOUNCE_SECONDS = 60
_recent_signatures: dict[str, float] = {}


def _cache_get(signature: str) -> dict | None:
    """Look up a cached LLM result by error signature."""
    if signature in _llm_cache:
        result, ts = _llm_cache[signature]
        if time.time() - ts < _CACHE_TTL:
            _llm_cache.move_to_end(signature)
            logger.debug("LLM cache hit: sig=%s", signature[:12])
            return result
        else:
            del _llm_cache[signature]
    return None


def _cache_put(signature: str, result: dict) -> None:
    """Store an LLM result in the cache."""
    _llm_cache[signature] = (result, time.time())
    while len(_llm_cache) > _MAX_CACHE_SIZE:
        _llm_cache.popitem(last=False)


def _is_debounced(signature: str) -> bool:
    """Check if this signature was seen recently."""
    now = time.time()
    # Clean old entries
    expired = [k for k, t in _recent_signatures.items() if now - t > _DEBOUNCE_SECONDS]
    for k in expired:
        del _recent_signatures[k]

    if signature in _recent_signatures:
        logger.debug(
            "Debounced: sig=%s (seen %.0fs ago)",
            signature[:12], now - _recent_signatures[signature],
        )
        return True

    _recent_signatures[signature] = now
    return False


def _is_rate_limited() -> bool:
    """Check if we've exceeded the hourly LLM call budget."""
    now = time.time()
    cutoff = now - 3600
    _llm_call_timestamps[:] = [t for t in _llm_call_timestamps if t > cutoff]

    if len(_llm_call_timestamps) >= _MAX_LLM_CALLS_PER_HOUR:
        logger.warning("LLM rate limit reached (%d calls/hour)", _MAX_LLM_CALLS_PER_HOUR)
        return True
    return False


def _record_llm_call() -> None:
    _llm_call_timestamps.append(time.time())


# ── Known local fixes (no LLM needed) ───────────────────────────────

_LOCAL_FIXES: dict[str, str] = {
    "ModuleNotFoundError": "pip install {package}",
    "NodeModuleNotFound": "npm install {package}",
    "PipInstallError": "Check package name spelling or try: pip install {package} --upgrade",
    "CommandNotFound": "Install '{package}' or check your PATH",
    "GoPackageError": "go get {package}",
}


def _try_local_fix(error_type: str | None, package: str | None) -> str | None:
    """Generate a fix from local patterns if the error type is known."""
    if not error_type or error_type not in _LOCAL_FIXES:
        return None

    template = _LOCAL_FIXES[error_type]
    if "{package}" in template:
        if not package:
            return None
        return template.format(package=package)
    return template


# ── LLM prompt ───────────────────────────────────────────────────────

_LLM_PROMPT = """\
A developer ran a command in their terminal and it failed.

Command: {command}
Exit code: {exit_code}
Working directory: {cwd}
{stderr_section}
{context_section}
Analyze this error and respond with ONLY a JSON object (no markdown, no explanation):
{{
  "error_type": "<specific error category, e.g. ModuleNotFoundError>",
  "package": "<the package/module involved, or null>",
  "is_valid_package": "<true if real package, false if typo, null>",
  "fix": "<terminal command or short instruction, or null>",
  "explanation": "<one sentence explaining what went wrong>"
}}"""


def _build_llm_prompt(state: TribalState) -> str:
    """Build a prompt for the LLM to classify the error and suggest a fix."""
    event = state.get("event")
    if not event:
        return ""

    stderr_section = ""
    if event.stderr:
        stderr_section = f"Stderr output:\n{event.stderr[:1000]}"

    context_section = ""
    context = state.get("context")
    if context and context.upstream_info:
        info = context.upstream_info
        parts = []
        if info.get("known_issues"):
            parts.append(f"Related upstream issues: {info['known_issues'][:500]}")
        if info.get("latest_version"):
            parts.append(f"Latest version: {info['latest_version']}")
        if parts:
            context_section = "\n".join(parts)

    return _LLM_PROMPT.format(
        command=event.command,
        exit_code=event.exit_code,
        cwd=event.cwd,
        stderr_section=stderr_section,
        context_section=context_section,
    )


def _parse_llm_response(response: dict) -> dict | None:
    """Parse the LLM's JSON response into a structured result."""
    content = response.get("content", "")
    if not content:
        messages = response.get("messages", [])
        if messages:
            last = messages[-1] if isinstance(messages, list) else messages
            content = last.get("content", "") if isinstance(last, dict) else str(last)

    if not content:
        return None

    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", content.strip())
    cleaned = re.sub(r"\n?```$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if cleaned:
            return {"fix": cleaned, "error_type": "UnknownError"}
        return None


async def _query_llm(state: TribalState) -> dict | None:
    """Send the error to Backboard's message API for LLM analysis."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.threads import create_thread, delete_thread, send_message
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    assistant_id = settings.project_assistant_id
    if not assistant_id:
        logger.warning("No project assistant configured, skipping LLM inference")
        return None

    prompt = _build_llm_prompt(state)
    thread_id = None

    try:
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

            result = _parse_llm_response(response)

            if thread_id:
                try:
                    await delete_thread(client, thread_id)
                except Exception:
                    pass

            return result

    except Exception as e:
        logger.warning("LLM inference failed: %s", e)

    return None


# Keep for backwards compatibility with existing imports in tests
def _extract_fix_from_response(response: dict) -> str | None:
    """Extract fix text from a Backboard message response."""
    parsed = _parse_llm_response(response)
    if parsed:
        return parsed.get("fix")
    return None


async def inference_node(state: TribalState) -> dict:
    """LangGraph node: classify error and suggest fixes.

    Cost-saving pipeline:
    1. Memory match (free) — known fix from Backboard memories
    2. Local fix (free) — if monitor classified it, use pattern-based fix
    3. LLM cache hit (free) — same error signature seen before
    4. LLM call (paid) — only if debounce + rate limit allow
    """
    suggested_fix: str | None = None
    fix_confidence = 0.0
    source = "none"
    error_type = state.get("error_type")
    error_package = state.get("error_package")
    error_signature = state.get("error_signature", "")

    # ── Stage 1: Memory match (free) ────────────────────────────────
    if state.get("has_known_fix") and state.get("context"):
        context = state["context"]
        for match in [*context.local_matches, *context.team_matches]:
            if hasattr(match, "fix_text") and match.fix_text:
                suggested_fix = match.fix_text
                fix_confidence = getattr(match, "relevance_score", 0.7)
                source = "memory"
                break

    # ── Stage 2: Local fix (free) ───────────────────────────────────
    if not suggested_fix and error_type:
        local_fix = _try_local_fix(error_type, error_package)
        if local_fix:
            suggested_fix = local_fix
            fix_confidence = LOCAL_FIX_CONFIDENCE
            source = "local"

    # ── Stage 3: LLM (paid) — with cache, debounce, rate limit ─────
    if not suggested_fix and state.get("is_error"):
        # 3a: Check cache first
        if error_signature:
            cached = _cache_get(error_signature)
            if cached:
                error_type = cached.get("error_type") or error_type
                error_package = cached.get("package") or error_package
                fix = cached.get("fix")
                is_valid = cached.get("is_valid_package")
                explanation = cached.get("explanation", "")

                if fix:
                    if is_valid is False:
                        suggested_fix = explanation or f"Package '{error_package}' does not exist"
                        fix_confidence = 0.9
                    else:
                        suggested_fix = fix
                        fix_confidence = LLM_FIX_CONFIDENCE
                    source = "cache"

        # 3b: LLM call (gated by debounce + rate limit)
        if not suggested_fix and error_signature:
            skip_reason = None
            if _is_debounced(error_signature):
                skip_reason = "debounced"
            elif _is_rate_limited():
                skip_reason = "rate_limited"

            if skip_reason:
                logger.info("Skipping LLM call: %s (sig=%s)", skip_reason, error_signature[:12])
            else:
                _record_llm_call()
                llm_result = await _query_llm(state)
                if llm_result:
                    # Cache the result
                    _cache_put(error_signature, llm_result)

                    error_type = llm_result.get("error_type") or error_type
                    error_package = llm_result.get("package") or error_package
                    fix = llm_result.get("fix")
                    is_valid = llm_result.get("is_valid_package")
                    explanation = llm_result.get("explanation", "")

                    if fix:
                        if is_valid is False:
                            suggested_fix = (
                                explanation
                                or f"Package '{error_package}' does not exist"
                            )
                            fix_confidence = 0.9
                        else:
                            suggested_fix = fix
                            fix_confidence = LLM_FIX_CONFIDENCE
                        source = "llm"

                    logger.info(
                        "LLM analysis: type=%s pkg=%s valid=%s fix=%s",
                        error_type, error_package, is_valid,
                        (fix or "none")[:80],
                    )

    return {
        "suggested_fix": suggested_fix,
        "fix_confidence": fix_confidence,
        "error_type": error_type,
        "error_package": error_package,
        "log": [
            f"inference: fix={'yes' if suggested_fix else 'no'} "
            f"confidence={fix_confidence:.2f} source={source}"
        ],
    }
