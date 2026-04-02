"""
Forecast inference.

The TTM model expects a tensor of shape (batch, context_length, num_targets) built from
the multivariate columns in ``target_columns``, in order. A ``TimeSeriesPreprocessor``
is constructed with the same column spec as fine-tuning for API consistency; the
forward pass uses the recent raw window aligned with the default granite-tsfm
inference examples. If you rely on scaler state from training, switch this path to
use the preprocessor's transform output instead of raw ``values``.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import torch
from tsfm_public import TimeSeriesPreprocessor

from app.services.constants import column_specifiers, target_columns, timestamp_column

logger = logging.getLogger("forecasting_service")


def run_forecast(request_data: dict[str, Any], model: torch.nn.Module) -> list:
    df = pd.DataFrame(request_data["data"])
    df[timestamp_column] = pd.to_datetime(df[timestamp_column])
    ctx = request_data["context_length"]
    if len(df) < ctx:
        raise ValueError(f"Insufficient historical data. At least {ctx} rows required.")

    TimeSeriesPreprocessor(
        **column_specifiers,
        context_length=ctx,
        prediction_length=request_data["forecast_length"],
        scaling=True,
        encode_categorical=False,
        scaler_type="standard",
    )

    df_recent = df.tail(ctx)
    input_tensor = torch.tensor(df_recent[target_columns].values, dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        forecast_output = model(input_tensor)
    return forecast_output.tolist()
