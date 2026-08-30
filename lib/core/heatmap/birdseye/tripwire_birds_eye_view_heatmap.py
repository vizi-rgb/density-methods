from __future__ import annotations

from typing import List, TYPE_CHECKING

from core.heatmap.birdseye.roi_birds_eye_view_heatmap import RoiBirdsEyeViewHeatmap
from core.heatmap.birdseye.roi_birds_eye_view_heatmap_builder import RoiBirdsEyeViewHeatmapBuilder
from core.heatmap.tripwire.tripwire_heatmap import _compute_tripwire_polygon
from core.momentum.domain import TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.birdseye.tripwire_birds_eye_view_heatmap_builder import (
        TripwireBirdsEyeViewHeatmapBuilder,
    )


class TripwireBirdsEyeViewHeatmap:
    def __init__(self, builder: "TripwireBirdsEyeViewHeatmapBuilder"):
        polygon_points = _compute_tripwire_polygon(
            p1=builder._p1,
            p2=builder._p2,
            inside_point=builder._inside_point,
            width=builder.width,
            height=builder.height,
        )

        roi_builder = (
            RoiBirdsEyeViewHeatmapBuilder()
            .with_width(builder.width)
            .with_height(builder.height)
            .with_camera_to_world_mapper(builder.camera_to_world_mapper)
            .with_granularity(builder.granularity)
            .with_frames(builder.frames_count)
            .with_fps(builder.fps)
            .with_momentum_buffer_size(builder.momentum_buffer_size)
            .with_max_lost_frames(builder.max_lost_frames)
            .with_polygon(polygon_points)
        )
        if builder.half_life_time is not None:
            roi_builder.with_half_life_time(builder.half_life_time)

        self._roi_heatmap: RoiBirdsEyeViewHeatmap = roi_builder.build()
        self.width = self._roi_heatmap.width
        self.height = self._roi_heatmap.height

    def handle(self, updates: List[TrackUpdate]) -> None:
        self._roi_heatmap.handle(updates)

    def handle_single_update(self, update: TrackUpdate) -> None:
        self._roi_heatmap.handle_single_update(update)

    def execute_track_update_batch(self, updates: List[TrackUpdate]) -> None:
        self._roi_heatmap.execute_track_update_batch(updates)

    def get_heatmap(self):
        return self._roi_heatmap.get_heatmap()

    def apply_decay(self) -> None:
        self._roi_heatmap.apply_decay()

    def get_polygon(self):
        return [(int(x), int(y)) for x, y in self._roi_heatmap.get_polygon().reshape(-1, 2)]

    def get_tripwire(self):
        polygon = self.get_polygon()
        return polygon[0], polygon[-1]
