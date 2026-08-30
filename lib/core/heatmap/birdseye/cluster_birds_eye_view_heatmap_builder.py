from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder

if TYPE_CHECKING:
    from core.heatmap.birdseye.cluster_birds_eye_view_heatmap import ClusterBirdsEyeViewHeatmap


@dataclass
class ClusterBirdsEyeViewHeatmapBuilder(BirdsEyeViewHeatmapBuilder):
    cluster_eps_meters: float = 1.0

    def with_cluster_eps_meters(self, cluster_eps_meters: float) -> "ClusterBirdsEyeViewHeatmapBuilder":
        self.cluster_eps_meters = cluster_eps_meters
        return self

    def build(self) -> "ClusterBirdsEyeViewHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.camera_to_world_mapper is None:
            raise ValueError("camera_to_world_mapper must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.fps is None:
            raise ValueError("fps must be set before build().")

        from core.heatmap.birdseye.cluster_birds_eye_view_heatmap import ClusterBirdsEyeViewHeatmap

        return ClusterBirdsEyeViewHeatmap(self)
