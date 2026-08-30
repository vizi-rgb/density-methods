"""Orchestrates the `lib` (density-methods) building blocks into a single
video-in / per-frame-overlay-out pipeline for exactly one heatmap request.

There is no such single entrypoint in `lib` itself — `lib/main.py` wires the
same pieces together by hand for one hardcoded video/ROI/tripwire setup. This
mirrors that wiring for arbitrary uploaded videos.

Builds a `CameraToWorldMapper` from the `transformation_matrix` passed in by
the caller and passes it to `MomentumTracker`. The caller (`app/api/routes/
heatmaps.py`) resolves this per-video, from a matrix calibrated via
`POST /api/videos/{video_id}/calibration`, falling back to `lib`'s
`CameraInfo` hardcoded reference-video calibration when a video hasn't been
calibrated.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np
from config.config_loader import ConfigLoader, TrackerConfig
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap.birdseye.birds_eye_view_heatmap_builder import (
    BirdsEyeViewHeatmapBuilder,
)
from core.heatmap.birdseye.cluster_birds_eye_view_heatmap_builder import (
    ClusterBirdsEyeViewHeatmapBuilder,
)
from core.heatmap.birdseye.directional_birds_eye_view_heatmap_builder import (
    DirectionalBirdsEyeViewHeatmapBuilder,
)
from core.heatmap.birdseye.roi_birds_eye_view_heatmap_builder import (
    RoiBirdsEyeViewHeatmapBuilder,
)
from core.heatmap.birdseye.speed_birds_eye_view_heatmap_builder import (
    SpeedBirdsEyeViewHeatmapBuilder,
)
from core.heatmap.birdseye.tripwire_birds_eye_view_heatmap_builder import (
    TripwireBirdsEyeViewHeatmapBuilder,
)
from core.heatmap.clusters.cluster_heatmap_builder import ClusterHeatmapBuilder
from core.heatmap.directional.directional_heatmap_builder import (
    DirectionalHeatmapBuilder,
)
from core.heatmap.logic.logic import HeatmapLogic
from core.heatmap.roi.roi_heatmap_builder import RoiHeatmapBuilder
from core.heatmap.speed.speed_filter import SpeedFilter
from core.heatmap.speed.speed_heatmap_builder import SpeedHeatmapBuilder
from core.heatmap.tripwire.tripwire_heatmap_builder import TripwireHeatmapBuilder
from core.heatmap.visualizer.birds_eye_view_visualizer import BirdsEyeViewVisualizer
from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer
from core.heatmap.visualizer.roi_visualizer import RoiVisualizer
from core.heatmap.visualizer.tripwire_visualizer import TripwireVisualizer
from core.helpers.data_source_info import DataSourceInfo, DataSourceInfoReader
from core.helpers.point import PointUtil
from core.momentum.camera_to_world_mapper import CameraToWorldMapper
from core.momentum.momentum import MomentumTracker
from models import YOLOModel

from app.config import Settings


class PipelineError(Exception):
    """Raised for input that made the pipeline unable to run (not a bug)."""


class _HeatmapTrack(Protocol):
    def apply_decay(self) -> None: ...
    def handle(self, updates: list) -> None: ...
    def flush(self, lost_updates: list) -> None: ...
    def frame(self) -> np.ndarray: ...
    def draw_overlay(self, frame: np.ndarray) -> np.ndarray: ...


class _DirectionalTrack:
    def __init__(
        self,
        direction: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        half_life_time: int | None = None,
    ) -> None:
        self._direction = direction
        builder = (
            DirectionalHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()[self._direction]

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _SpeedTrack:
    _FILTER_NAME = "selected"

    def __init__(
        self,
        min_speed: float | None,
        max_speed: float | None,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        half_life_time: int | None = None,
    ) -> None:
        speed_filter = SpeedFilter(
            name=self._FILTER_NAME,
            min_speed=min_speed if min_speed is not None else 0.0,
            max_speed=max_speed if max_speed is not None else float("inf"),
            get_speed_function=lambda u: u.speed_km_per_h,
        )
        builder = (
            SpeedHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_speed_filter(speed_filter)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()[self._FILTER_NAME]

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _ClusterTrack:
    def __init__(
        self,
        group_size: int,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        half_life_time: int | None = None,
    ) -> None:
        self._group_size_key = str(group_size)
        self._height = metadata.height
        self._width = metadata.width
        builder = (
            ClusterHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
        )

        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        pass  # ClusterHeatmap has no lost-track flushing.

    def frame(self) -> np.ndarray:
        buckets = self._heatmap.get_heatmap()
        bucket = buckets.get(self._group_size_key)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _TripwireTrack:
    def __init__(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        inside_point: tuple[float, float],
        bucket: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        half_life_time: int | None = None,
    ) -> None:
        self._bucket = bucket
        self._height = metadata.height
        self._width = metadata.width
        builder = (
            TripwireHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_tripwire(p1, p2, inside_point)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()
        self._line_visualizer = TripwireVisualizer(*self._heatmap.get_tripwire())

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        # Tripwire is Roi-backed; RoiHeatmap.execute_track_update_batch()
        # raises NotImplementedError for lost-track flushing.
        pass

    def frame(self) -> np.ndarray:
        bucket = self._heatmap.get_heatmap().get(self._bucket)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return self._line_visualizer.draw(frame)


class _RoiTrack:
    def __init__(
        self,
        polygon: Sequence[tuple[float, float]],
        bucket: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        half_life_time: int | None = None,
    ) -> None:
        self._bucket = bucket
        self._height = metadata.height
        self._width = metadata.width
        builder = (
            RoiHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_polygon(polygon)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()
        self._polygon_visualizer = RoiVisualizer(self._heatmap.get_polygon())

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        # RoiHeatmap.execute_track_update_batch() raises NotImplementedError
        # for lost-track flushing.
        pass

    def frame(self) -> np.ndarray:
        bucket = self._heatmap.get_heatmap().get(self._bucket)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return self._polygon_visualizer.draw(frame)



class _DirectionalBirdsEyeTrack:
    def __init__(
        self,
        direction: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        camera_to_world_mapper: CameraToWorldMapper,
        half_life_time: int | None = None,
    ) -> None:
        self._direction = direction
        builder = (
            DirectionalBirdsEyeViewHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_camera_to_world_mapper(camera_to_world_mapper)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()[self._direction]

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _SpeedBirdsEyeTrack:
    _FILTER_NAME = "selected"

    def __init__(
        self,
        min_speed: float | None,
        max_speed: float | None,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        camera_to_world_mapper: CameraToWorldMapper,
        half_life_time: int | None = None,
    ) -> None:
        speed_filter = SpeedFilter(
            name=self._FILTER_NAME,
            min_speed=min_speed if min_speed is not None else 0.0,
            max_speed=max_speed if max_speed is not None else float("inf"),
            get_speed_function=lambda u: u.speed_km_per_h,
        )
        builder = (
            SpeedBirdsEyeViewHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_camera_to_world_mapper(camera_to_world_mapper)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_speed_filter(speed_filter)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()[self._FILTER_NAME]

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _ClusterBirdsEyeTrack:
    def __init__(
        self,
        group_size: int,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        camera_to_world_mapper: CameraToWorldMapper,
        half_life_time: int | None = None,
    ) -> None:
        self._group_size_key = str(group_size)
        builder = (
            ClusterBirdsEyeViewHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_camera_to_world_mapper(camera_to_world_mapper)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()
        self._height = self._heatmap.height
        self._width = self._heatmap.width

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        pass  # ClusterHeatmap has no lost-track flushing.

    def frame(self) -> np.ndarray:
        buckets = self._heatmap.get_heatmap()
        bucket = buckets.get(self._group_size_key)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return frame


class _TripwireBirdsEyeTrack:
    def __init__(
        self,
        p1: tuple[float, float],
        p2: tuple[float, float],
        inside_point: tuple[float, float],
        bucket: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        camera_to_world_mapper: CameraToWorldMapper,
        half_life_time: int | None = None,
    ) -> None:
        self._bucket = bucket
        builder = (
            TripwireBirdsEyeViewHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_camera_to_world_mapper(camera_to_world_mapper)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_tripwire(p1, p2, inside_point)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()
        self._line_visualizer = TripwireVisualizer(*self._heatmap.get_tripwire())
        self._height = self._heatmap.height
        self._width = self._heatmap.width

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        # Tripwire is Roi-backed; RoiHeatmap.execute_track_update_batch()
        # raises NotImplementedError for lost-track flushing.
        pass

    def frame(self) -> np.ndarray:
        bucket = self._heatmap.get_heatmap().get(self._bucket)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return self._line_visualizer.draw(frame)


class _RoiBirdsEyeTrack:
    def __init__(
        self,
        polygon: Sequence[tuple[float, float]],
        bucket: str,
        metadata: DataSourceInfo,
        settings: Settings,
        max_lost_frames: int,
        camera_to_world_mapper: CameraToWorldMapper,
        half_life_time: int | None = None,
    ) -> None:
        self._bucket = bucket
        builder = (
            RoiBirdsEyeViewHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_camera_to_world_mapper(camera_to_world_mapper)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_polygon(polygon)
        )
        if half_life_time is not None:
            builder = builder.with_half_life_time(half_life_time)
        self._heatmap = builder.build()
        self._polygon_visualizer = RoiVisualizer(self._heatmap.get_polygon())
        self._height = self._heatmap.height
        self._width = self._heatmap.width

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        # RoiHeatmap.execute_track_update_batch() raises NotImplementedError
        # for lost-track flushing.
        pass

    def frame(self) -> np.ndarray:
        bucket = self._heatmap.get_heatmap().get(self._bucket)
        if bucket is None:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return bucket

    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        return self._polygon_visualizer.draw(frame)


def _build_track(
    heatmap_request: dict[str, Any],
    metadata: DataSourceInfo,
    settings: Settings,
    max_lost_frames: int,
    view: str,
    camera_to_world_mapper: CameraToWorldMapper,
) -> _HeatmapTrack:
    heatmap_type = heatmap_request["type"]
    is_world = view == "world"

    if heatmap_type == "directional":
        if is_world:
            return _DirectionalBirdsEyeTrack(
                heatmap_request["direction"],
                metadata,
                settings,
                max_lost_frames,
                camera_to_world_mapper,
                heatmap_request.get("half_life_time"),
            )
        return _DirectionalTrack(
            heatmap_request["direction"],
            metadata,
            settings,
            max_lost_frames,
            heatmap_request.get("half_life_time"),
        )
    if heatmap_type == "speed":
        if is_world:
            return _SpeedBirdsEyeTrack(
                heatmap_request.get("min_speed"),
                heatmap_request.get("max_speed"),
                metadata,
                settings,
                max_lost_frames,
                camera_to_world_mapper,
                heatmap_request.get("half_life_time"),
            )
        return _SpeedTrack(
            heatmap_request.get("min_speed"),
            heatmap_request.get("max_speed"),
            metadata,
            settings,
            max_lost_frames,
            heatmap_request.get("half_life_time"),
        )
    if heatmap_type == "cluster":
        if is_world:
            return _ClusterBirdsEyeTrack(
                heatmap_request["group_size"],
                metadata,
                settings,
                max_lost_frames,
                camera_to_world_mapper,
                heatmap_request.get("half_life_time"),
            )
        return _ClusterTrack(
            heatmap_request["group_size"],
            metadata,
            settings,
            max_lost_frames,
            heatmap_request.get("half_life_time")
        )
    if heatmap_type == "tripwire":
        if is_world:
            return _TripwireBirdsEyeTrack(
                tuple(heatmap_request["p1"]),
                tuple(heatmap_request["p2"]),
                tuple(heatmap_request["inside_point"]),
                heatmap_request["bucket"],
                metadata,
                settings,
                max_lost_frames,
                camera_to_world_mapper,
                heatmap_request.get("half_life_time"),
            )
        return _TripwireTrack(
            tuple(heatmap_request["p1"]),
            tuple(heatmap_request["p2"]),
            tuple(heatmap_request["inside_point"]),
            heatmap_request["bucket"],
            metadata,
            settings,
            max_lost_frames,
            heatmap_request.get("half_life_time"),
        )
    if heatmap_type == "roi":
        if is_world:
            return _RoiBirdsEyeTrack(
                [tuple(p) for p in heatmap_request["polygon"]],
                heatmap_request["bucket"],
                metadata,
                settings,
                max_lost_frames,
                camera_to_world_mapper,
                heatmap_request.get("half_life_time"),
            )
        return _RoiTrack(
            [tuple(p) for p in heatmap_request["polygon"]],
            heatmap_request["bucket"],
            metadata,
            settings,
            max_lost_frames,
            heatmap_request.get("half_life_time"),
        )

    raise PipelineError(f"Unsupported heatmap type: {heatmap_type!r}")


def _normalize_layers(heatmap_request: dict[str, Any]) -> list[dict[str, Any]]:
    """Both request shapes reduce to an ordered list of layers: a legacy
    single-primitive request is just the 1-layer case, with no operator."""
    if heatmap_request["type"] == "composed":
        return [
            {
                "heatmap": layer["heatmap"],
                "operator": layer.get("operator"),
                "invert": layer.get("invert", False),
            }
            for layer in heatmap_request["layers"]
        ]
    return [{"heatmap": heatmap_request, "operator": None, "invert": False}]


def read_metadata(video_path: Path) -> DataSourceInfo:
    metadata = DataSourceInfoReader(video_path).read()
    if not metadata.fps or metadata.fps <= 0:
        raise PipelineError(
            f"Could not determine a valid frame rate for video: {video_path}"
        )
    if metadata.frames <= 0:
        raise PipelineError(f"Video has no decodable frames: {video_path}")
    return metadata


def resolve_output_dimensions(
    view: str,
    metadata: DataSourceInfo,
    transformation_matrix: list[list[float]],
    settings: Settings,
) -> tuple[int, int]:
    """(width, height) of the frames `run()` yields for `view`. Camera view
    matches the source video's native resolution; world view renders on a
    small real-world/meter grid (see lib's birdseye classes) then upscales by
    `settings.birdseye_display_scale` — used both to size the `Mp4Encoder`
    (app/worker/tasks.py) and as `run()`'s own resize target, so the two
    never drift apart."""
    if view != "world":
        return metadata.width, metadata.height

    camera_to_world_mapper = CameraToWorldMapper(
        np.array(transformation_matrix, dtype=np.float32)
    )
    grid = (
        BirdsEyeViewHeatmapBuilder()
        .with_width(metadata.width)
        .with_height(metadata.height)
        .with_camera_to_world_mapper(camera_to_world_mapper)
        .build()
    )
    return (
        grid.width * settings.birdseye_display_scale,
        grid.height * settings.birdseye_display_scale,
    )


def run(
    video_path: Path,
    metadata: DataSourceInfo,
    heatmap_request: dict[str, Any],
    settings: Settings,
    transformation_matrix: list[list[float]],
) -> Iterator[np.ndarray]:
    """Yields one BGR overlay frame per input frame for `heatmap_request`."""
    view = heatmap_request.get("view", "camera")
    tracker_config = ConfigLoader.load_tracker_config(TrackerConfig.BOTSORT)
    max_lost_frames = tracker_config.get(
        "track_buffer", settings.default_max_lost_frames
    )

    camera_world_mapper = CameraToWorldMapper(
        np.array(transformation_matrix, dtype=np.float32)
    )
    momentum = MomentumTracker(
        metadata.fps, settings.momentum_buffer_size, max_lost_frames, camera_world_mapper
    )

    tracks = [
        (
            _build_track(
                layer["heatmap"], metadata, settings, max_lost_frames, view, camera_world_mapper
            ),
            layer["operator"],
            layer["invert"],
        )
        for layer in _normalize_layers(heatmap_request)
    ]

    model = YOLOModel(str(video_path))
    raw_predictions = model.run_tracking(show=False, stream=True)
    predictions_adapter = StreamedPredictionsAdapterFactory.for_model(model)
    visualizer_override = heatmap_request.get("visualizer")
    visualizer_kwargs = dict(
        fixed_max=(
            visualizer_override["fixed_max"] if visualizer_override else settings.heatmap_fixed_max
        ),
        alpha=visualizer_override["alpha"] if visualizer_override else settings.heatmap_alpha,
        sigma=visualizer_override["sigma"] if visualizer_override else settings.heatmap_sigma,
    )
    visualizer = (
        BirdsEyeViewVisualizer(**visualizer_kwargs)
        if view == "world"
        else HeatmapVisualizer(**visualizer_kwargs)
    )
    output_dimensions = (
        resolve_output_dimensions(view, metadata, transformation_matrix, settings)
        if view == "world"
        else None
    )

    for raw_prediction in raw_predictions:
        processed = predictions_adapter.to_predictions(raw_prediction)
        source_image = raw_prediction.orig_img

        for track, _, _ in tracks:
            track.apply_decay()

        clamped_points = PointUtil.clamp_points_to_heatmap_points(
            processed.points, metadata.width, metadata.height
        )
        track_ids = [point.track_id for point in processed.points]
        updates = momentum.update_batch(track_ids, clamped_points)

        for track, _, _ in tracks:
            track.handle(updates)

        lost_updates = momentum.flush_lost_tracks_buffers(set(track_ids))
        for track, _, _ in tracks:
            track.flush(lost_updates)

        cumulative: HeatmapLogic | None = None
        for track, operator, invert in tracks:
            layer_frame = track.frame()
            if invert:
                layer_frame = HeatmapLogic(layer_frame).negate().result()
            if cumulative is None:
                cumulative = HeatmapLogic(layer_frame)
            elif operator == "AND":
                cumulative.and_(layer_frame)
            elif operator == "OR":
                cumulative.or_(layer_frame)
            elif operator == "AND_NOT":
                cumulative.and_not(layer_frame)

        assert cumulative is not None  # tracks is never empty
        background = visualizer.draw(
            cumulative.result(), None if view == "world" else source_image
        )
        for track, _, _ in tracks:
            background = track.draw_overlay(background)
        if output_dimensions is not None:
            background = cv2.resize(
                background, output_dimensions, interpolation=cv2.INTER_NEAREST
            )
        yield background
