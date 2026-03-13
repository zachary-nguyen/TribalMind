"""Upstream GitHub integration for checking package health.

Searches for related issues and releases when errors are detected,
helping correlate local errors with known upstream bugs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Common Python package -> GitHub repo mappings
KNOWN_REPOS: dict[str, str] = {
    "requests": "psf/requests",
    "flask": "pallets/flask",
    "django": "django/django",
    "fastapi": "tiangolo/fastapi",
    "pydantic": "pydantic/pydantic",
    "httpx": "encode/httpx",
    "numpy": "numpy/numpy",
    "pandas": "pandas-dev/pandas",
    "pytest": "pytest-dev/pytest",
    "celery": "celery/celery",
    "sqlalchemy": "sqlalchemy/sqlalchemy",
    "typer": "tiangolo/typer",
    "rich": "Textualize/rich",
    "langchain": "langchain-ai/langchain",
    "langgraph": "langchain-ai/langgraph",
}


def _get_repo_name(package: str) -> str | None:
    """Map a package name to its GitHub repository."""
    return KNOWN_REPOS.get(package.lower())


async def check_package_health(
    package: str,
    error_type: str,
) -> dict[str, Any] | None:
    """Check upstream GitHub for issues related to an error.

    Runs PyGithub calls in a thread to avoid blocking the async event loop.
    """
    repo_name = _get_repo_name(package)
    if not repo_name:
        return None

    try:
        result = await asyncio.to_thread(
            _check_github_sync, repo_name, error_type, package
        )
        return result
    except Exception as e:
        logger.warning("GitHub check failed for %s: %s", package, e)
        return None


def _check_github_sync(
    repo_name: str,
    error_type: str,
    package: str,
) -> dict[str, Any] | None:
    """Synchronous GitHub API calls (run in thread)."""
    from tribalmind.config.credentials import get_github_token

    try:
        from github import Github
    except ImportError:
        logger.warning("PyGithub not installed, skipping upstream check")
        return None

    token = get_github_token()
    gh = Github(token) if token else Github()

    try:
        repo = gh.get_repo(repo_name)
    except Exception:
        logger.warning("Could not access repo %s", repo_name)
        return None

    result: dict[str, Any] = {
        "repo": repo_name,
        "package": package,
        "matching_issues": [],
        "latest_release": None,
        "is_known_bug": False,
    }

    # Search open issues for the error type
    if error_type:
        try:
            issues = repo.get_issues(state="open", sort="updated", direction="desc")
            count = 0
            for issue in issues:
                if count >= 50:  # Limit search depth
                    break
                count += 1
                title_lower = issue.title.lower()
                if error_type.lower() in title_lower or package.lower() in title_lower:
                    result["matching_issues"].append({
                        "number": issue.number,
                        "title": issue.title,
                        "url": issue.html_url,
                        "created_at": issue.created_at.isoformat(),
                        "labels": [l.name for l in issue.labels],
                    })
                    if len(result["matching_issues"]) >= 3:
                        break
        except Exception as e:
            logger.warning("Issue search failed: %s", e)

    # Get latest release
    try:
        releases = repo.get_releases()
        if releases.totalCount > 0:
            latest = releases[0]
            result["latest_release"] = {
                "tag": latest.tag_name,
                "name": latest.title,
                "url": latest.html_url,
                "published_at": latest.published_at.isoformat() if latest.published_at else None,
            }
    except Exception as e:
        logger.warning("Release check failed: %s", e)

    result["is_known_bug"] = len(result["matching_issues"]) > 0
    return result
