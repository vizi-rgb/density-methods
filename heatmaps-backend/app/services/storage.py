import json
from pathlib import Path
from uuid import uuid4

from app.config import Settings

MEDIA_MOUNT_PATH = "/media"


def new_id() -> str:
    return str(uuid4())


def ensure_base_dirs(settings: Settings) -> None:
    settings.videos_dir.mkdir(parents=True, exist_ok=True)
    settings.jobs_dir.mkdir(parents=True, exist_ok=True)


def staging_video_path(settings: Settings, video_id: str, suffix: str) -> Path:
    """Temporary write target while streaming an upload to disk, before it's
    moved into its final location. `suffix` includes the leading dot."""
    staging_dir = settings.videos_dir / "_staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    return staging_dir / f"{video_id}{suffix}"


def video_dir(settings: Settings, video_id: str) -> Path:
    return settings.videos_dir / video_id


def finalize_video_path(settings: Settings, video_id: str, suffix: str) -> Path:
    """Final path for an uploaded source video. `suffix` includes the leading dot."""
    target_dir = video_dir(settings, video_id)
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"source{suffix}"


def video_source_path(settings: Settings, video_id: str) -> Path | None:
    """Locates the previously uploaded source video for `video_id`, if any —
    used to 404 unknown videos and to hand the pipeline a real file path."""
    matches = sorted(video_dir(settings, video_id).glob("source.*"))
    return matches[0] if matches else None


def video_url(base_url: str, video_id: str, source_path: Path) -> str:
    return f"{base_url.rstrip('/')}{MEDIA_MOUNT_PATH}/videos/{video_id}/{source_path.name}"


def calibration_path(settings: Settings, video_id: str) -> Path:
    return video_dir(settings, video_id) / "calibration.json"


def save_calibration_matrix(
    settings: Settings, video_id: str, matrix: list[list[float]]
) -> None:
    calibration_path(settings, video_id).write_text(json.dumps(matrix))


def load_calibration_matrix(
    settings: Settings, video_id: str
) -> list[list[float]] | None:
    path = calibration_path(settings, video_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def job_output_path(settings: Settings, job_id: str) -> Path:
    """Single MP4 output file for one heatmap job."""
    output_dir = settings.jobs_dir / job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "output.mp4"


def job_output_url(base_url: str, job_id: str) -> str:
    return f"{base_url.rstrip('/')}{MEDIA_MOUNT_PATH}/jobs/{job_id}/output.mp4"
