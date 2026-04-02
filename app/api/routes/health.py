from __future__ import annotations

import logging

from fastapi import APIRouter, Request

from app.config import settings
from app.observability.metrics import forecast_requests_total

logger = logging.getLogger("forecasting_service")

router = APIRouter()


@router.get("/health", summary="Health Check (legacy)")
async def health_legacy():
    forecast_requests_total.labels(method="GET", endpoint="/health").inc()
    return {"status": "ok"}


@router.get("/health/live", summary="Liveness")
async def health_live():
    forecast_requests_total.labels(method="GET", endpoint="/health/live").inc()
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness")
async def health_ready(request: Request):
    forecast_requests_total.labels(method="GET", endpoint="/health/ready").inc()
    model = getattr(request.app.state, "forecast_model", None)
    if model is None:
        return {"ready": False, "reason": "model_not_attached"}
    body: dict = {
        "ready": True,
        "production_model": not settings.skip_model_load,
    }
    if settings.kafka_enabled:
        body["kafka_enabled"] = True
        body["note"] = "Kafka connectivity is not probed; ensure broker is reachable."
    return body
