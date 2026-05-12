from pathlib import Path

import cv2

from core.adapter.predictions_adapter import PredictionsAdapter
from core.heatmap.heatmap_factory import HeatmapFactory
from core.heatmap.heatmap_visualizer import HeatmapVisualizer
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT

path = "data/datasets/mall_dataset/frames/"

def _resolve_path(image_path: str) -> Path:
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        return path_obj
    return PROJECT_ROOT / path_obj


def main() -> None:
    model = YOLOModel(path)
    raw_predictions = model.run_prediction(show=False)
    predictions = PredictionsAdapter().to_predictions(raw_predictions)

    if not predictions:
        raise RuntimeError("No predictions were produced.")

    hf = HeatmapFactory(480, 640)
    hv = HeatmapVisualizer(fixed_max=1000, alpha=0.5, sigma=15)
    path_base = Path("out")
    for num, prediction in enumerate(predictions):
        heatmap = hf.get_heatmap_from_streamed_prediction(prediction)
        hv.draw(heatmap, prediction.image_path, save_path= path_base / f"{num}.png")


if __name__ == "__main__":
    main()
