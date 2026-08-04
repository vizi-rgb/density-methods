from __future__ import annotations

from enum import StrEnum

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
    manifest_url: str


HEATMAP_TYPE_LABELS: dict[str, str] = {
    "directional": "Directional flow",
    "speed": "Speed",
    "cluster": "Cluster",
}

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
    outputs: list[VideoOutput] | None = None
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
            outputs = [VideoOutput(**o) for o in job.meta.get("outputs", [])]
            return JobState(
                status=JobStatus.COMPLETED, progress=100, outputs=outputs
            )

        if rq_status in _RQ_FAILED_STATUSES:
            return JobState(
                status=JobStatus.FAILED,
                error=job.meta.get("error") or "Job processing failed unexpectedly.",
            )

        raise ValueError(f"Unhandled RQ job status: {rq_status!r}")
