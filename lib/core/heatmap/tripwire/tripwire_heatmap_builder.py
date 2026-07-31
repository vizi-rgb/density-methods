from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.heatmap.tripwire.tripwire_heatmap import TripwireHeatmap


@dataclass
class TripwireHeatmapBuilder:
    height: int | None = None
    width: int | None = None
    frames_count: int | None = None
    fps: int | None = None
    half_life_time: int | None = None
    momentum_buffer_size: int = 1
    max_lost_frames: int = 10
    _p1: tuple[int, int] | None = None
    _p2: tuple[int, int] | None = None
    _inside_point: tuple[int, int] | None = None

    def with_height(self, height: int) -> "TripwireHeatmapBuilder":
        self.height = height
        return self

    def with_width(self, width: int) -> "TripwireHeatmapBuilder":
        self.width = width
        return self

    def with_frames(self, frames_count: int) -> "TripwireHeatmapBuilder":
        self.frames_count = frames_count
        return self

    def with_fps(self, fps: int) -> "TripwireHeatmapBuilder":
        self.fps = fps
        return self

    def with_momentum_buffer_size(self, momentum_buffer_size: int) -> "TripwireHeatmapBuilder":
        self.momentum_buffer_size = momentum_buffer_size
        return self

    def with_max_lost_frames(self, max_lost_frames: int) -> "TripwireHeatmapBuilder":
        self.max_lost_frames = max_lost_frames
        return self

    def with_half_life_time(self, half_life_time_in_seconds: int) -> "TripwireHeatmapBuilder":
        self.half_life_time = half_life_time_in_seconds
        return self

    def with_tripwire(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int],
        inside_point: tuple[int, int],
    ) -> "TripwireHeatmapBuilder":
        self._p1 = p1
        self._p2 = p2
        self._inside_point = inside_point
        return self

    def build(self) -> "TripwireHeatmap":
        if self.height is None:
            raise ValueError("height must be set before build().")
        if self.width is None:
            raise ValueError("width must be set before build().")
        if self.frames_count is None:
            raise ValueError("frames_count must be set before build().")
        if self._p1 is None or self._p2 is None or self._inside_point is None:
            raise ValueError("tripwire (p1, p2, inside_point) must be set before build().")

        from core.heatmap.tripwire.tripwire_heatmap import TripwireHeatmap

        return TripwireHeatmap(self)
