from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.momentum.camera_to_world_mapper import CameraToWorldMapper

if TYPE_CHECKING:
    from core.heatmap.birdseye.birds_eye_view_heatmap import BirdsEyeViewHeatmap


@dataclass
class BirdsEyeViewHeatmapBuilder:
    height: int | None = None
    width: int | None = None
    granularity: float | None = 0.01
    camera_to_world_mapper: CameraToWorldMapper | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10

    def with_height(self, height: int) -> "BirdsEyeViewHeatmapBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "BirdsEyeViewHeatmapBuilder":
        self.width = width
        return self

    def with_granularity(self, granularity: float) -> "BirdsEyeViewHeatmapBuilder":
        self.granularity = granularity
        return self

    def with_camera_to_world_mapper(
        self, camera_to_world_mapper: CameraToWorldMapper
    ) -> "BirdsEyeViewHeatmapBuilder":
        self.camera_to_world_mapper = camera_to_world_mapper
        return self

    def with_frames(self, frames_count: int) -> "BirdsEyeViewHeatmapBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "BirdsEyeViewHeatmapBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(
        self, momentum_buffer_size: int
    ) -> "BirdsEyeViewHeatmapBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "BirdsEyeViewHeatmapBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(
        self, half_life_time_in_seconds: int
    ) -> "BirdsEyeViewHeatmapBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def build(self) -> "BirdsEyeViewHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.camera_to_world_mapper is None:
            raise ValueError("camera_to_world_mapper must be set before build().")

        from core.heatmap.birdseye.birds_eye_view_heatmap import BirdsEyeViewHeatmap

        return BirdsEyeViewHeatmap(self)
