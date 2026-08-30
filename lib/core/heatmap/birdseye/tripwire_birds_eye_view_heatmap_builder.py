from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder

if TYPE_CHECKING:
    from core.heatmap.birdseye.tripwire_birds_eye_view_heatmap import (
        TripwireBirdsEyeViewHeatmap,
    )


@dataclass
class TripwireBirdsEyeViewHeatmapBuilder(BirdsEyeViewHeatmapBuilder):
    _p1: tuple[int, int] | None = None
    _p2: tuple[int, int] | None = None
    _inside_point: tuple[int, int] | None = None

    def with_tripwire(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int],
        inside_point: tuple[int, int],
    ) -> "TripwireBirdsEyeViewHeatmapBuilder":
        self._p1 = p1
        self._p2 = p2
        self._inside_point = inside_point
        return self

    def build(self) -> "TripwireBirdsEyeViewHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.camera_to_world_mapper is None:
            raise ValueError("camera_to_world_mapper must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self._p1 is None or self._p2 is None or self._inside_point is None:
            raise ValueError("tripwire (p1, p2, inside_point) must be set before build().")

        from core.heatmap.birdseye.tripwire_birds_eye_view_heatmap import (
            TripwireBirdsEyeViewHeatmap,
        )

        return TripwireBirdsEyeViewHeatmap(self)
