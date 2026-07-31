from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer


class TripwireHeatmapVisualizer:
    def __init__(
        self,
        visualizer: HeatmapVisualizer,
        p1: tuple[int, int],
        p2: tuple[int, int],
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> None:
        self.visualizer = visualizer
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.thickness = thickness

    def draw(
        self,
        heatmap: np.ndarray,
        image: str | Path | np.ndarray,
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        overlay = self.visualizer.draw(heatmap, image)
        cv2.line(overlay, self.p1, self.p2, self.color, self.thickness)

        if save_path is not None:
            output_path = Path(save_path)
            if not cv2.imwrite(str(output_path), overlay):
                raise RuntimeError(f"Could not save overlay image to path: {output_path}")

        return overlay
