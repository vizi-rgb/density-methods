import os
from typing import Any

import numpy as np
import scipy.io


def load_mall_gt_counts(ground_truth_path) -> dict[int, int]:
    mall_gt_counts: dict[int, int] = {}
    if os.path.exists(ground_truth_path):
        try:
            mat = scipy.io.loadmat(ground_truth_path)
            counts = mat["count"].flatten()
            for i, c in enumerate(counts):
                mall_gt_counts[i] = int(c)
            print(f"Mall GT loaded: {len(mall_gt_counts)} count values")
        except Exception as e:
            print(f"Mall GT load error: {e}")
        finally:
            return mall_gt_counts
    else:
        print(f"Mall GT not found {ground_truth_path}")
        return mall_gt_counts


def compute_count_metrics(
    results_count: np.ndarray, gt_count: dict[int, int]
) -> dict[str, float] | None:
    frame_indices = [i for i in range(len(results_count)) if i in gt_count]

    if not frame_indices:
        print("No overlapping frames between predictions and GT.")
        return None

    results_arr = results_count[frame_indices]
    gt_arr = np.array([gt_count[i] for i in frame_indices], dtype=np.float64)
    errors = results_arr - gt_arr

    return {
        "mean_error": float(np.mean(errors)),
        "mean_absolute_error": float(np.mean(np.abs(errors))),
        "mean_squared_error": float(np.mean(np.square(errors))),
        "avg_gt_count": float(np.mean(gt_arr)),
        "avg_results_count": float(np.mean(results_arr)),
    }


def print_count_metrics(metrics: dict[str, Any]) -> None:
    print(f"Mean Error (ME): {metrics['mean_error']:.4f}")
    print(f"Mean Absolute Error (MAE): {metrics['mean_absolute_error']:.4f}")
    print(f"Mean Squared Error (MSE): {metrics['mean_squared_error']:.4f}")
    print(f"Avg GT Person Count: {metrics['avg_gt_count']:.4f}")
    print(f"Avg Predicted Person Count: {metrics['avg_results_count']:.4f}")
