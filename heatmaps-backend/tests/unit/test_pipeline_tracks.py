import numpy as np
from core.helpers.data_source_info import DataSourceInfo
from core.momentum.domain import TrackedPoint, TrackUpdate

from app.config import Settings
from app.services.pipeline import (
    _ClusterTrack,
    _DirectionalTrack,
    _normalize_layers,
    _RoiTrack,
    _SpeedTrack,
    _TripwireTrack,
)

_METADATA = DataSourceInfo(height=100, width=100, frames=10, fps=25)
_SETTINGS = Settings()
_MAX_LOST_FRAMES = 10


def test_directional_track_draws_into_the_requested_direction_bucket() -> None:
    track = _DirectionalTrack("right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(2, 2))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_directional_track_only_populates_requested_bucket() -> None:
    # A "down" update shouldn't show up in the "up" track's frame.
    track = _DirectionalTrack("up", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="down",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(2, 2))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_directional_track_applies_half_life_decay() -> None:
    track = _DirectionalTrack("right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, 1)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(2, 2))],
    )

    track.handle([update])
    before = track.frame().sum()
    for _ in range(_METADATA.fps):
        track.apply_decay()
    after = track.frame().sum()

    assert after < before


def test_speed_track_uses_km_per_h_from_camera_calibration() -> None:
    # pipeline.py always builds a CameraToWorldMapper from CameraInfo's
    # transformation matrix (product decision), so speed_km_per_h is
    # populated for real predictions — the speed track keys off it.
    track = _SpeedTrack(None, None, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
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


def test_speed_track_respects_min_max_bounds() -> None:
    track = _SpeedTrack(10.0, 20.0, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    too_slow = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(0, 0),
        current_point=TrackedPoint(3, 3),
        direction_label="right",
        speed_px_per_s=1.0,
        speed_km_per_h=1.0,
        track_id=1,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(3, 3))],
    )

    track.handle([too_slow])
    frame = track.frame()

    assert frame.sum() == 0


def test_speed_track_applies_half_life_decay() -> None:
    track = _SpeedTrack(None, None, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, 1)
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
    before = track.frame().sum()
    for _ in range(_METADATA.fps):
        track.apply_decay()
    after = track.frame().sum()

    assert after < before


def test_cluster_track_frame_is_zero_when_requested_size_never_occurs() -> None:
    track = _ClusterTrack(5, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)

    frame = track.frame()

    assert frame.shape == (100, 100)
    assert np.array_equal(frame, np.zeros((100, 100), dtype=np.float32))


def test_cluster_track_renders_only_the_requested_group_size() -> None:
    # Two nearby points form a cluster of exactly size 2 — a track asking
    # for size 3 should stay empty even though *a* cluster formed.
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

    track_for_2 = _ClusterTrack(2, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    track_for_2.handle(close_pair)
    assert track_for_2.frame().sum() > 0

    track_for_3 = _ClusterTrack(3, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    track_for_3.handle(close_pair)
    assert track_for_3.frame().sum() == 0


def test_tripwire_track_draws_into_the_requested_bucket() -> None:
    # Vertical line at x=50; inside_point (90, 50) makes x>50 the "inside" half.
    track = _TripwireTrack(
        (50, 0), (50, 100), (90, 50), "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES
    )
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(80, 40), TrackedPoint(85, 45))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_tripwire_track_only_populates_requested_bucket() -> None:
    # Same update as above lands in "inside", so the "outside" bucket stays empty.
    track = _TripwireTrack(
        (50, 0), (50, 100), (90, 50), "outside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES
    )
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(80, 40), TrackedPoint(85, 45))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_roi_track_draws_into_the_requested_bucket() -> None:
    # Rectangle covering x in [50, 100]; the update below lands inside it.
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiTrack(polygon, "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(80, 40), TrackedPoint(85, 45))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_roi_track_only_populates_requested_bucket() -> None:
    # Same update as above lands in "inside", so "outside" stays empty.
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiTrack(polygon, "outside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = TrackUpdate(
        was_tracked=True,
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
        speed_px_per_s=None,
        speed_km_per_h=None,
        track_id=1,
        processed_segments=[(TrackedPoint(80, 40), TrackedPoint(85, 45))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_directional_speed_cluster_draw_overlay_is_identity() -> None:
    frame = np.full((100, 100, 3), 7, dtype=np.uint8)

    directional = _DirectionalTrack("right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    speed = _SpeedTrack(None, None, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    cluster = _ClusterTrack(2, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)

    assert directional.draw_overlay(frame) is frame
    assert speed.draw_overlay(frame) is frame
    assert cluster.draw_overlay(frame) is frame


def test_tripwire_draw_overlay_draws_the_line_on_top() -> None:
    background = np.zeros((100, 100, 3), dtype=np.uint8)
    track = _TripwireTrack(
        (50, 0), (50, 100), (90, 50), "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES
    )

    overlay = track.draw_overlay(background)

    assert overlay.sum() > 0


def test_roi_draw_overlay_draws_the_polygon_on_top() -> None:
    background = np.zeros((100, 100, 3), dtype=np.uint8)
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiTrack(polygon, "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)

    overlay = track.draw_overlay(background)

    assert overlay.sum() > 0


def test_normalize_layers_wraps_a_legacy_single_primitive_request() -> None:
    request = {"type": "speed", "min_speed": 7}

    layers = _normalize_layers(request)

    assert layers == [{"heatmap": request, "operator": None, "invert": False}]


def test_normalize_layers_extracts_a_composed_request() -> None:
    request = {
        "type": "composed",
        "layers": [
            {"heatmap": {"type": "speed", "min_speed": 7}},
            {
                "heatmap": {"type": "directional", "direction": "up"},
                "operator": "AND",
                "invert": True,
            },
        ],
    }

    layers = _normalize_layers(request)

    assert layers == [
        {"heatmap": {"type": "speed", "min_speed": 7}, "operator": None, "invert": False},
        {
            "heatmap": {"type": "directional", "direction": "up"},
            "operator": "AND",
            "invert": True,
        },
    ]
