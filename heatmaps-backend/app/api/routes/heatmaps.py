from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob

from app.api.errors import ApiError
from app.api.schemas import HeatmapJobResponse, HeatmapRequest
from app.config import get_settings
from app.domain.job import JobState, JobStatus
from app.services.storage import new_id, video_source_path
from app.worker import queue as worker_queue

router = APIRouter()

_POLL_INTERVAL_SECONDS = 1.0


@router.post(
    "/api/videos/{video_id}/heatmaps",
    response_model=HeatmapJobResponse,
    status_code=202,
)
async def create_heatmap_job(
    video_id: str, request: Request, heatmap_request: HeatmapRequest
) -> HeatmapJobResponse:
    settings = get_settings()
    source_path = video_source_path(settings, video_id)
    if source_path is None:
        raise ApiError(404, "video_not_found", f"No video found with id {video_id!r}.")

    job_id = new_id()
    worker_queue.get_queue().enqueue(
        "app.worker.tasks.process_video",
        job_id,
        str(source_path),
        heatmap_request.model_dump(),
        str(request.base_url),
        job_id=job_id,
        meta={"progress": 0},
        result_ttl=settings.job_ttl_seconds,
        failure_ttl=settings.job_ttl_seconds,
    )

    return HeatmapJobResponse(job_id=job_id)


def _fetch_job(job_id: str) -> RQJob:
    try:
        return RQJob.fetch(job_id, connection=worker_queue.get_redis())
    except NoSuchJobError as exc:
        raise ApiError(404, "job_not_found", f"No job found with id {job_id!r}.") from exc


@router.get(
    "/api/heatmaps/{job_id}", response_model=JobState, response_model_exclude_none=True
)
async def get_heatmap_job(job_id: str) -> JobState:
    return JobState.from_rq_job(_fetch_job(job_id))


@router.get("/api/heatmaps/{job_id}/stream")
async def stream_heatmap_job(job_id: str) -> StreamingResponse:
    _fetch_job(job_id)  # 404 fast if the job doesn't exist, before opening the stream
    return StreamingResponse(
        _sse_events(job_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse_events(job_id: str) -> AsyncIterator[str]:
    last_state: JobState | None = None
    while True:
        state = JobState.from_rq_job(_fetch_job(job_id))
        if state != last_state:
            yield _format_event(state)
            last_state = state
        if state.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            return
        await asyncio.sleep(_POLL_INTERVAL_SECONDS)


def _format_event(state: JobState) -> str:
    payload = state.model_dump(exclude_none=True, mode="json")
    return f"data: {json.dumps(payload)}\n\n"
