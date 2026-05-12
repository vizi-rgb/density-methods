import math

import numpy as np

from core.adapter.predictions_adapter import Prediction

class HeatmapFactory:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.heatmap = None

    def init_heatmap(self):
        if self.heatmap is None:
            self.heatmap = np.zeros((self.height, self.width), dtype=np.float32)

    def get_heatmap_from_streamed_prediction(self, prediction: Prediction):
        self.init_heatmap()
        for x, y in prediction.points:
            x = min(max(math.floor(x), 0), self.width - 1)
            y = min(max(math.floor(y), 0), self.height - 1)
            self.heatmap[y, x] += 1
        print(f"Returning heatmap {prediction.image_path}")
        return self.heatmap

    def get_heatmap_from_predictions(self, predictions: list[Prediction]):
        self.init_heatmap()
        for prediction in predictions:
            for x, y in prediction.points:
                x = min(max(math.floor(x), 0), self.width - 1)
                y = min(max(math.floor(y), 0), self.height - 1)
                self.heatmap[y, x] += 1
        return self.heatmap
