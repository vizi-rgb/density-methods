from __future__ import annotations

import math
import cv2
import numpy as np
from typing import TYPE_CHECKING
from core.adapter.predictions_adapter import Prediction, Point
from core.heatmap.momentum import MomentumTracker, TrackedPoint, TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.heatmap_accumulator_builder import HeatmapAccumulatorBuilder


class HeatmapAccumulator:
    def __init__(self, builder: "HeatmapAccumulatorBuilder"):
        self.height = builder.height
        self.width = builder.width
        self.frames_count = builder.frames_count
        if self.height is None or self.width is None or self.frames_count is None:
            raise ValueError("Builder fields must be set before use.")

        self.fps = builder.fps
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
        self.momentum_tracker = MomentumTracker(
            builder.momentum_buffer_size,
            builder.max_lost_frames,
        )

    def get_heatmap_from_streamed_prediction(self, prediction: Prediction):
        self._process_prediction(prediction)
        print(f"Returning heatmap [{self.frames_processed + 1}/{self.frames_count}]")
        self.frames_processed += 1
        return self.heatmap

    def get_heatmap_from_predictions(self, predictions: list[Prediction]):
        for prediction in predictions:
            self._process_prediction(prediction)
        return self.heatmap

    def _process_prediction(self, prediction: Prediction):
        for point in prediction.points:
            self._update_heatmap(point)

        updates = self.momentum_tracker.flush_lost_tracks_buffers(set(point.track_id for point in prediction.points))
        for update in updates:
            self._execute_track_update(update, None)

    def _update_heatmap(self, current_pos: Point):
        clamped_current_pos = self._clamp_point_to_heatmap_point(current_pos)
        update = self.momentum_tracker.update(
            current_pos.track_id,
            clamped_current_pos,
        )

        if not update.was_tracked:
            self._update_point_heatmap(clamped_current_pos)
            return

        if update.first_point is None or update.last_point is None:
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        if update.buffer_full:
            self._execute_track_update(update, clamped_current_pos)
        else:
            self._update_directional_heatmap(
                update.last_point, clamped_current_pos, "all"
            )

    def _execute_track_update(self, update: TrackUpdate, clamped_current_pos: TrackedPoint | None):
        if update.first_point is None or update.last_point is None:
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        direction_label = self._get_direction_label(
            update.first_point,
            clamped_current_pos if clamped_current_pos is not None else update.last_point,
        )
        for first_point, second_point in update.flushed_segments:
            self._update_directional_heatmap(
                first_point, second_point, direction_label
            )

        if clamped_current_pos is not None:
            self._update_directional_heatmap(
                update.last_point, clamped_current_pos, direction_label
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

    def _clamp_point_to_heatmap_point(self, point: Point) -> TrackedPoint:
        return TrackedPoint(
            x=min(max(math.floor(point.x), 0), self.width - 1),
            y=min(max(math.floor(point.y), 0), self.height - 1),
        )

    def _get_direction_label(self, p1: TrackedPoint, p2: TrackedPoint):
        dx = p2.x - p1.x
        dy = p2.y - p1.y

        if math.hypot(dx, dy) < 5:
            return "static"

        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0:
            angle += 360

        if 45 <= angle < 135:
            return "up"
        elif 135 <= angle < 225:
            return "left"
        elif 225 <= angle < 315:
            return "down"
        else:
            return "right"
