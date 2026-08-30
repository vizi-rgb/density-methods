from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.heatmap.clusters.cluster_heatmap import ClusterHeatmap


@dataclass
class ClusterHeatmapBuilder:
    height: int | None = None
    width: int | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10
    cluster_eps: float = 80.0

    def with_height(self, height: int) -> "ClusterHeatmapBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "ClusterHeatmapBuilder":
        self.width = width
        return self

    def with_frames(self, frames_count: int) -> "ClusterHeatmapBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "ClusterHeatmapBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(
        self, momentum_buffer_size: int
    ) -> "ClusterHeatmapBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "ClusterHeatmapBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(
        self, half_life_time_in_seconds: int
    ) -> "ClusterHeatmapBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def with_cluster_eps(self, cluster_eps: float) -> "ClusterHeatmapBuilder":
        self.cluster_eps = cluster_eps
        return self

    def build(self) -> "ClusterHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.fps is None:
            raise ValueError("fps must be set before build().")

        from core.heatmap.clusters.cluster_heatmap import ClusterHeatmap

        return ClusterHeatmap(self)
