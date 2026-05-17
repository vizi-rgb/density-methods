import math

import cv2
import numpy as np

from core.adapter.predictions_adapter import Prediction


class HeatmapFactory:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.heatmap = {
            "all": np.zeros((self.height, self.width), dtype=np.float32),
            "up": np.zeros((self.height, self.width), dtype=np.float32),
            "down": np.zeros((self.height, self.width), dtype=np.float32),
            "left": np.zeros((self.height, self.width), dtype=np.float32),
            "right": np.zeros((self.height, self.width), dtype=np.float32),
        }
        self.id_tracker = dict()

    def get_heatmap_from_streamed_prediction(self, prediction: Prediction):
        self._update_heatmap(prediction)
        print(f"Returning heatmap {prediction.image_path}")
        return self.heatmap

    def get_heatmap_from_predictions(self, predictions: list[Prediction]):
        for prediction in predictions:
            self._update_heatmap(prediction)
        return self.heatmap

    def _update_heatmap(self, prediction: Prediction):
        for point in prediction.points:
            x = min(max(math.floor(point.x), 0), self.width - 1)
            y = min(max(math.floor(point.y), 0), self.height - 1)
            if point.track_id != 0 and point.track_id in self.id_tracker:
                prev_pos = self.id_tracker[point.track_id]
                direction_label = self._get_direction_label(prev_pos, (x, y))
                if direction_label != "static":
                    cv2.line(self.heatmap["all"], prev_pos, (x, y), 1, 1)
                    cv2.line(self.heatmap[direction_label], prev_pos, (x, y), 1, 1)
                else:
                    self.heatmap["all"][y, x] += 1
            else:
                self.heatmap["all"][y, x] += 1

            if point.track_id != 0:
                self.id_tracker[point.track_id] = (x, y)

    def _get_direction_label(self, p1, p2):
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

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
