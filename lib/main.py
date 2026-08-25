from pathlib import Path

from config.config_loader import ConfigLoader, TrackerConfig
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap import SpeedHeatmapBuilder, RoiHeatmapBuilder, RoiVisualizer, TripwireHeatmapBuilder, \
    TripwireVisualizer
from core.heatmap.clusters.cluster_heatmap_builder import ClusterHeatmapBuilder
from core.heatmap.directional.directional_heatmap_builder import (
    DirectionalHeatmapBuilder,
)
from core.heatmap.logic.logic import HeatmapLogic
from core.heatmap.speed.speed_filter import SpeedFilter
from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer
from core.helpers.camera_info import CameraInfo
from core.momentum.camera_to_world_mapper import CameraToWorldMapper
from core.momentum.momentum import MomentumTracker
from core.helpers import DataSourceInfoReader
from core.helpers.point import PointUtil
from models import YOLOModel
from project_root import PROJECT_ROOT
import time

# path = "data/datasets/mall_dataset/frames/"
path = PROJECT_ROOT / "data/datasets/yt/walking_people.mp4"


def _resolve_path(image_path: str) -> Path:
    path_obj = Path(image_path)
    if path_obj.is_absolute():
        return path_obj
    return PROJECT_ROOT / path_obj


to_save = {
    "directional": {
        "down": Path("lib/out/down"),
        "up": Path("lib/out/up"),
        "static": Path("lib/out/static"),
        "right": Path("lib/out/right"),
        "left": Path("lib/out/left"),
        "all": Path("lib/out/all"),
    },
    "speed": {
        "fast": Path("lib/out/fast"),
        "slow": Path("lib/out/slow"),
    },
    "cluster": {
        "2": Path("lib/out/two-people"),
        "3": Path("lib/out/three-people"),
    },
    "roi": {
       "inside->outside": Path("lib/out/inside->outside"),
        "outside->inside": Path("lib/out/outside->inside"),
    },
    "tripwire": {
        "inside->outside": Path("lib/out/tripwire-inside->outside"),
    },
    "combined": {
        "combined": Path("lib/out/combined"),
    }
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
    max_lost_frames = tracker_config.get("track_buffer", 10)
    directional_heatmap = (
        DirectionalHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_fps(metadata.fps)
        .with_momentum_buffer_size(15)
        .with_max_lost_frames(max_lost_frames)
        .build()
    )

    speed_heatmap = (
        SpeedHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_fps(metadata.fps)
        .with_momentum_buffer_size(15)
        .with_max_lost_frames(max_lost_frames)
        .with_speed_filter(SpeedFilter(name="slow", max_speed=2, get_speed_function=lambda x: x.speed_km_per_h))
        .with_speed_filter(SpeedFilter(name="fast", min_speed=3.5, get_speed_function=lambda x: x.speed_km_per_h))
        .build()
    )

    cluster_heatmap = (
        ClusterHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_fps(metadata.fps)
        .with_momentum_buffer_size(15)
        .with_max_lost_frames(max_lost_frames)
        .build()
    )

    polygon = [(250, 400), (250, 700), (600, 700), (600, 400)]
    roi_heatmap = (
        RoiHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_polygon(polygon)
        .build()
    )

    tripwire_heatmap = (
        TripwireHeatmapBuilder()
        .with_height(metadata.height)
        .with_width(metadata.width)
        .with_frames(metadata.frames)
        .with_tripwire((412, 370), (1350, 400), (750, 750))
        .build()
    )

    mapper = CameraToWorldMapper(CameraInfo().get_transformation_matrix())
    momentum = MomentumTracker(metadata.fps, 15, max_lost_frames, mapper)
    heatmap_visualizer = HeatmapVisualizer(fixed_max=3, alpha=0.5, sigma=25)

    roi_visualizer = RoiVisualizer(roi_heatmap.get_polygon())
    tripwire_visualizer = TripwireVisualizer(*tripwire_heatmap.get_tripwire())

    for category, save_paths in to_save.items():
        for direction, save_path in save_paths.items():
            save_path.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
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
        cluster_heatmap.handle(updates)
        roi_heatmap.handle(updates)
        tripwire_heatmap.handle(updates)

        lost_tracks_updates = momentum.flush_lost_tracks_buffers(
            set(point.track_id for point in processed_prediction.points)
        )
        directional_heatmap.execute_track_update_batch(lost_tracks_updates)
        speed_heatmap.execute_track_update_batch(lost_tracks_updates)


        combined_heatmap = (
            HeatmapLogic(directional_heatmap.get_heatmap()["up"])
            .and_(speed_heatmap.get_heatmap()["fast"])
            .and_(tripwire_heatmap.get_heatmap()["inside"])
            .result()
        )


        for direction, path_base in to_save["directional"].items():
            heatmap_visualizer.draw(
                directional_heatmap.get_heatmap()[direction],
                processed_prediction.image,
                save_path=path_base / f"{num}.png",
            )

        for speed, path_base in to_save["speed"].items():
            heatmap_visualizer.draw(
                speed_heatmap.get_heatmap()[speed],
                processed_prediction.image,
                save_path=path_base / f"{num}.png",
            )

        for cluster_size, path_base in to_save["cluster"].items():
            heatmap_visualizer.draw(
                cluster_heatmap.get_heatmap()[cluster_size],
                processed_prediction.image,
                save_path=path_base / f"{num}.png",
            )

        for roi_motion, path_base in to_save["roi"].items():
            background = heatmap_visualizer.draw(
                roi_heatmap.get_heatmap()[roi_motion], processed_prediction.image
            )
            roi_visualizer.draw(background, save_path=path_base / f"{num}.png")

        for tripwire_motion, path_base in to_save["tripwire"].items():
            background = heatmap_visualizer.draw(
                tripwire_heatmap.get_heatmap()[tripwire_motion], processed_prediction.image
            )
            tripwire_visualizer.draw(background, save_path=path_base / f"{num}.png")

        background = heatmap_visualizer.draw(combined_heatmap, processed_prediction.image)
        tripwire_visualizer.draw(
            background, save_path=to_save["combined"]["combined"] / f"{num}.png"
        )

    end = time.perf_counter()
    elapsed = end - start
    print(f"Time taken: {int(elapsed) // 60} minutes and {int(elapsed) % 60} seconds ({elapsed:.2f}s total {metadata.frames // elapsed} fps)")


if __name__ == "__main__":
    main()
