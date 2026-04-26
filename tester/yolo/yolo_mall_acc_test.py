import os

import numpy as np
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT
import scipy.io


class YOLOMallAccTest:
    def __init__(self):
        self.dataset_path = (
            PROJECT_ROOT / "data" / "datasets" / "mall_dataset" / "frames"
        )
        self.gt_path = (
            PROJECT_ROOT / "data" / "datasets" / "mall_dataset" / "mall_gt.mat"
        )
        self.model = YOLOModel(dataset_path=str(self.dataset_path))

    def run_test(self):
        raw_results = self.model.run_prediction(show=False)
        print(f"YOLO Mall Accuracy Test performed predictions: {len(raw_results)}")
        results_count = np.array(
            [len(result.boxes) for result in raw_results], dtype=np.float64
        )
        gt_count = self._get_gt(self.gt_path)
        frame_indices = [i for i in range(len(results_count)) if i in gt_count]

        if not frame_indices:
            print("No overlapping frames between predictions and GT.")
            return

        results_arr = results_count[frame_indices]
        gt_arr = np.array([gt_count[i] for i in frame_indices], dtype=np.float64)
        errors = results_arr - gt_arr

        mean_error = np.mean(errors)
        mean_absolute_error = np.mean(np.abs(errors))
        mean_squared_error = np.mean(np.square(errors))
        avg_gt_count = np.mean(gt_arr)
        avg_results_count = np.mean(results_arr)

        print(f"Mean Error (ME): {mean_error:.4f}")
        print(f"Mean Absolute Error (MAE): {mean_absolute_error:.4f}")
        print(f"Mean Squared Error (MSE): {mean_squared_error:.4f}")
        print(f"Avg GT Person Count: {avg_gt_count:.4f}")
        print(f"Avg Predicted Person Count: {avg_results_count:.4f}")

    def _get_gt(self, ground_truth_path):
        mall_gt_counts = {}
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


if __name__ == "__main__":
    tester = YOLOMallAccTest()
    tester.run_test()
