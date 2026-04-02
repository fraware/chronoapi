from __future__ import annotations

import inspect
import math
import tempfile
import warnings
from typing import Any

import pandas as pd
from torch.optim import AdamW
from torch.optim.lr_scheduler import OneCycleLR
from transformers import EarlyStoppingCallback, Trainer, TrainingArguments, set_seed
from tsfm_public import TimeSeriesPreprocessor, TrackingCallback, get_datasets
from tsfm_public.toolkit.get_model import get_model

from app.services.constants import column_specifiers, timestamp_column


def _training_args_kwargs(
    temp_dir: str,
    learning_rate: float,
    num_epochs: int,
    batch_size: int,
    seed: int,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "output_dir": temp_dir,
        "overwrite_output_dir": True,
        "learning_rate": learning_rate,
        "num_train_epochs": num_epochs,
        "do_eval": True,
        "per_device_train_batch_size": batch_size,
        "per_device_eval_batch_size": batch_size,
        "dataloader_num_workers": 4,
        "report_to": "none",
        "save_strategy": "epoch",
        "logging_strategy": "epoch",
        "save_total_limit": 1,
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "seed": seed,
    }
    params = inspect.signature(TrainingArguments.__init__).parameters
    if "eval_strategy" in params:
        base["eval_strategy"] = "epoch"
    else:
        base["evaluation_strategy"] = "epoch"
    return base


def run_finetune(request_data: dict[str, Any]) -> dict[str, Any]:
    warnings.filterwarnings("ignore")
    seed = 42
    set_seed(seed)

    n = len(request_data["data"])
    train_end = int(0.6 * n)
    valid_end = int(0.8 * n)
    split_config = {
        "train": [0, train_end],
        "valid": [train_end, valid_end],
        "test": [valid_end, n],
    }

    df = pd.DataFrame(request_data["data"])
    df[timestamp_column] = pd.to_datetime(df[timestamp_column])
    ctx = request_data.get("context_length", 512)
    pred = request_data.get("forecast_length", 96)

    tsp = TimeSeriesPreprocessor(
        **column_specifiers,
        context_length=ctx,
        prediction_length=pred,
        scaling=True,
        encode_categorical=False,
        scaler_type="standard",
    )
    dset_train, dset_val, dset_test = get_datasets(
        tsp,
        df,
        split_config,
        fewshot_fraction=request_data.get("fewshot_percent", 5.0) / 100,
        fewshot_location="first",
    )

    fine_tune_model = get_model(
        model_path="ibm-granite/granite-timeseries-ttm-r2",
        context_length=ctx,
        prediction_length=pred,
        loss=request_data.get("loss", "mse"),
        quantile=request_data.get("quantile", 0.5),
    )

    if request_data.get("freeze_backbone", True):
        for param in fine_tune_model.backbone.parameters():
            param.requires_grad = False

    learning_rate = request_data.get("learning_rate", 0.001)
    num_epochs = request_data.get("num_epochs", 50)
    batch_size = request_data.get("batch_size", 64)

    with tempfile.TemporaryDirectory() as temp_dir:
        ta_kwargs = _training_args_kwargs(temp_dir, learning_rate, num_epochs, batch_size, seed)
        training_args = TrainingArguments(**ta_kwargs)

        early_stopping_callback = EarlyStoppingCallback(
            early_stopping_patience=10, early_stopping_threshold=1e-5
        )
        tracking_callback = TrackingCallback()
        optimizer = AdamW(fine_tune_model.parameters(), lr=learning_rate)
        scheduler = OneCycleLR(
            optimizer,
            learning_rate,
            epochs=num_epochs,
            steps_per_epoch=math.ceil(len(dset_train) / batch_size),
        )

        trainer = Trainer(
            model=fine_tune_model,
            args=training_args,
            train_dataset=dset_train,
            eval_dataset=dset_val,
            callbacks=[early_stopping_callback, tracking_callback],
            optimizers=(optimizer, scheduler),
        )

        trainer.train()
        eval_result = trainer.evaluate(dset_test)

    return eval_result
