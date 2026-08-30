from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder
from core.heatmap.speed.speed_filter import SpeedFilter

if TYPE_CHECKING:
    from core.heatmap.birdseye.speed_birds_eye_view_heatmap import SpeedBirdsEyeViewHeatmap


@dataclass
class SpeedBirdsEyeViewHeatmapBuilder(BirdsEyeViewHeatmapBuilder):
    speed_filters: list[SpeedFilter] = field(default_factory=list)

    def with_speed_filter(self, speed_filter: SpeedFilter) -> "SpeedBirdsEyeViewHeatmapBuilder":
        self.speed_filters.append(speed_filter)
        return self

    def build(self) -> "SpeedBirdsEyeViewHeatmap":
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

        from core.heatmap.birdseye.speed_birds_eye_view_heatmap import SpeedBirdsEyeViewHeatmap

        return SpeedBirdsEyeViewHeatmap(self)
