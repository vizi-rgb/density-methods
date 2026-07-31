import numpy as np
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT
from tester.mall_acc_common import (
    compute_count_metrics,
    load_mall_gt_counts,
    print_count_metrics,
)


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
        gt_count = load_mall_gt_counts(self.gt_path)
        metrics = compute_count_metrics(results_count, gt_count)
        if metrics is None:
            return
        print_count_metrics(metrics)


if __name__ == "__main__":
    tester = YOLOMallAccTest()
    tester.run_test()
