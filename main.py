from pathlib import Path

from config.config_loader import ConfigLoader, TrackerConfig
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap import SpeedHeatmapBuilder
from core.heatmap.directional.directional_heatmap_builder import (
    DirectionalHeatmapBuilder,
)
from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer
from core.momentum.momentum import MomentumTracker
from core.helpers import DataSourceInfoReader
from core.helpers.point import PointUtil
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
    # "static": Path("out/static"),
    # "right": Path("out/right"),
    # "left": Path("out/left"),
    "speed": Path("out/speed"),
    "all": Path("out/all"),
}


def main() -> None:
    model = YOLOModel(path)
    raw_predictions = model.run_tracking(show=False, stream=True)
    predictions_adapter = StreamedPredictionsAdapterFactory.for_model(model)
    metadata = DataSourceInfoReader(path).read()

    if metadata is None:
        raise ValueError("Could not read metadata from source")

    assert metadata.fps is not None

    tracker_config = ConfigLoader.load_tracker_config(TrackerConfig.BOTSORT)
    directional_heatmap = (
        DirectionalHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_fps(metadata.fps)
        .with_momentum_buffer_size(15)
        .with_max_lost_frames(tracker_config.get("track_buffer", 10))
        .build()
    )

    speed_heatmap = (
        SpeedHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_fps(metadata.fps)
        .with_momentum_buffer_size(15)
        .with_half_life_time(4)
        .with_max_lost_frames(tracker_config.get("track_buffer", 10))
        .with_speed_max(90)
        .build()
    )

    momentum = MomentumTracker(metadata.fps, 15, tracker_config.get("track_buffer", 10))
    hv = HeatmapVisualizer(fixed_max=3, alpha=0.5, sigma=25)

    for direction, save_path in to_save.items():
        save_path.mkdir(parents=True, exist_ok=True)

    for num, prediction in enumerate(raw_predictions):
        processed_prediction = predictions_adapter.to_predictions(prediction)

        directional_heatmap.apply_decay()
        speed_heatmap.apply_decay()

        clamped_points = PointUtil.clamp_points_to_heatmap_points(
            processed_prediction.points, metadata.width, metadata.height
        )
        updates = momentum.update_batch(
            [idx.track_id for idx in processed_prediction.points], clamped_points
        )

        directional_heatmap.handle(updates)
        speed_heatmap.handle(updates)

        lost_tracks_updates = momentum.flush_lost_tracks_buffers(
            set(point.track_id for point in processed_prediction.points)
        )
        directional_heatmap.execute_track_update_batch(lost_tracks_updates)
        speed_heatmap.execute_track_update_batch(lost_tracks_updates)

        hv.draw(
            speed_heatmap.get_heatmap(),
            processed_prediction.image,
            save_path=to_save["speed"] / f"{num}.png",
        )

        # for direction, path_base in to_save.items():
        #     hv.draw(
        #         directional_heatmap.get_heatmap()[direction],
        #         processed_prediction.image,
        #         save_path=path_base / f"{num}.png",
        #     )


if __name__ == "__main__":
    main()
