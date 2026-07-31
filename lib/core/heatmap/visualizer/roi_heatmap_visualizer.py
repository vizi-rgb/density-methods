from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer


class RoiHeatmapVisualizer:
    def __init__(
        self,
        visualizer: HeatmapVisualizer,
        polygon: list[tuple[int, int]] | np.ndarray,
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> None:
        self.visualizer = visualizer
        self.polygon = (
            np.array(polygon, dtype=np.int32).reshape((-1, 1, 2))
            if not isinstance(polygon, np.ndarray)
            else polygon.reshape((-1, 1, 2)).astype(np.int32)
        )
        self.color = color
        self.thickness = thickness

    def draw(
        self,
        heatmap: np.ndarray,
        image: str | Path | np.ndarray,
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        overlay = self.visualizer.draw(heatmap, image)
        cv2.polylines(overlay, [self.polygon], isClosed=True, color=self.color, thickness=self.thickness)

        if save_path is not None:
            output_path = Path(save_path)
            if not cv2.imwrite(str(output_path), overlay):
                raise RuntimeError(f"Could not save overlay image to path: {output_path}")

        return overlay
