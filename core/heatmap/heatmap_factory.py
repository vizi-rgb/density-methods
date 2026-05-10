import math

import numpy as np

class HeatmapFactory:
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.heatmap = None

    def init_heatmap(self):
        if self.heatmap is None:
            self.heatmap = np.zeros((self.height, self.width), dtype=np.float32)

    def get_heatmap_from_prediction_points(self, prediction_points: list[list[tuple[float, float]]]):
        self.init_heatmap()
        for points in prediction_points:
            for x, y in points:
                x = min(max(math.floor(x), 0), self.width - 1)
                y = min(max(math.floor(y), 0), self.height - 1)
                self.heatmap[y, x] += 1
        return self.heatmap
