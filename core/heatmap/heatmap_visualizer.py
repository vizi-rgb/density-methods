from pathlib import Path
from typing import Any

import cv2
import numpy as np

# /* ************************************************************************* */
# /**
# * @brief Computes kernel size for Gaussian smoothing if the image
# * @param sigma Kernel standard deviation
# * @returns kernel size
# */
# static inline int getGaussianKernelSize(float sigma) {
#                                                      // Compute an appropriate kernel size according to the specified sigma
# int ksize = (int)cvCeil(2.0f*(1.0f + (sigma - 0.8f) / (0.3f)));
# ksize |= 1; // kernel should be odd
# return ksize;
# }


class HeatmapVisualizer:
    def __init__(
        self,
        fixed_max: float,
        alpha: float = 0.5,
        sigma: float = 1.0,
        colormap: int = cv2.COLORMAP_JET,
    ) -> None:
        if fixed_max <= 0:
            raise ValueError(f"fixed_max must be > 0, got: {fixed_max}")
        if not 0 <= alpha <= 1:
            raise ValueError(f"alpha must be in range [0, 1], got: {alpha}")
        self.fixed_max = float(fixed_max)
        self.alpha = alpha
        self.sigma = sigma
        self.colormap = colormap
        self.peak_gaussian_kernel_value = None

    def draw(
        self,
        heatmap: np.ndarray,
        image: str | Path | np.ndarray,
        save_path: str | Path | None = None,
    ) -> np.ndarray:
        source_image = self._load_image(image)
        validated_heatmap = self._validate_heatmap(heatmap)

        if source_image.shape[:2] != validated_heatmap.shape:
            raise ValueError(
                f"Heatmap shape {validated_heatmap.shape} does not match image shape {source_image.shape[:2]}."
            )

        blurred_heatmap = cv2.GaussianBlur(validated_heatmap, (0, 0), sigmaX=self.sigma)
        calibrated_max = self.fixed_max * self._get_peak_gaussian_kernel_value(blurred_heatmap)
        normalized_heatmap = np.clip((blurred_heatmap / calibrated_max) * 255.0, 0, 255).astype(np.uint8)
        colored_heatmap = cv2.applyColorMap(normalized_heatmap, self.colormap)

        overlay = cv2.addWeighted(source_image, 1 - self.alpha, colored_heatmap, self.alpha, 0.0)

        if save_path is not None:
            output_path = Path(save_path)
            if not cv2.imwrite(str(output_path), overlay):
                raise RuntimeError(f"Could not save overlay image to path: {output_path}")

        return overlay

    def _load_image(self, image: str | Path | np.ndarray) -> np.ndarray:
        if isinstance(image, (str, Path)):
            image_path = Path(image)
            loaded_image = cv2.imread(str(image_path))
            if loaded_image is None:
                raise FileNotFoundError(f"Could not load image from path: {image_path}")
            return self._normalize_image_array(loaded_image)
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

    def _validate_heatmap(self, heatmap: np.ndarray) -> np.ndarray:
        if not isinstance(heatmap, np.ndarray):
            raise TypeError(f"heatmap must be np.ndarray, got: {type(heatmap)}")
        if heatmap.ndim != 2:
            raise ValueError(f"heatmap must be 2D (H, W), got shape: {heatmap.shape}")
        if not np.issubdtype(heatmap.dtype, np.number):
            raise ValueError(f"heatmap must have numeric dtype, got: {heatmap.dtype}")
        if not np.isfinite(heatmap).all():
            raise ValueError("heatmap contains NaN or Inf values")
        return heatmap.astype(np.float32, copy=False)

    def _get_peak_gaussian_kernel_value(self, validated_heatmap: np.ndarray):
        if self.peak_gaussian_kernel_value is None:
            dummy_heatmap = np.zeros_like(validated_heatmap)
            yy, xx = validated_heatmap.shape
            cy, cx = yy // 2, xx // 2
            dummy_heatmap[cy, cx] = 1.0
            self.peak_gaussian_kernel_value = cv2.GaussianBlur(dummy_heatmap, (0, 0), sigmaX=self.sigma)[cy, cx]

        return self.peak_gaussian_kernel_value



