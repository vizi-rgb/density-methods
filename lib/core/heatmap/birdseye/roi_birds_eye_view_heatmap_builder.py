from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder

if TYPE_CHECKING:
    from core.heatmap.birdseye.roi_birds_eye_view_heatmap import RoiBirdsEyeViewHeatmap


@dataclass
class RoiBirdsEyeViewHeatmapBuilder(BirdsEyeViewHeatmapBuilder):
    polygon_points: list[tuple[int, int]] | None = None

    def with_polygon(self, polygon_points: list[tuple[int, int]]) -> "RoiBirdsEyeViewHeatmapBuilder":
        self.polygon_points = polygon_points
        return self

    def build(self) -> "RoiBirdsEyeViewHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.camera_to_world_mapper is None:
            raise ValueError("camera_to_world_mapper must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self.polygon_points is None:
            raise ValueError("polygon must be set before build().")

        from core.heatmap.birdseye.roi_birds_eye_view_heatmap import RoiBirdsEyeViewHeatmap

        return RoiBirdsEyeViewHeatmap(self)
