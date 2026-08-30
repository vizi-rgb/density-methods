from __future__ import annotations

from typing import List, TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap import BirdsEyeViewHeatmap
from core.heatmap.roi.roi_heatmap import RoiHeatmap
from core.heatmap.roi.roi_heatmap_builder import RoiHeatmapBuilder
from core.momentum.domain import TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.birdseye.roi_birds_eye_view_heatmap_builder import (
        RoiBirdsEyeViewHeatmapBuilder,
    )


class RoiBirdsEyeViewHeatmap(BirdsEyeViewHeatmap):
    def __init__(self, builder: "RoiBirdsEyeViewHeatmapBuilder"):
        super().__init__(builder)

        projected_polygon = self._project_polygon(builder.polygon_points)
        inner_builder = (
            RoiHeatmapBuilder()
            .with_width(self.width)
            .with_height(self.height)
            .with_frames(builder.frames_count)
            .with_fps(builder.fps)
            .with_momentum_buffer_size(builder.momentum_buffer_size)
            .with_max_lost_frames(builder.max_lost_frames)
            .with_polygon(projected_polygon)
        )
        if builder.half_life_time is not None:
            inner_builder.with_half_life_time(builder.half_life_time)

        self._inner: RoiHeatmap = inner_builder.build()

    def handle(self, updates: List[TrackUpdate]):
        self._inner.handle([self._project_update(update) for update in updates])

    def handle_single_update(self, update: TrackUpdate):
        self._inner.handle_single_update(self._project_update(update))

    def execute_track_update_batch(self, updates: List[TrackUpdate]):
        self._inner.execute_track_update_batch([self._project_update(update) for update in updates])

    def get_heatmap(self):
        return self._inner.get_heatmap()

    def get_polygon(self):
        return self._inner.get_polygon()

    def apply_decay(self):
        self._inner.apply_decay()
