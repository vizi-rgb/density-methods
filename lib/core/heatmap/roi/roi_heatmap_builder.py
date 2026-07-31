from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from core.heatmap.roi.roi_heatmap import RoiHeatmap


@dataclass
class RoiHeatmapBuilder:
    height: int | None = None
    width: int | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10
    polygon: np.ndarray | None = None

    def with_height(self, height: int) -> "RoiHeatmapBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "RoiHeatmapBuilder":
        self.width = width
        return self

    def with_frames(self, frames_count: int) -> "RoiHeatmapBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "RoiHeatmapBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(
        self, momentum_buffer_size: int
    ) -> "RoiHeatmapBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "RoiHeatmapBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(
        self, half_life_time_in_seconds: int
    ) -> "RoiHeatmapBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def with_polygon(self, polygon_points: list[tuple[int, int]]) -> "RoiHeatmapBuilder":
        self.polygon = np.array(polygon_points, dtype=np.float32).reshape((-1, 1, 2))
        return self

    def build(self) -> "RoiHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.polygon is None:
            raise ValueError("polygon must be set before build().")

        from core.heatmap.roi.roi_heatmap import RoiHeatmap

        return RoiHeatmap(self)
