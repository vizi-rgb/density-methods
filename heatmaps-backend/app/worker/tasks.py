"""RQ task entrypoint: ties the pipeline and the MP4 encoder together and
keeps the job's Redis-backed meta (progress/output/error) up to date so
GET /api/heatmaps/{job_id} and the SSE stream can reflect real state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from rq import get_current_job

from app.config import Settings, get_settings
from app.domain.job import build_label
from app.services import pipeline
from app.services.mp4_encoder import Mp4Encoder
from app.services.storage import job_output_path, job_output_url

logger = logging.getLogger(__name__)


class _JobMeta(Protocol):
    meta: dict[str, Any]

    def save_meta(self) -> None: ...


def process_video(
    job_id: str,
    video_path_str: str,
    heatmap_request: dict[str, Any],
    base_url: str,
) -> None:
    job = get_current_job()
    if job is None:
        raise RuntimeError("process_video must be run inside an RQ worker")
    run_job(job, job_id, Path(video_path_str), heatmap_request, base_url, get_settings())


def run_job(
    job: _JobMeta,
    job_id: str,
    video_path: Path,
    heatmap_request: dict[str, Any],
    base_url: str,
    settings: Settings,
) -> None:
    encoder: Mp4Encoder | None = None
    try:
        metadata = pipeline.read_metadata(video_path)
        encoder = Mp4Encoder(
            output_path=job_output_path(settings, job_id),
            width=metadata.width,
            height=metadata.height,
            fps=metadata.fps,
        )

        frames_done = 0
        for frame in pipeline.run(video_path, metadata, heatmap_request, settings):
            encoder.write_frame(frame)

            frames_done += 1
            if frames_done % settings.progress_update_every_n_frames == 0:
                _update_progress(job, frames_done, metadata.frames)

        if frames_done == 0:
            raise RuntimeError(
                "No frames were processed — video may be corrupt or unreadable"
            )

        encoder.close()

        job.meta["progress"] = 100
        job.meta["output"] = {
            "type": heatmap_request["type"],
            "label": build_label(heatmap_request),
            "video_url": job_output_url(base_url, job_id),
        }
        job.save_meta()
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        if encoder is not None:
            encoder.kill()
        job.meta["error"] = str(exc)
        job.save_meta()
        raise


def _update_progress(job: _JobMeta, frames_done: int, total_frames: int) -> None:
    # capped below 100 — only a `completed` job is ever reported as 100%.
    progress = min(99, int(frames_done / total_frames * 100))
    job.meta["progress"] = progress
    job.save_meta()
