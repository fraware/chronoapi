from fastapi import APIRouter

from app.api.routes import finetune, forecast, health
from app.api.routes import metrics as metrics_route

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(forecast.router, tags=["forecast"])
api_router.include_router(finetune.router, tags=["finetune"])
api_router.include_router(metrics_route.router, tags=["metrics"])
