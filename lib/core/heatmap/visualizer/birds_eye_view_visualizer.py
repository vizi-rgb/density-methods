from pathlib import Path

import cv2
import numpy as np

from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer


class BirdsEyeViewVisualizer:
    def __init__(
        self,
        fixed_max: float,
        alpha: float = 0.5,
        sigma: float = 1.0,
        colormap: int = cv2.COLORMAP_JET,
    ) -> None:
        self._visualizer = HeatmapVisualizer(fixed_max, alpha, sigma, colormap)

    def draw(
        self,
        heatmap: np.ndarray,
        image: str | Path | np.ndarray | None = None,
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        if image is None:
            image = np.zeros((*heatmap.shape, 3), dtype=np.uint8)

        return self._visualizer.draw(heatmap, image, save_path)
