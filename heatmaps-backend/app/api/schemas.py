from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class VideoUploadResponse(BaseModel):
    video_id: str
    video_url: str


class HeatmapJobResponse(BaseModel):
    job_id: str


class HealthResponse(BaseModel):
    status: str
    workers_online: int
    queued_jobs: int


Direction = Literal["all", "static", "up", "down", "left", "right"]


class DirectionalHeatmapRequest(BaseModel):
    type: Literal["directional"]
    direction: Direction


class SpeedHeatmapRequest(BaseModel):
    type: Literal["speed"]
    min_speed: float | None = Field(default=None, ge=0)
    max_speed: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _check_bounds(self) -> "SpeedHeatmapRequest":
        if (
            self.min_speed is not None
            and self.max_speed is not None
            and self.min_speed > self.max_speed
        ):
            raise ValueError("min_speed must not be greater than max_speed")
        return self


class ClusterHeatmapRequest(BaseModel):
    type: Literal["cluster"]
    # DBSCAN's min_samples=2 (lib/core/heatmap/clusters/cluster_heatmap.py)
    # means a "cluster" of 1 person doesn't exist in the underlying data.
    group_size: int = Field(ge=2)


HeatmapRequest = Annotated[
    DirectionalHeatmapRequest | SpeedHeatmapRequest | ClusterHeatmapRequest,
    Field(discriminator="type"),
]
