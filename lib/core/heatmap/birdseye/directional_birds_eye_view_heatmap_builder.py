from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder

if TYPE_CHECKING:
    from core.heatmap.birdseye.directional_birds_eye_view_heatmap import (
        DirectionalBirdsEyeViewHeatmap,
    )


@dataclass
class DirectionalBirdsEyeViewHeatmapBuilder(BirdsEyeViewHeatmapBuilder):
    def build(self) -> "DirectionalBirdsEyeViewHeatmap":
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

        from core.heatmap.birdseye.directional_birds_eye_view_heatmap import (
            DirectionalBirdsEyeViewHeatmap,
        )

        return DirectionalBirdsEyeViewHeatmap(self)
