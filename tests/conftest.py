from __future__ import annotations

import os

os.environ.setdefault("SKIP_MODEL_LOAD", "1")
os.environ.setdefault("KAFKA_ENABLED", "false")

import pytest
import torch
from app.api.factory import create_app
from httpx import ASGITransport, AsyncClient


class FakeForecastModel(torch.nn.Module):
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _b, _t, c = x.shape
        return torch.zeros(1, 96, c, dtype=x.dtype, device=x.device)


@pytest.fixture
def fake_model() -> torch.nn.Module:
    return FakeForecastModel().eval()


@pytest.fixture
async def async_client(fake_model: torch.nn.Module):
    app = create_app(forecast_model=fake_model)
    # Older httpx ASGITransport does not run Starlette lifespan; mirror startup state.
    app.state.forecast_model = fake_model
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
