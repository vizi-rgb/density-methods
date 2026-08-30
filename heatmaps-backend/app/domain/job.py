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


def _speed_phrase(heatmap_request: dict[str, Any]) -> str:
    min_speed = heatmap_request.get("min_speed")
    max_speed = heatmap_request.get("max_speed")
    if min_speed is not None and max_speed is not None:
        return f"Speed {min_speed}–{max_speed} km/h"
    if min_speed is not None:
        return f"Speed ≥{min_speed} km/h"
    if max_speed is not None:
        return f"Speed ≤{max_speed} km/h"
    return "Speed (any)"


def _view_prefix(view: str | None) -> str:
    return "World — " if view == "world" else ""


def build_label(heatmap_request: dict[str, Any]) -> str:
    """Human label for a heatmap request, e.g. for `VideoOutput.label`."""
    heatmap_type = heatmap_request["type"]
    prefix = _view_prefix(heatmap_request.get("view"))

    if heatmap_type == "directional":
        return f"{prefix}Directional — {heatmap_request['direction']}"

    if heatmap_type == "speed":
        return f"{prefix}{_speed_phrase(heatmap_request)}"

    if heatmap_type == "cluster":
        return f"{prefix}Cluster size {heatmap_request['group_size']}"

    if heatmap_type == "tripwire":
        return f"{prefix}Tripwire — {heatmap_request['bucket']}"

    if heatmap_type == "roi":
        return f"{prefix}ROI — {heatmap_request['bucket']}"

    raise ValueError(f"Unknown heatmap type: {heatmap_type!r}")


_DIRECTION_PHRASES = {
    "up": "Moving Up",
    "down": "Moving Down",
    "left": "Moving Left",
    "right": "Moving Right",
    "static": "Stationary",
    "all": "Any Direction",
}

_REGION_BUCKET_PHRASES = {
    "inside": "Inside",
    "outside": "Outside",
    "inside->outside": "Exiting",
    "outside->inside": "Entering",
}

_OPERATOR_WORDS = {
    "AND": "AND",
    "OR": "OR",
    "AND_NOT": "BUT NOT",
}


def _layer_condition_phrase(heatmap_request: dict[str, Any]) -> str:
    """Short, human-readable phrase for one layer's primitive condition,
    used to build the composed-job natural-language readout."""
    heatmap_type = heatmap_request["type"]

    if heatmap_type == "directional":
        return _DIRECTION_PHRASES[heatmap_request["direction"]]

    if heatmap_type == "speed":
        return _speed_phrase(heatmap_request)

    if heatmap_type == "cluster":
        return f"Cluster Size {heatmap_request['group_size']}"

    if heatmap_type == "tripwire":
        return f"{_REGION_BUCKET_PHRASES[heatmap_request['bucket']]} Tripwire"

    if heatmap_type == "roi":
        return f"{_REGION_BUCKET_PHRASES[heatmap_request['bucket']]} ROI"

    raise ValueError(f"Unknown heatmap type: {heatmap_type!r}")


def build_composed_label(layers: list[dict[str, Any]], view: str | None = None) -> str:
    """Natural-language readout for a composed (layered) heatmap job, e.g.
    "Show tracks matching (Speed ≥7 km/h) AND (Moving Up) BUT NOT (Inside ROI)".
    `view` is job-level (see ComposedHeatmapRequest.view), not per-layer.
    """
    parts: list[str] = []
    for i, layer in enumerate(layers):
        phrase = _layer_condition_phrase(layer["heatmap"])
        if layer.get("invert"):
            phrase = f"NOT {phrase}"
        phrase = f"({phrase})"
        if i == 0:
            parts.append(phrase)
        else:
            parts.append(f"{_OPERATOR_WORDS[layer['operator']]} {phrase}")
    return _view_prefix(view) + "Show tracks matching " + " ".join(parts)


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
