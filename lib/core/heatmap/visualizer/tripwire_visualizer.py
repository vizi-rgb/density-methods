from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


class TripwireVisualizer:
    def __init__(
        self,
        p1: tuple[int, int],
        p2: tuple[int, int],
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> None:
        self.p1 = p1
        self.p2 = p2
        self.color = color
        self.thickness = thickness

    def draw(
        self,
        image: np.ndarray,
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        overlay = image.copy()
        cv2.line(overlay, self.p1, self.p2, self.color, self.thickness)

        if save_path is not None:
            output_path = Path(save_path)
            if not cv2.imwrite(str(output_path), overlay):
                raise RuntimeError(f"Could not save overlay image to path: {output_path}")

        return overlay
