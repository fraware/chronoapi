"""
In-process fine-tune jobs for optional async mode (FINETUNE_ASYNC=true).

Production deployments should prefer a dedicated queue (Celery, RQ, Arq) for
long-running training; this module provides a minimal 202 Accepted flow without
external brokers.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from app.services.finetune import run_finetune

logger = logging.getLogger("forecasting_service")


@dataclass
class FinetuneJob:
    job_id: str
    status: str  # pending | running | completed | failed
    result: dict[str, Any] | None = None
    error: str | None = None


class FinetuneJobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, FinetuneJob] = {}
        self._lock = asyncio.Lock()

    async def submit(self, request_data: dict[str, Any]) -> str:
        job_id = str(uuid.uuid4())
        async with self._lock:
            self._jobs[job_id] = FinetuneJob(job_id=job_id, status="pending")
        asyncio.create_task(self._run(job_id, request_data))
        return job_id

    async def _run(self, job_id: str, request_data: dict[str, Any]) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "running"
        try:
            result = await asyncio.to_thread(run_finetune, request_data)
            async with self._lock:
                j = self._jobs.get(job_id)
                if j:
                    j.status = "completed"
                    j.result = result
        except Exception as e:
            logger.exception("Async finetune job failed", extra={"job_id": job_id})
            async with self._lock:
                j = self._jobs.get(job_id)
                if j:
                    j.status = "failed"
                    j.error = str(e)

    async def get(self, job_id: str) -> FinetuneJob | None:
        async with self._lock:
            j = self._jobs.get(job_id)
            if j is None:
                return None
            return FinetuneJob(
                job_id=j.job_id,
                status=j.status,
                result=j.result,
                error=j.error,
            )


registry = FinetuneJobRegistry()
