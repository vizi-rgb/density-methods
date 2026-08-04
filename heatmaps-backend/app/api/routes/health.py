from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from rq import Worker

from app.api.schemas import ErrorDetail, ErrorResponse, HealthResponse
from app.worker import queue as worker_queue

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    try:
        redis = worker_queue.get_redis()
        redis.ping()
    except Exception as exc:
        logger.warning("health check failed: redis unreachable: %s", exc)
        body = ErrorResponse(
            error=ErrorDetail(code="redis_unreachable", message=str(exc))
        )
        return JSONResponse(status_code=503, content=body.model_dump())

    queue = worker_queue.get_queue()
    workers_online = len(Worker.all(connection=redis, queue=queue))
    queued_jobs = queue.count
    # Not a failure — the API itself is healthy — but a queue backing up
    # with nobody consuming it is exactly what makes uploads look "stuck at
    # 0%" with no other symptom, so surface it instead of staying silent.
    if workers_online == 0 and queued_jobs > 0:
        logger.warning(
            "%d job(s) queued but no worker is running — uploads will stall", queued_jobs
        )

    return JSONResponse(
        status_code=200,
        content=HealthResponse(
            status="ok", workers_online=workers_online, queued_jobs=queued_jobs
        ).model_dump(),
    )
