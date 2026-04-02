from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient) -> None:
    r = await async_client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready(async_client: AsyncClient) -> None:
    r = await async_client.get("/health/ready")
    assert r.status_code == 200
    data = r.json()
    assert data["ready"] is True


@pytest.mark.asyncio
async def test_health_legacy(async_client: AsyncClient) -> None:
    r = await async_client.get("/health")
    assert r.status_code == 200
