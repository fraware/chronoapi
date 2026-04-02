from __future__ import annotations

import logging

import torch
import torch.nn as nn
from tsfm_public.toolkit.get_model import get_model

from app.config import settings

logger = logging.getLogger("forecasting_service")

TTM_MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"
CONTEXT_LENGTH = 512
PREDICTION_LENGTH = 96


class DummyForecastModel(nn.Module):
    """Minimal stand-in when SKIP_MODEL_LOAD=1 (CI/local API tests)."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _b, _t, c = x.shape
        horizon = PREDICTION_LENGTH
        return torch.zeros(1, horizon, c, dtype=x.dtype, device=x.device)


def _load_real() -> nn.Module:
    try:
        m = get_model(
            model_path=TTM_MODEL_PATH,
            context_length=CONTEXT_LENGTH,
            prediction_length=PREDICTION_LENGTH,
        )
        m.eval()
        return m
    except Exception as e:
        raise RuntimeError(f"Failed to load TTM model: {e}") from e


def load_inference_model() -> nn.Module:
    if settings.skip_model_load:
        logger.warning("SKIP_MODEL_LOAD=1: using dummy forecast model")
        return DummyForecastModel().eval()
    return _load_real()


def is_production_model_loaded() -> bool:
    return not settings.skip_model_load
