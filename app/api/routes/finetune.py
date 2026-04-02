from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas.requests import FineTuneRequest
from app.services.finetune import run_finetune
from app.services.jobs import registry

logger = logging.getLogger("forecasting_service")

router = APIRouter()


@router.post("/finetune", summary="Fine-Tune Model")
async def finetune(request: Request, req: FineTuneRequest):
    rid = getattr(request.state, "request_id", None)
    logger.info(
        "Finetuning endpoint called",
        extra={"extra_payload": {"request_id": req.request_id or rid}},
    )
    payload = req.model_dump()

    if settings.finetune_async:
        job_id = await registry.submit(payload)
        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "status": "accepted",
                "request_id": req.request_id,
                "detail": "Poll GET /finetune/jobs/{job_id} for status.",
            },
        )

    try:
        result = run_finetune(payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception:
        logger.exception(
            "Error during finetuning",
            extra={"extra_payload": {"request_id": req.request_id}},
        )
        raise HTTPException(status_code=500, detail="Fine-tuning failed.") from None

    logger.info(
        "Fine-tuning completed",
        extra={"extra_payload": {"request_id": req.request_id or rid}},
    )
    return {"evaluation": result, "request_id": req.request_id}


@router.get("/finetune/jobs/{job_id}", summary="Fine-tune job status")
async def finetune_job_status(job_id: str):
    job = await registry.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id")
    body: dict = {"job_id": job.job_id, "status": job.status}
    if job.result is not None:
        body["evaluation"] = job.result
    if job.error:
        body["error"] = job.error
    return body
