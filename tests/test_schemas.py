from __future__ import annotations

import pytest
from app.schemas.requests import FineTuneRequest, ForecastRow
from pydantic import ValidationError


def test_forecast_row() -> None:
    r = ForecastRow(
        date="2023-01-01",
        HUFL=1.0,
        HULL=0.5,
        MUFL=1.0,
        MULL=0.8,
        LUFL=1.1,
        LULL=0.7,
        OT=1.2,
    )
    assert r.date == "2023-01-01"


def test_fewshot_percent_range() -> None:
    row = ForecastRow(
        date="2023-01-01",
        HUFL=1.0,
        HULL=0.5,
        MUFL=1.0,
        MULL=0.8,
        LUFL=1.1,
        LULL=0.7,
        OT=1.2,
    )
    with pytest.raises(ValidationError):
        FineTuneRequest(data=[row], fewshot_percent=0)
    with pytest.raises(ValidationError):
        FineTuneRequest(data=[row], fewshot_percent=101)
