import math
from collections import deque
import cv2
import numpy as np
from typing import NamedTuple
from core.adapter.predictions_adapter import Prediction, Point
from core.util import DataSourceInfo


class HeatmapPoint(NamedTuple):
    x: int
    y: int

class HeatmapFactory:
    def __init__(self, height, width, frames_count, fps, momentum_buffer_size: int | None = None):
        self.height = height
        self.width = width
        self.frames_count = frames_count
        self.fps = fps
        self.frames_processed = 0
        self.heatmap = {
            "all": np.zeros((self.height, self.width), dtype=np.float32),
            "static": np.zeros((self.height, self.width), dtype=np.float32),
            "up": np.zeros((self.height, self.width), dtype=np.float32),
            "down": np.zeros((self.height, self.width), dtype=np.float32),
            "left": np.zeros((self.height, self.width), dtype=np.float32),
            "right": np.zeros((self.height, self.width), dtype=np.float32),
        }
        self.intermediate_heatmap = np.zeros((self.height, self.width), dtype=np.float32)
        self.momentum_buffer_size = 1 if not momentum_buffer_size else momentum_buffer_size
        self.id_tracker = dict()

    @classmethod
    def from_metadata(cls, metadata: DataSourceInfo):
        return cls(metadata.height, metadata.width, metadata.frames, metadata.fps, metadata.fps // 3 if metadata.fps else None)


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

    def _update_heatmap(self, current_pos: Point):
        clamped_current_pos = self._clamp_point_to_heatmap_point(current_pos)

        if self._is_id_tracked(current_pos.track_id):
            prev_pos_queue = self.id_tracker[current_pos.track_id]
            if len(prev_pos_queue) == self.momentum_buffer_size:
                direction_label = self._get_direction_label(prev_pos_queue[0], clamped_current_pos)
                last_point = prev_pos_queue[-1]
                self._flush_momentum_buffer(prev_pos_queue, direction_label)
                self._update_directional_heatmap(last_point, clamped_current_pos, direction_label)
            else:
                self._update_directional_heatmap(prev_pos_queue[-1], clamped_current_pos, "all")
        else:
            self._update_point_heatmap(clamped_current_pos)

        self._update_track_if_needed(current_pos)

    def _update_directional_heatmap(self, prev_pos: HeatmapPoint, current_pos: HeatmapPoint, direction_label: str):
        self._draw_line(self.heatmap[direction_label], prev_pos, current_pos)

    def _update_point_heatmap(self, point: HeatmapPoint, direction_label: str = "all"):
        self.heatmap[direction_label][point.y, point.x] += 1

    def _draw_line(self, heatmap: np.ndarray, p1: HeatmapPoint, p2: HeatmapPoint):
        cv2.line(self.intermediate_heatmap, p1, p2, 1, 1)
        heatmap += self.intermediate_heatmap
        cv2.line(self.intermediate_heatmap, p1, p2, 0, 1)

    def _update_track_if_needed(self, current_pos: Point):
        if current_pos.track_id == 0:
            return

        if not self._is_id_tracked(current_pos.track_id):
            self.id_tracker[current_pos.track_id] = deque(maxlen=self.momentum_buffer_size)

        history = self.id_tracker[current_pos.track_id]
        history.append(self._clamp_point_to_heatmap_point(current_pos))

    def _flush_momentum_buffer(self, queue: deque, direction_label: str):
        first_point = queue.popleft()
        while queue:
            second_point = queue.popleft()
            self._update_directional_heatmap(first_point, second_point, direction_label)
            first_point = second_point

    def _clamp_point_to_heatmap_point(self, point: Point) -> HeatmapPoint:
        return HeatmapPoint(
            x = min(max(math.floor(point.x), 0), self.width - 1),
            y = min(max(math.floor(point.y), 0), self.height - 1),
        )

    def _get_direction_label(self, p1: HeatmapPoint, p2: HeatmapPoint):
        dx = p2.x - p1.x
        dy = p2.y - p1.y

        if math.hypot(dx, dy) < 3:
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

    def _is_id_tracked(self, track_id: int):
        return track_id != 0 and track_id in self.id_tracker
