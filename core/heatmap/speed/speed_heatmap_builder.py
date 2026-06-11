from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.heatmap.speed.speed_heatmap import SpeedHeatmap


@dataclass
class SpeedHeatmapBuilder:
    height: int | None = None
    width: int | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10
    speed_min: float = 0.0
    speed_max: float = float("inf")

    def with_height(self, height: int) -> "SpeedHeatmapBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "SpeedHeatmapBuilder":
        self.width = width
        return self

    def with_frames(self, frames_count: int) -> "SpeedHeatmapBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "SpeedHeatmapBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(
        self, momentum_buffer_size: int
    ) -> "SpeedHeatmapBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "SpeedHeatmapBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(
        self, half_life_time_in_seconds: int
    ) -> "SpeedHeatmapBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def with_speed_min(self, speed_min: float) -> "SpeedHeatmapBuilder":
        self.speed_min = speed_min
        return self

    def with_speed_max(self, speed_max: float) -> "SpeedHeatmapBuilder":
        self.speed_max = speed_max
        return self

    def build(self) -> "SpeedHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.fps is None:
            raise ValueError("fps must be set before build().")

        from core.heatmap.speed.speed_heatmap import SpeedHeatmap

        return SpeedHeatmap(self)
