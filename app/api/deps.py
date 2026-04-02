from __future__ import annotations

from typing import Annotated

import torch
from fastapi import Depends, Request


def get_forecast_model(request: Request) -> torch.nn.Module:
    return request.app.state.forecast_model


ForecastModelDep = Annotated[torch.nn.Module, Depends(get_forecast_model)]
