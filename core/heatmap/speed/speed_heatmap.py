from __future__ import annotations


import cv2
import numpy as np
from typing import TYPE_CHECKING

from core.heatmap.speed.speed_filter_chain import SpeedFilterChain
from core.momentum.momentum import TrackedPoint, TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.speed.speed_heatmap_builder import SpeedHeatmapBuilder

EPS = 0.01


class SpeedHeatmap:
    def __init__(self, builder: "SpeedHeatmapBuilder"):
        self.height = builder.height
        self.width = builder.width
        self.frames_count = builder.frames_count
        self.fps = builder.fps

        if (
            self.height is None
            or self.width is None
            or self.frames_count is None
            or self.fps is None
        ):
            raise ValueError("Builder fields must be set before use.")

        self.speed_filter_chain = SpeedFilterChain(builder.speed_filters)
        self.frames_processed = 0
        self.heatmap = {
            name: np.zeros((self.height, self.width), dtype=np.float32)
            for name in self.speed_filter_chain.filter_names()
        }
        self.intermediate_heatmap = np.zeros(
            (self.height, self.width), dtype=np.float32
        )

        if self.fps and builder.half_life_time:
            self.decay_factor = 0.5 ** (1 / (builder.half_life_time * self.fps))
        else:
            self.decay_factor = None

    def handle(self, updates: list[TrackUpdate]):
        for update in updates:
            self.handle_single_update(update)
        self.frames_processed += 1

    def handle_single_update(self, update: TrackUpdate):
        filters = self.speed_filter_chain.evaluate(update)
        if len(filters) == 0:
            return

        if not update.was_tracked and update.current_point is not None:
            return

        if (
            update.first_point is None
            or update.last_point is None
            or update.current_point is None
        ):
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        if update.processed_segments:
            for filter_name in filters:
                self.execute_track_update(update, filter_name)

    def get_heatmap(self):
        return self.heatmap

    def apply_decay(self):
        if self.decay_factor:
            self._apply_decay()

    def execute_track_update_batch(self, updates: list[TrackUpdate]):
        for update in updates:
            filters = self.speed_filter_chain.evaluate(update)
            for filter_name in filters:
                self.execute_track_update(update, filter_name)

    def execute_track_update(self, update: TrackUpdate, filter_name: str):
        if update.first_point is None or update.last_point is None:
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        for first_point, second_point in update.processed_segments:
            self._update_speed_heatmap(first_point, second_point, filter_name)

    def _update_point_heatmap(self, point: TrackedPoint, filter_name: str):
        self.heatmap[filter_name][point.y, point.x] += 1

    def _update_speed_heatmap(
        self,
        prev_pos: TrackedPoint,
        current_pos: TrackedPoint,
        filter_name: str,
    ):
        self._draw_line(self.heatmap[filter_name], prev_pos, current_pos)

    def _draw_line(self, heatmap: np.ndarray, p1: TrackedPoint, p2: TrackedPoint):
        cv2.line(self.intermediate_heatmap, p1, p2, 1, 1)
        heatmap += self.intermediate_heatmap
        cv2.line(self.intermediate_heatmap, p1, p2, 0, 1)

    def _apply_decay(self):
        for key in self.heatmap:
            self.heatmap[key] *= self.decay_factor
            self.heatmap[key][self.heatmap[key] < EPS] = 0.0
