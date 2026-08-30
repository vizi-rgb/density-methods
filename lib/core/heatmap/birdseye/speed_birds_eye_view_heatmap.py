from __future__ import annotations

from typing import List, TYPE_CHECKING

from core.heatmap.birdseye.birds_eye_view_heatmap import BirdsEyeViewHeatmap
from core.heatmap.speed.speed_heatmap import SpeedHeatmap
from core.heatmap.speed.speed_heatmap_builder import SpeedHeatmapBuilder
from core.momentum.domain import TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.birdseye.speed_birds_eye_view_heatmap_builder import (
        SpeedBirdsEyeViewHeatmapBuilder,
    )


class SpeedBirdsEyeViewHeatmap(BirdsEyeViewHeatmap):
    def __init__(self, builder: "SpeedBirdsEyeViewHeatmapBuilder"):
        super().__init__(builder)

        inner_builder = (
            SpeedHeatmapBuilder()
            .with_width(self.width)
            .with_height(self.height)
            .with_frames(builder.frames_count)
            .with_fps(builder.fps)
            .with_momentum_buffer_size(builder.momentum_buffer_size)
            .with_max_lost_frames(builder.max_lost_frames)
        )
        if builder.half_life_time is not None:
            inner_builder.with_half_life_time(builder.half_life_time)
        for speed_filter in builder.speed_filters:
            inner_builder.with_speed_filter(speed_filter)

        self._inner: SpeedHeatmap = inner_builder.build()

    def handle(self, updates: List[TrackUpdate]):
        self._inner.handle([self._project_update(update) for update in updates])

    def handle_single_update(self, update: TrackUpdate):
        self._inner.handle_single_update(self._project_update(update))

    def execute_track_update_batch(self, updates: List[TrackUpdate]):
        self._inner.execute_track_update_batch([self._project_update(update) for update in updates])

    def get_heatmap(self):
        return self._inner.get_heatmap()

    def apply_decay(self):
        self._inner.apply_decay()
