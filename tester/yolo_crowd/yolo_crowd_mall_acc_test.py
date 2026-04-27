import numpy as np

from models.yolo_crowd.yolo_crowd import YOLOCrowdModel
from project_root import PROJECT_ROOT
from tester.mall_acc_common import (
    compute_count_metrics,
    load_mall_gt_counts,
    print_count_metrics,
)


class YOLOCrowdMallAccTest:
    def __init__(self):
        self.dataset_path = (
            PROJECT_ROOT / "data" / "datasets" / "mall_dataset" / "frames"
        )
        self.gt_path = (
            PROJECT_ROOT / "data" / "datasets" / "mall_dataset" / "mall_gt.mat"
        )
        self.model = YOLOCrowdModel(dataset_path=str(self.dataset_path))

    def run_test(self):
        raw_results = self.model.run_prediction(show=False)
        print(
            f"YOLO Crowd Mall Accuracy Test performed predictions: {len(raw_results)}"
        )

        results_count = np.array(
            [
                result["count"]
                if "count" in result
                else len(result.get("detections", []))
                for result in raw_results
            ],
            dtype=np.float64,
        )
        gt_count = load_mall_gt_counts(self.gt_path)
        metrics = compute_count_metrics(results_count, gt_count)
        if metrics is None:
            return
        print_count_metrics(metrics)


if __name__ == "__main__":
    tester = YOLOCrowdMallAccTest()
    tester.run_test()
