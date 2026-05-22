import math
import cv2
import numpy as np
from typing import NamedTuple
from core.adapter.predictions_adapter import Prediction, Point

class HeatmapPoint(NamedTuple):
    x: int
    y: int

class HeatmapFactory:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.heatmap = {
            "all": np.zeros((self.height, self.width), dtype=np.float32),
            "static": np.zeros((self.height, self.width), dtype=np.float32),
            "up": np.zeros((self.height, self.width), dtype=np.float32),
            "down": np.zeros((self.height, self.width), dtype=np.float32),
            "left": np.zeros((self.height, self.width), dtype=np.float32),
            "right": np.zeros((self.height, self.width), dtype=np.float32),
        }
        self.id_tracker = dict()

    def get_heatmap_from_streamed_prediction(self, prediction: Prediction):
        self._process_prediction(prediction)
        print(f"Returning heatmap")
        return self.heatmap

    def get_heatmap_from_predictions(self, predictions: list[Prediction]):
        for prediction in predictions:
            self._process_prediction(prediction)
        return self.heatmap

    def _process_prediction(self, prediction: Prediction):
        for point in prediction.points:
            self._update_heatmap(point)

    def _update_heatmap(self, current_pos: Point):
        clamped_current_pos = HeatmapPoint(
            x = min(max(math.floor(current_pos.x), 0), self.width - 1),
            y = min(max(math.floor(current_pos.y), 0), self.height - 1),
        )
        if self._is_prediction_point_tracked(current_pos):
            prev_pos = self.id_tracker[current_pos.track_id]
            direction_label = self._get_direction_label(prev_pos, clamped_current_pos)
            self._update_directional_heatmap(prev_pos, clamped_current_pos, direction_label)
        else:
            self._update_point_heatmap(clamped_current_pos)

        if current_pos.track_id != 0:
            self.id_tracker[current_pos.track_id] = clamped_current_pos

    def _update_directional_heatmap(self, prev_pos: HeatmapPoint, current_pos: HeatmapPoint, direction_label: str):
        if direction_label != "static":
            cv2.line(self.heatmap["all"], prev_pos, current_pos, 1, 1)
            cv2.line(self.heatmap[direction_label], prev_pos, current_pos, 1, 1)
        else:
            self._update_point_heatmap(prev_pos, "static")
            self._update_point_heatmap(prev_pos, "all")

    def _update_point_heatmap(self, point: HeatmapPoint, direction_label: str = "all"):
        self.heatmap[direction_label][point.y, point.x] += 1

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

    def _is_prediction_point_tracked(self, point: Point):
        return point.track_id != 0 and point.track_id in self.id_tracker
