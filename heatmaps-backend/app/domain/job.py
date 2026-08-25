from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from rq.job import Job as RQJob
from rq.job import JobStatus as RQJobStatus


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VideoOutput(BaseModel):
    type: str
    label: str
    video_url: str


def build_label(heatmap_request: dict[str, Any]) -> str:
    """Human label for a heatmap request, e.g. for `VideoOutput.label`."""
    heatmap_type = heatmap_request["type"]

    if heatmap_type == "directional":
        return f"Directional — {heatmap_request['direction']}"

    if heatmap_type == "speed":
        min_speed = heatmap_request.get("min_speed")
        max_speed = heatmap_request.get("max_speed")
        if min_speed is not None and max_speed is not None:
            return f"Speed {min_speed}–{max_speed} km/h"
        if min_speed is not None:
            return f"Speed ≥{min_speed} km/h"
        if max_speed is not None:
            return f"Speed ≤{max_speed} km/h"
        return "Speed (any)"

    if heatmap_type == "cluster":
        return f"Cluster size {heatmap_request['group_size']}"

    if heatmap_type == "tripwire":
        return f"Tripwire — {heatmap_request['bucket']}"

    if heatmap_type == "roi":
        return f"ROI — {heatmap_request['bucket']}"

    raise ValueError(f"Unknown heatmap type: {heatmap_type!r}")


_RQ_QUEUED_STATUSES = {
    RQJobStatus.CREATED,
    RQJobStatus.QUEUED,
    RQJobStatus.DEFERRED,
    RQJobStatus.SCHEDULED,
}
_RQ_FAILED_STATUSES = {RQJobStatus.FAILED, RQJobStatus.STOPPED, RQJobStatus.CANCELED}


class JobState(BaseModel):
    status: JobStatus
    progress: int | None = None
    output: VideoOutput | None = None
    error: str | None = None

    @staticmethod
    def from_rq_job(job: RQJob) -> JobState:
        rq_status = job.get_status(refresh=True)

        if rq_status in _RQ_QUEUED_STATUSES:
            return JobState(status=JobStatus.QUEUED)

        if rq_status == RQJobStatus.STARTED:
            return JobState(
                status=JobStatus.PROCESSING,
                progress=int(job.meta.get("progress", 0)),
            )

        if rq_status == RQJobStatus.FINISHED:
            output = job.meta.get("output")
            return JobState(
                status=JobStatus.COMPLETED,
                progress=100,
                output=VideoOutput(**output) if output else None,
            )

        if rq_status in _RQ_FAILED_STATUSES:
            return JobState(
                status=JobStatus.FAILED,
                error=job.meta.get("error") or "Job processing failed unexpectedly.",
            )

        raise ValueError(f"Unhandled RQ job status: {rq_status!r}")
