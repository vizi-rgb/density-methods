from pathlib import Path

import cv2
import numpy as np

from core.momentum.domain import TrackUpdate

_PALETTE = [
    (255, 56, 56),
    (56, 255, 56),
    (56, 56, 255),
    (255, 255, 56),
    (255, 56, 255),
    (56, 255, 255),
    (255, 165, 0),
    (128, 0, 128),
]


class TrackVisualizer:
    def draw(
        self,
        image: str | Path | np.ndarray,
        track_updates: dict[int, TrackUpdate],
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        frame = self._load_image(image)

        for track_id, update in track_updates.items():
            if update.current_point is None:
                continue
            color = _PALETTE[track_id % len(_PALETTE)]
            self._draw_segments(frame, update, color)
            self._draw_label(frame, track_id, update, color)

        if save_path is not None:
            output_path = Path(save_path)
            if not cv2.imwrite(str(output_path), frame):
                raise RuntimeError(f"Could not save frame to path: {output_path}")

        return frame

    def _draw_segments(self, frame: np.ndarray, update: TrackUpdate, color: tuple) -> None:
        for start, end in update.processed_segments:
            cv2.line(frame, (int(start.x), int(start.y)), (int(end.x), int(end.y)), color, 2)
        cx, cy = int(update.current_point.x), int(update.current_point.y)
        cv2.circle(frame, (cx, cy), 5, color, -1)

    def _draw_label(self, frame: np.ndarray, track_id: int, update: TrackUpdate, color: tuple) -> None:
        cx, cy = int(update.current_point.x), int(update.current_point.y)

        fp = update.first_point
        lp = update.last_point
        cp = update.current_point

        lines = [
            f"id={track_id}",
            f"tracked={update.was_tracked}",
            f"dir={update.direction_label}",
            f"spd_px={update.speed_px_per_s:.1f}" if update.speed_px_per_s is not None else "spd_px=None",
            f"spd_m={update.speed_km_per_h:.2f}" if update.speed_km_per_h is not None else "spd_m=None",
            f"first=({fp.x},{fp.y})" if fp else "first=None",
            f"last=({lp.x},{lp.y})" if lp else "last=None",
            f"cur=({cp.x},{cp.y})",
        ]

        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.45
        thickness = 1
        pad = 4
        line_h = 14

        text_w = max(cv2.getTextSize(l, font, scale, thickness)[0][0] for l in lines)
        box_h = line_h * len(lines) + pad * 2

        bx = min(cx + 8, frame.shape[1] - text_w - pad * 2 - 1)
        by = max(cy - box_h // 2, 0)

        cv2.rectangle(frame, (bx, by), (bx + text_w + pad * 2, by + box_h), (0, 0, 0), -1)
        cv2.rectangle(frame, (bx, by), (bx + text_w + pad * 2, by + box_h), color, 1)

        for i, line in enumerate(lines):
            ty = by + pad + line_h * i + line_h - 2
            cv2.putText(frame, line, (bx + pad, ty), font, scale, color, thickness, cv2.LINE_AA)

    def _load_image(self, image: str | Path | np.ndarray) -> np.ndarray:
        if isinstance(image, (str, Path)):
            image_path = Path(image)
            loaded = cv2.imread(str(image_path))
            if loaded is None:
                raise FileNotFoundError(f"Could not load image from path: {image_path}")
            return self._normalize_image_array(loaded)
        if isinstance(image, np.ndarray):
            return self._normalize_image_array(image)
        raise TypeError(f"Unsupported image type: {type(image)}")

    def _normalize_image_array(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        elif image.ndim != 3 or image.shape[2] != 3:
            raise ValueError(f"Expected image shape (H, W) or (H, W, 3/4), got: {image.shape}")
        if not np.issubdtype(image.dtype, np.number):
            raise ValueError(f"Expected numeric image array dtype, got: {image.dtype}")
        if image.dtype != np.uint8:
            image = np.clip(image, 0, 255).astype(np.uint8)
        return image.copy()
