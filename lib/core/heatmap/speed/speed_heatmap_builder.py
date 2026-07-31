from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.heatmap.speed.speed_filter import SpeedFilter

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
    speed_filters: list[SpeedFilter] = field(default_factory=list)

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

    def with_speed_filter(self, speed_filter: SpeedFilter) -> "SpeedHeatmapBuilder":
        self.speed_filters.append(speed_filter)
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
