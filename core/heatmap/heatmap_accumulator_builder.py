from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.heatmap.heatmap_accumulator import HeatmapAccumulator


@dataclass
class HeatmapAccumulatorBuilder:
    height: int | None = None
    width: int | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10

    def with_height(self, height: int) -> "HeatmapAccumulatorBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "HeatmapAccumulatorBuilder":
        self.width = width
        return self

    def with_frames(self, frames_count: int) -> "HeatmapAccumulatorBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "HeatmapAccumulatorBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(
        self, momentum_buffer_size: int
    ) -> "HeatmapAccumulatorBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "HeatmapAccumulatorBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(self, half_life_time_in_seconds: int) -> "HeatmapAccumulatorBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def build(self) -> "HeatmapAccumulator":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.frames_count is None:
            raise ValueError("fps must be set before build().")

        from core.heatmap.heatmap_accumulator import HeatmapAccumulator

        return HeatmapAccumulator(self)
