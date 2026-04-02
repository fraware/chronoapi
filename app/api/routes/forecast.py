from __future__ import annotations

import logging
import time

from fastapi import APIRouter, HTTPException, Request

from app.api.deps import ForecastModelDep
from app.observability.metrics import forecast_latency_seconds, forecast_requests_total
from app.schemas.requests import ForecastRequest
from app.services.forecast import run_forecast

logger = logging.getLogger("forecasting_service")

router = APIRouter()


@router.post("/forecast", summary="Generate Forecast")
async def forecast(
    request: Request,
    req: ForecastRequest,
    model: ForecastModelDep,
):
    start_time = time.time()
    forecast_requests_total.labels(method="POST", endpoint="/forecast").inc()
    rid = getattr(request.state, "request_id", None)
    logger.info(
        "REST forecast endpoint called",
        extra={
            "extra_payload": {
                "context_length": req.context_length,
                "forecast_length": req.forecast_length,
                "request_id": req.request_id or rid,
            }
        },
    )
    payload = req.model_dump()
    try:
        result = run_forecast(payload, model)
    except ValueError as e:
        logger.info(
            "Forecast validation failed",
            extra={"extra_payload": {"error": str(e), "request_id": req.request_id}},
        )
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception:
        logger.exception(
            "Error during REST forecasting",
            extra={"extra_payload": {"request_id": req.request_id}},
        )
        raise HTTPException(status_code=500, detail="Forecasting failed.") from None

    elapsed = time.time() - start_time
    forecast_latency_seconds.labels(method="POST", endpoint="/forecast").observe(elapsed)
    logger.info(
        "Forecast generated successfully",
        extra={"extra_payload": {"request_id": req.request_id or rid}},
    )
    return {"forecast": result, "request_id": req.request_id}
