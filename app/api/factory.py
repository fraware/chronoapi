from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.middleware import ApiKeyMiddleware, RequestContextMiddleware
from app.api.routes import api_router
from app.config import settings
from app.model import load_inference_model
from app.observability.logging_setup import configure_logging

if TYPE_CHECKING:
    from torch.nn import Module

logger = logging.getLogger("forecasting_service")


def _maybe_instrument_otel(app: FastAPI) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return
    FastAPIInstrumentor.instrument_app(app)


def create_app(
    forecast_model: Module | None = None,
    lifespan_override: Any = None,
) -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def default_lifespan(app: FastAPI) -> AsyncIterator[None]:
        m = forecast_model if forecast_model is not None else load_inference_model()
        app.state.forecast_model = m
        task: asyncio.Task | None = None
        if settings.kafka_enabled:
            from app.services.kafka import run_kafka_consumer

            task = asyncio.create_task(run_kafka_consumer(m))
            logger.info("Kafka consumer task started")
        else:
            logger.info("Kafka disabled (KAFKA_ENABLED=false)")
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    lifespan = lifespan_override if lifespan_override is not None else default_lifespan

    app = FastAPI(
        title="TTM Forecasting Microservice API",
        description=(
            "This API provides real-time forecasting using IBM Research's TTM model. "
            "Endpoints cover health, forecasting, fine-tuning, and metrics. "
            "See Swagger at /docs and ReDoc at /redoc."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return await http_exception_handler(request, exc)
        if isinstance(exc, RequestValidationError):
            return await request_validation_exception_handler(request, exc)
        logger.exception(
            "Unhandled error",
            extra={
                "extra_payload": {
                    "url": str(request.url.path),
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ApiKeyMiddleware)
    app.include_router(api_router)
    _maybe_instrument_otel(app)
    return app
