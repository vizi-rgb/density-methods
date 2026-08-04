from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent

HEATMAP_TYPES: tuple[str, ...] = ("directional", "speed", "cluster")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"

    data_dir: Path = BACKEND_ROOT / "data"
    max_upload_mb: int = 500

    cors_origins: list[str] = ["http://localhost:5173"]

    hls_segment_seconds: int = 4

    # job state kept in Redis (RQ job meta); how long a finished job's
    # state/output stays queryable via GET /api/status/{job_id}.
    job_ttl_seconds: int = 24 * 60 * 60

    # matches the values lib/main.py uses for its own reference pipeline run.
    momentum_buffer_size: int = 15
    default_max_lost_frames: int = 10
    heatmap_fixed_max: float = 3.0
    heatmap_alpha: float = 0.5
    heatmap_sigma: float = 25.0

    progress_update_every_n_frames: int = 10

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
