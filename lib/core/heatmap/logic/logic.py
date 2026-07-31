import numpy as np


class HeatmapLogic:
    def __init__(self, heatmap: np.ndarray):
        self.initial_heatmap = heatmap
        self.heatmap = heatmap.copy()

    def negate(self) -> "HeatmapLogic":
        self.heatmap = np.where(self.heatmap != 0, 0, 1).astype(self.heatmap.dtype)
        return self

    def and_(self, other: "HeatmapLogic | np.ndarray") -> "HeatmapLogic":
        if isinstance(other, np.ndarray):
            other = self._wrap(other)
        mask = (self.heatmap == 0) | (other.heatmap == 0)
        self.heatmap = np.where(mask, 0, np.maximum(self.heatmap, other.heatmap))
        return self

    def or_(self, other: "HeatmapLogic | np.ndarray") -> "HeatmapLogic":
        if isinstance(other, np.ndarray):
            other = self._wrap(other)
        self.heatmap = np.maximum(self.heatmap, other.heatmap)
        return self

    def result(self) -> np.ndarray:
        return self.heatmap

    def _wrap(self, other: np.ndarray):
        return HeatmapLogic(other)
