from pathlib import Path
from uuid import uuid4

from app.config import Settings

MEDIA_MOUNT_PATH = "/media"


def new_job_id() -> str:
    return str(uuid4())


def ensure_base_dirs(settings: Settings) -> None:
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)


def upload_path(settings: Settings, job_id: str, suffix: str) -> Path:
    """Path for the uploaded source video. `suffix` includes the leading dot."""
    job_dir = settings.uploads_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir / f"source{suffix}"


def job_output_dir(settings: Settings, job_id: str, heatmap_type: str) -> Path:
    """Directory holding one heatmap type's HLS output — mounted verbatim at
    /media/{job_id}/{heatmap_type}/ so this layout must match the URL layout."""
    output_dir = settings.jobs_dir / job_id / heatmap_type
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def manifest_url(base_url: str, job_id: str, heatmap_type: str) -> str:
    return f"{base_url.rstrip('/')}{MEDIA_MOUNT_PATH}/{job_id}/{heatmap_type}/stream.m3u8"
