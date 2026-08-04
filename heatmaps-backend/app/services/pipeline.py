"""Orchestrates the `lib` (density-methods) building blocks into a single
video-in / per-frame-overlays-out pipeline.

There is no such single entrypoint in `lib` itself — `lib/main.py` wires the
same pieces together by hand for one hardcoded video/ROI/tripwire setup. This
mirrors that wiring for arbitrary uploaded videos, restricted to the
geometry-free heatmap types (`directional`/`speed`/`cluster`) since no UI
collects ROI polygons or tripwire lines.

Always builds a `CameraToWorldMapper` from `lib`'s `CameraInfo` transformation
matrix and passes it to `MomentumTracker`, per product decision — note
`CameraInfo`'s keypoints are a hardcoded perspective calibration for one
specific reference video, so `speed_km_per_h` for an arbitrary upload is only
as accurate as that calibration happens to be for the uploaded footage.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Protocol

import numpy as np
from config.config_loader import ConfigLoader, TrackerConfig
from core.adapter.predictions_adapter_factory import StreamedPredictionsAdapterFactory
from core.heatmap.clusters.cluster_heatmap_builder import ClusterHeatmapBuilder
from core.heatmap.directional.directional_heatmap_builder import (
    DirectionalHeatmapBuilder,
)
from core.heatmap.speed.speed_filter import SpeedFilter
from core.heatmap.speed.speed_heatmap_builder import SpeedHeatmapBuilder
from core.heatmap.visualizer.heatmap_visualizer import HeatmapVisualizer
from core.helpers.camera_info import CameraInfo
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


class _DirectionalTrack:
    def __init__(
        self, metadata: DataSourceInfo, settings: Settings, max_lost_frames: int
    ) -> None:
        self._heatmap = (
            DirectionalHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .build()
        )

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()["all"]


class _SpeedTrack:
    def __init__(
        self, metadata: DataSourceInfo, settings: Settings, max_lost_frames: int
    ) -> None:
        speed_filter = SpeedFilter(
            name="all", get_speed_function=lambda u: u.speed_km_per_h
        )
        self._heatmap = (
            SpeedHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .with_speed_filter(speed_filter)
            .build()
        )

    def apply_decay(self) -> None:
        self._heatmap.apply_decay()

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        self._heatmap.execute_track_update_batch(lost_updates)

    def frame(self) -> np.ndarray:
        return self._heatmap.get_heatmap()["all"]


class _ClusterTrack:
    def __init__(
        self, metadata: DataSourceInfo, settings: Settings, max_lost_frames: int
    ) -> None:
        self._height = metadata.height
        self._width = metadata.width
        self._heatmap = (
            ClusterHeatmapBuilder()
            .with_height(metadata.height)
            .with_width(metadata.width)
            .with_frames(metadata.frames)
            .with_fps(metadata.fps)
            .with_momentum_buffer_size(settings.momentum_buffer_size)
            .with_max_lost_frames(max_lost_frames)
            .build()
        )

    def apply_decay(self) -> None:
        pass  # ClusterHeatmap has no decay support.

    def handle(self, updates: list) -> None:
        self._heatmap.handle(updates)

    def flush(self, lost_updates: list) -> None:
        pass  # ClusterHeatmap has no lost-track flushing.

    def frame(self) -> np.ndarray:
        # Cluster sizes are dynamic, unbounded dict keys (one per distinct
        # cluster size observed so far) — there's no single fixed sub-key
        # like directional's "all", so the rendered video sums activity
        # across every cluster size seen.
        buckets = self._heatmap.get_heatmap()
        if not buckets:
            return np.zeros((self._height, self._width), dtype=np.float32)
        return np.sum(np.stack(list(buckets.values())), axis=0)


_TRACK_FACTORIES: dict[str, type] = {
    "directional": _DirectionalTrack,
    "speed": _SpeedTrack,
    "cluster": _ClusterTrack,
}


def read_metadata(video_path: Path) -> DataSourceInfo:
    metadata = DataSourceInfoReader(video_path).read()
    if not metadata.fps or metadata.fps <= 0:
        raise PipelineError(
            f"Could not determine a valid frame rate for video: {video_path}"
        )
    if metadata.frames <= 0:
        raise PipelineError(f"Video has no decodable frames: {video_path}")
    return metadata


def run(
    video_path: Path,
    metadata: DataSourceInfo,
    heatmap_types: Sequence[str],
    settings: Settings,
) -> Iterator[dict[str, np.ndarray]]:
    """Yields one `{heatmap_type: BGR overlay frame}` dict per input frame."""
    unknown = set(heatmap_types) - _TRACK_FACTORIES.keys()
    if unknown:
        raise PipelineError(f"Unsupported heatmap type(s): {sorted(unknown)}")

    tracker_config = ConfigLoader.load_tracker_config(TrackerConfig.BOTSORT)
    max_lost_frames = tracker_config.get(
        "track_buffer", settings.default_max_lost_frames
    )

    tracks: dict[str, _HeatmapTrack] = {
        heatmap_type: _TRACK_FACTORIES[heatmap_type](metadata, settings, max_lost_frames)
        for heatmap_type in heatmap_types
    }

    model = YOLOModel(str(video_path))
    raw_predictions = model.run_tracking(show=False, stream=True)
    predictions_adapter = StreamedPredictionsAdapterFactory.for_model(model)
    camera_world_mapper = CameraToWorldMapper(CameraInfo().get_transformation_matrix())
    momentum = MomentumTracker(
        metadata.fps, settings.momentum_buffer_size, max_lost_frames, camera_world_mapper
    )
    visualizer = HeatmapVisualizer(
        fixed_max=settings.heatmap_fixed_max,
        alpha=settings.heatmap_alpha,
        sigma=settings.heatmap_sigma,
    )

    for raw_prediction in raw_predictions:
        processed = predictions_adapter.to_predictions(raw_prediction)
        source_image = raw_prediction.orig_img

        for track in tracks.values():
            track.apply_decay()

        clamped_points = PointUtil.clamp_points_to_heatmap_points(
            processed.points, metadata.width, metadata.height
        )
        track_ids = [point.track_id for point in processed.points]
        updates = momentum.update_batch(track_ids, clamped_points)

        for track in tracks.values():
            track.handle(updates)

        lost_updates = momentum.flush_lost_tracks_buffers(set(track_ids))
        for track in tracks.values():
            track.flush(lost_updates)

        yield {
            heatmap_type: visualizer.draw(track.frame(), source_image)
            for heatmap_type, track in tracks.items()
        }
