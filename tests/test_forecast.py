from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


def _rows(n: int) -> list[dict]:
    base = {
        "HUFL": 1.0,
        "HULL": 0.5,
        "MUFL": 1.0,
        "MULL": 0.8,
        "LUFL": 1.1,
        "LULL": 0.7,
        "OT": 1.3,
    }
    start = datetime(2023, 1, 1)
    return [
        {
            "date": (start + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M"),
            **base,
        }
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_forecast_success(async_client: AsyncClient) -> None:
    payload = {
        "data": _rows(520),
        "context_length": 512,
        "forecast_length": 96,
        "request_id": "t1",
    }
    r = await async_client.post("/forecast", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["request_id"] == "t1"
    assert "forecast" in body


@pytest.mark.asyncio
async def test_forecast_insufficient_rows(async_client: AsyncClient) -> None:
    payload = {
        "data": _rows(10),
        "context_length": 512,
        "forecast_length": 96,
    }
    r = await async_client.post("/forecast", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_forecast_validation(async_client: AsyncClient) -> None:
    r = await async_client.post("/forecast", json={"data": []})
    assert r.status_code == 422
