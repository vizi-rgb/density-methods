"""RQ task entrypoint: ties the pipeline and HLS encoders together and keeps
the job's Redis-backed meta (progress/outputs/error) up to date so
GET /api/status/{job_id} and the SSE stream can reflect real state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

from rq import get_current_job

from app.config import Settings, get_settings
from app.domain.job import HEATMAP_TYPE_LABELS
from app.services import pipeline
from app.services.hls_encoder import HlsEncoder
from app.services.storage import job_output_dir, manifest_url

logger = logging.getLogger(__name__)


class _JobMeta(Protocol):
    meta: dict[str, Any]

    def save_meta(self) -> None: ...


def process_video(
    job_id: str, heatmap_types: list[str], video_path_str: str, base_url: str
) -> None:
    job = get_current_job()
    if job is None:
        raise RuntimeError("process_video must be run inside an RQ worker")
    run_job(job, job_id, heatmap_types, Path(video_path_str), base_url, get_settings())


def run_job(
    job: _JobMeta,
    job_id: str,
    heatmap_types: list[str],
    video_path: Path,
    base_url: str,
    settings: Settings,
) -> None:
    encoders: dict[str, HlsEncoder] = {}
    try:
        metadata = pipeline.read_metadata(video_path)

        for heatmap_type in heatmap_types:
            output_dir = job_output_dir(settings, job_id, heatmap_type)
            encoders[heatmap_type] = HlsEncoder(
                output_dir=output_dir,
                width=metadata.width,
                height=metadata.height,
                fps=metadata.fps,
                segment_seconds=settings.hls_segment_seconds,
            )

        frames_done = 0
        for overlays in pipeline.run(video_path, metadata, heatmap_types, settings):
            for heatmap_type, frame in overlays.items():
                encoders[heatmap_type].write_frame(frame)

            frames_done += 1
            if frames_done % settings.progress_update_every_n_frames == 0:
                _update_progress(job, frames_done, metadata.frames)

        for encoder in encoders.values():
            encoder.close()

        job.meta["progress"] = 100
        job.meta["outputs"] = [
            {
                "type": heatmap_type,
                "label": HEATMAP_TYPE_LABELS[heatmap_type],
                "manifest_url": manifest_url(base_url, job_id, heatmap_type),
            }
            for heatmap_type in heatmap_types
        ]
        job.save_meta()
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        for encoder in encoders.values():
            encoder.kill()
        job.meta["error"] = str(exc)
        job.save_meta()
        raise


def _update_progress(job: _JobMeta, frames_done: int, total_frames: int) -> None:
    # capped below 100 — only a `completed` job is ever reported as 100%.
    progress = min(99, int(frames_done / total_frames * 100))
    job.meta["progress"] = progress
    job.save_meta()
