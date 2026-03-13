"""Async HTTP client for the Backboard API.

Wraps httpx.AsyncClient with authentication, error handling, and retry logic.
Base URL: https://app.backboard.io/api
Auth: X-API-Key header
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackboardError(Exception):
    """Base exception for Backboard API errors."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Backboard API error {status_code}: {detail}")


class BackboardClient:
    """Async client for the Backboard REST API."""

    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: Any = None,
    ) -> dict[str, Any]:
        """Make an authenticated API request and return JSON response."""
        try:
            response = await self._client.request(
                method, path, json=json, params=params, data=data, files=files,
            )
        except httpx.TimeoutException:
            raise BackboardError(0, f"Request to {path} timed out")
        except httpx.ConnectError:
            raise BackboardError(0, f"Could not connect to Backboard API at {self._client.base_url}")

        if response.status_code >= 400:
            detail = response.text
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                pass
            raise BackboardError(response.status_code, detail)

        if response.status_code == 204:
            return {}

        return response.json()

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("DELETE", path, **kwargs)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> BackboardClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


def create_client() -> BackboardClient:
    """Create a BackboardClient using the current settings and credentials."""
    from tribalmind.config.credentials import require_backboard_api_key
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    api_key = require_backboard_api_key()
    return BackboardClient(
        base_url=settings.backboard_base_url,
        api_key=api_key,
    )
