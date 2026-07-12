from __future__ import annotations

import cv2
import numpy as np
from typing import TYPE_CHECKING
from core.momentum.momentum import TrackedPoint, TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.directional.directional_heatmap_builder import (
        DirectionalHeatmapBuilder,
    )

EPS = 0.01


class DirectionalHeatmap:
    def __init__(self, builder: "DirectionalHeatmapBuilder"):
        self.height = builder.height
        self.width = builder.width
        self.frames_count = builder.frames_count
        self.fps = builder.fps

        if (
            self.height is None
            or self.width is None
            or self.frames_count is None
        ):
            raise ValueError("Builder fields must be set before use.")

        self.frames_processed = 0
        self.heatmap = {
            "all": np.zeros((self.height, self.width), dtype=np.float32),
            "static": np.zeros((self.height, self.width), dtype=np.float32),
            "up": np.zeros((self.height, self.width), dtype=np.float32),
            "down": np.zeros((self.height, self.width), dtype=np.float32),
            "left": np.zeros((self.height, self.width), dtype=np.float32),
            "right": np.zeros((self.height, self.width), dtype=np.float32),
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
        if not update.was_tracked and update.current_point is not None:
            self._update_point_heatmap(update.current_point)
            return

        if (
            update.first_point is None
            or update.last_point is None
            or update.current_point is None
        ):
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        if update.processed_segments:
            self.execute_track_update(update)

        self._update_directional_heatmap(update.last_point, update.current_point, "all")

    def get_heatmap(self):
        return self.heatmap

    def apply_decay(self):
        if self.decay_factor:
            self._apply_decay()

    def execute_track_update_batch(self, updates: list[TrackUpdate]):
        for update in updates:
            self.execute_track_update(update)

    def execute_track_update(self, update: TrackUpdate):
        if (
            update.first_point is None
            or update.last_point is None
            or update.direction_label is None
        ):
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        for first_point, second_point in update.processed_segments:
            self._update_directional_heatmap(
                first_point, second_point, update.direction_label
            )

    def _update_directional_heatmap(
        self,
        prev_pos: TrackedPoint,
        current_pos: TrackedPoint,
        direction_label: str,
    ):
        self._draw_line(self.heatmap[direction_label], prev_pos, current_pos)

    def _update_point_heatmap(
        self,
        point: TrackedPoint,
        direction_label: str = "all",
    ):
        self.heatmap[direction_label][point.y, point.x] += 1

    def _draw_line(self, heatmap: np.ndarray, p1: TrackedPoint, p2: TrackedPoint):
        cv2.line(self.intermediate_heatmap, p1, p2, 1, 1)
        heatmap += self.intermediate_heatmap
        cv2.line(self.intermediate_heatmap, p1, p2, 0, 1)

    def _apply_decay(self):
        for key in self.heatmap:
            self.heatmap[key] *= self.decay_factor
            self.heatmap[key][self.heatmap[key] < EPS] = 0.0
