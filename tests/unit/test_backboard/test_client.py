"""Tests for the Backboard HTTP client."""

from __future__ import annotations

import httpx
import pytest
import respx
from tribalmind.backboard.client import BackboardClient, BackboardError


@pytest.fixture
def client():
    return BackboardClient(
        base_url="https://app.backboard.io/api",
        api_key="test-key",
    )


class TestBackboardClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_get_success(self, client):
        respx.get("https://app.backboard.io/api/assistants").mock(
            return_value=httpx.Response(200, json={"data": []})
        )
        result = await client.get("/assistants")
        assert result == {"data": []}

    @respx.mock
    @pytest.mark.asyncio
    async def test_post_success(self, client):
        respx.post("https://app.backboard.io/api/assistants").mock(
            return_value=httpx.Response(201, json={"id": "asst-123"})
        )
        result = await client.post("/assistants", json={"name": "test"})
        assert result["id"] == "asst-123"

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_key_header(self, client):
        route = respx.get("https://app.backboard.io/api/assistants").mock(
            return_value=httpx.Response(200, json={})
        )
        await client.get("/assistants")
        assert route.calls[0].request.headers["X-API-Key"] == "test-key"

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_response(self, client):
        respx.get("https://app.backboard.io/api/assistants/bad").mock(
            return_value=httpx.Response(404, json={"detail": "Not found"})
        )
        with pytest.raises(BackboardError) as exc_info:
            await client.get("/assistants/bad")
        assert exc_info.value.status_code == 404

    @respx.mock
    @pytest.mark.asyncio
    async def test_delete_204(self, client):
        respx.delete("https://app.backboard.io/api/assistants/123").mock(
            return_value=httpx.Response(204)
        )
        result = await client.delete("/assistants/123")
        assert result == {}

    @pytest.mark.asyncio
    async def test_context_manager(self):
        async with BackboardClient("https://app.backboard.io/api", "key") as client:
            assert client is not None
