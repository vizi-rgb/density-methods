import numpy as np
from core.helpers.data_source_info import DataSourceInfo
from core.momentum.domain import TrackedPoint, TrackUpdate

from app.config import Settings
from app.services.pipeline import _ClusterTrack, _DirectionalTrack, _SpeedTrack

_METADATA = DataSourceInfo(height=100, width=100, frames=10, fps=25)
_SETTINGS = Settings()
_MAX_LOST_FRAMES = 10


def test_directional_track_draws_into_the_all_bucket() -> None:
    track = _DirectionalTrack(_METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label=None,
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_speed_track_uses_km_per_h_from_camera_calibration() -> None:
    # pipeline.py always builds a CameraToWorldMapper from CameraInfo's
    # transformation matrix (product decision), so speed_km_per_h is
    # populated for real predictions — the speed track keys off it.
    track = _SpeedTrack(_METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(0, 0),
        current_point=TrackedPoint(3, 3),
        direction_label="right",
        speed_px_per_s=5.0,
        speed_km_per_h=5.0,
        track_id=1,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(3, 3))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_cluster_track_frame_is_zero_when_no_clusters_formed() -> None:
    track = _ClusterTrack(_METADATA, _SETTINGS, _MAX_LOST_FRAMES)

    frame = track.frame()

    assert frame.shape == (100, 100)
    assert np.array_equal(frame, np.zeros((100, 100), dtype=np.float32))


def test_cluster_track_sums_activity_across_all_dynamic_cluster_sizes() -> None:
    # Cluster sizes are dynamic dict keys assigned by lib's DBSCAN clustering
    # (one bucket per distinct cluster size observed) — frame() must sum
    # across whatever buckets exist rather than assuming a fixed key.
    track = _ClusterTrack(_METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    close_pair = [
        TrackUpdate(
            was_tracked=True,
            first_point=None,
            last_point=None,
            current_point=TrackedPoint(10, 10),
            direction_label=None,
            speed_px_per_s=None,
            speed_km_per_h=None,
            track_id=track_id,
            processed_segments=[],
        )
        for track_id in (1, 2)
    ]

    track.handle(close_pair)
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0
