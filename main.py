from pathlib import Path
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap.heatmap_factory import HeatmapFactory
from core.heatmap.heatmap_visualizer import HeatmapVisualizer
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT

# path = "data/datasets/mall_dataset/frames/"
path = "data/datasets/yt/walking_people.mp4"

def _resolve_path(image_path: str) -> Path:
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        return path_obj
    return PROJECT_ROOT / path_obj


def main() -> None:
    model = YOLOModel(path)
    raw_predictions = model.run_tracking(show=False, stream=True)
    predictions_adapter = StreamedPredictionsAdapterFactory.for_model(model)

    hf = HeatmapFactory(1080, 1920)
    hv = HeatmapVisualizer(fixed_max=60, alpha=0.5, sigma=10)
    path_base= Path("out")

    for num, prediction in enumerate(raw_predictions):
        processed_prediction = predictions_adapter.to_predictions(prediction)
        heatmap = hf.get_heatmap_from_streamed_prediction(processed_prediction)
        hv.draw(heatmap["down"], processed_prediction.image, save_path= path_base / f"{num}.png")


if __name__ == "__main__":
    main()
