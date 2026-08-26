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


Point = tuple[float, float]


class CalibrationRequest(BaseModel):
    camera_points: list[Point] = Field(min_length=4, max_length=4)
    real_world_points: list[Point] = Field(min_length=4, max_length=4)


class HealthResponse(BaseModel):
    status: str
    workers_online: int
    queued_jobs: int

class DefaultsResponse(BaseModel):
    fixed_max: float
    alpha: float
    sigma: float


Direction = Literal["all", "static", "up", "down", "left", "right"]


class HeatmapVisualizerRequest(BaseModel):
    fixed_max: float = Field(ge=0)
    alpha: float = Field(ge=0, le=1)
    sigma: float = Field(ge=0)


class DirectionalHeatmapRequest(BaseModel):
    type: Literal["directional"]
    direction: Direction
    half_life_time: int | None = Field(default=None, gt=0)
    visualizer: HeatmapVisualizerRequest | None = None


class SpeedHeatmapRequest(BaseModel):
    type: Literal["speed"]
    min_speed: float | None = Field(default=None, ge=0)
    max_speed: float | None = Field(default=None, ge=0)
    half_life_time: int | None = Field(default=None, gt=0)
    visualizer: HeatmapVisualizerRequest | None = None

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
    half_life_time: int | None = Field(default=None, gt=0)
    visualizer: HeatmapVisualizerRequest | None = None


RegionBucket = Literal["inside", "outside", "inside->outside", "outside->inside"]


class TripwireHeatmapRequest(BaseModel):
    type: Literal["tripwire"]
    p1: Point
    p2: Point
    inside_point: Point
    bucket: RegionBucket
    half_life_time: int | None = Field(default=None, gt=0)
    visualizer: HeatmapVisualizerRequest | None = None

    @model_validator(mode="after")
    def _check_distinct_points(self) -> "TripwireHeatmapRequest":
        if self.p1 == self.p2:
            raise ValueError("p1 and p2 must be distinct points")
        return self


class RoiHeatmapRequest(BaseModel):
    type: Literal["roi"]
    polygon: list[Point] = Field(min_length=3)
    bucket: RegionBucket
    half_life_time: int | None = Field(default=None, gt=0)
    visualizer: HeatmapVisualizerRequest | None = None


HeatmapRequest = Annotated[
    DirectionalHeatmapRequest
    | SpeedHeatmapRequest
    | ClusterHeatmapRequest
    | TripwireHeatmapRequest
    | RoiHeatmapRequest,
    Field(discriminator="type"),
]


Operator = Literal["AND", "OR", "AND_NOT"]


class HeatmapLayer(BaseModel):
    heatmap: HeatmapRequest
    operator: Operator | None = None
    invert: bool = False


class ComposedHeatmapRequest(BaseModel):
    type: Literal["composed"] = "composed"
    layers: list[HeatmapLayer] = Field(min_length=1)
    visualizer: HeatmapVisualizerRequest | None = None

    @model_validator(mode="after")
    def _check_operators(self) -> "ComposedHeatmapRequest":
        if self.layers[0].operator is not None:
            raise ValueError("the first layer must not specify an operator")
        for layer in self.layers[1:]:
            if layer.operator is None:
                raise ValueError(
                    "every layer after the first must specify an operator"
                )
        return self


HeatmapJobRequest = Annotated[
    DirectionalHeatmapRequest
    | SpeedHeatmapRequest
    | ClusterHeatmapRequest
    | TripwireHeatmapRequest
    | RoiHeatmapRequest
    | ComposedHeatmapRequest,
    Field(discriminator="type"),
]
