from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from rq.exceptions import NoSuchJobError
from rq.job import Job as RQJob

from app.api.errors import ApiError
from app.domain.job import JobState, JobStatus
from app.worker import queue as worker_queue

router = APIRouter()

_POLL_INTERVAL_SECONDS = 1.0


def _fetch_job(job_id: str) -> RQJob:
    try:
        return RQJob.fetch(job_id, connection=worker_queue.get_redis())
    except NoSuchJobError as exc:
        raise ApiError(404, "job_not_found", f"No job found with id {job_id!r}.") from exc


@router.get("/api/status/{job_id}", response_model=JobState, response_model_exclude_none=True)
async def get_status(job_id: str) -> JobState:
    return JobState.from_rq_job(_fetch_job(job_id))


@router.get("/api/status/{job_id}/stream")
async def stream_status(job_id: str) -> StreamingResponse:
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
