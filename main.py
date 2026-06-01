from pathlib import Path

from config.config_loader import ConfigLoader, TrackerConfig
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap.heatmap_factory import HeatmapFactory
from core.heatmap.heatmap_visualizer import HeatmapVisualizer
from core.util import DataSourceInfoReader
from models.yolo.yolo import YOLOModel
from project_root import PROJECT_ROOT

# path = "data/datasets/mall_dataset/frames/"
path = "data/datasets/yt/walking_people.mp4"


def _resolve_path(image_path: str) -> Path:
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        return path_obj
    return PROJECT_ROOT / path_obj

to_save = {
    "down": Path("out/down"),
    "up": Path("out/up"),
    "static": Path("out/static"),
    "right": Path("out/right"),
    "left": Path("out/left"),
}


def main() -> None:
    model = YOLOModel(path)
    raw_predictions = model.run_tracking(show=False, stream=True)
    predictions_adapter = StreamedPredictionsAdapterFactory.for_model(model)
    metadata = DataSourceInfoReader(path).read()
    tracker_config = ConfigLoader.load_tracker_config(TrackerConfig.BOTSORT)
    # fps = metadata.fps // 3 if metadata.fps else 1
    fps = 15

    hf = HeatmapFactory.from_metadata(metadata, fps, tracker_config.get("track_buffer", 10))
    hv = HeatmapVisualizer(fixed_max=2, alpha=0.5, sigma=15)

    for direction, save_path in to_save.items():
        save_path.mkdir(parents=True, exist_ok=True)

    for num, prediction in enumerate(raw_predictions):
        processed_prediction = predictions_adapter.to_predictions(prediction)
        heatmap = hf.get_heatmap_from_streamed_prediction(processed_prediction)
        for direction, path_base in to_save.items():
            hv.draw(
                heatmap[direction],
                processed_prediction.image,
                save_path=path_base / f"{num}.png",
            )


if __name__ == "__main__":
    main()
