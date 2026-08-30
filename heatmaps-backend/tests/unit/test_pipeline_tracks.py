import cv2
import numpy as np
from core.helpers.data_source_info import DataSourceInfo
from core.momentum.camera_to_world_mapper import CameraToWorldMapper
from core.momentum.domain import TrackedPoint, TrackUpdate, WorldPoint

from core.heatmap.birdseye.birds_eye_view_heatmap_builder import (
    BirdsEyeViewHeatmapBuilder,
)

from app.config import Settings
from app.services.pipeline import (
    _ClusterBirdsEyeTrack,
    _ClusterTrack,
    _DirectionalBirdsEyeTrack,
    _DirectionalTrack,
    _normalize_layers,
    _RoiBirdsEyeTrack,
    _RoiTrack,
    _SpeedBirdsEyeTrack,
    _SpeedTrack,
    _TripwireBirdsEyeTrack,
    _TripwireTrack,
    resolve_output_dimensions,
)

_METADATA = DataSourceInfo(height=100, width=100, frames=10, fps=25)
_SETTINGS = Settings()
_MAX_LOST_FRAMES = 10

# A 15x6m room mapped onto the full 100x100 camera frame — a pure axis-aligned
# scale (no rotation), so camera (x, y) -> world (x * 0.15, y * 0.06).
_CAMERA_POINTS = np.array([[0, 0], [0, 100], [100, 100], [100, 0]], dtype=np.float32)
_WORLD_POINTS = np.array([[0, 0], [0, 6], [15, 6], [15, 0]], dtype=np.float32)
# Canonical list-of-lists form, matching what actually flows through the API
# (JSON -> Pydantic -> plain list) and `resolve_output_dimensions`'s own
# `np.array(transformation_matrix, dtype=np.float32)` round-trip — building
# `_CAMERA_TO_WORLD_MAPPER` from this exact representation (rather than
# straight from `cv2.getPerspectiveTransform`'s float64 output) keeps the
# grid math bit-for-bit identical to what the tracks under test compute.
_TRANSFORMATION_MATRIX = cv2.getPerspectiveTransform(
    _CAMERA_POINTS, _WORLD_POINTS
).tolist()
_CAMERA_TO_WORLD_MAPPER = CameraToWorldMapper(
    np.array(_TRANSFORMATION_MATRIX, dtype=np.float32)
)
# The birdseye grid shape for _METADATA at the library's default granularity
# (0.05), computed via the real builder rather than hand-derived, since the
# float32 perspective-transform math can round either 7 or 8 for a
# mathematically-exact-8 world dimension.
_GRID = (
    BirdsEyeViewHeatmapBuilder()
    .with_width(_METADATA.width)
    .with_height(_METADATA.height)
    .with_camera_to_world_mapper(_CAMERA_TO_WORLD_MAPPER)
    .build()
)
_GRID_SHAPE = (_GRID.height, _GRID.width)


def _camera_update(
    *,
    was_tracked: bool = True,
    first_point: TrackedPoint | None = None,
    last_point: TrackedPoint | None = None,
    current_point: TrackedPoint | None = None,
    direction_label: str | None = None,
    speed_px_per_s: float | None = None,
    speed_km_per_h: float | None = None,
    track_id: int | None = 1,
    processed_segments=(),
) -> TrackUpdate:
    """Camera-view fixture — the `*_world` fields aren't read by camera-view
    tracks, so they're left as harmless empty defaults."""
    return TrackUpdate(
        was_tracked=was_tracked,
        first_point=first_point,
        first_point_world=None,
        last_point=last_point,
        last_point_world=None,
        current_point=current_point,
        current_point_world=None,
        direction_label=direction_label,
        direction_label_world=None,
        speed_px_per_s=speed_px_per_s,
        speed_km_per_h=speed_km_per_h,
        track_id=track_id,
        processed_segments=list(processed_segments),
        processed_segments_world=[],
    )


def _world_update(
    *,
    was_tracked: bool = True,
    first_point_world: WorldPoint | None = None,
    last_point_world: WorldPoint | None = None,
    current_point_world: WorldPoint | None = None,
    direction_label_world: str | None = None,
    speed_km_per_h: float | None = None,
    track_id: int | None = 1,
    processed_segments_world=(),
) -> TrackUpdate:
    """World-view fixture — birdseye tracks project the `*_world` fields into
    grid-space pixel fields internally, so the pixel-space fields on the
    input update itself are irrelevant and left unset."""
    return TrackUpdate(
        was_tracked=was_tracked,
        first_point=None,
        first_point_world=first_point_world,
        last_point=None,
        last_point_world=last_point_world,
        current_point=None,
        current_point_world=current_point_world,
        direction_label=None,
        direction_label_world=direction_label_world,
        speed_px_per_s=None,
        speed_km_per_h=speed_km_per_h,
        track_id=track_id,
        processed_segments=[],
        processed_segments_world=list(processed_segments_world),
    )


def test_directional_track_draws_into_the_requested_direction_bucket() -> None:
    track = _DirectionalTrack("right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="right",
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(2, 2))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_directional_track_only_populates_requested_bucket() -> None:
    # A "down" update shouldn't show up in the "up" track's frame.
    track = _DirectionalTrack("up", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="down",
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(2, 2))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_directional_track_applies_half_life_decay() -> None:
    track = _DirectionalTrack("right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, 1)
    update = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(1, 1),
        current_point=TrackedPoint(2, 2),
        direction_label="right",
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
    update = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(0, 0),
        current_point=TrackedPoint(3, 3),
        direction_label="right",
        speed_px_per_s=5.0,
        speed_km_per_h=5.0,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(3, 3))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == (100, 100)
    assert frame.sum() > 0


def test_speed_track_respects_min_max_bounds() -> None:
    track = _SpeedTrack(10.0, 20.0, _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    too_slow = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(0, 0),
        current_point=TrackedPoint(3, 3),
        direction_label="right",
        speed_px_per_s=1.0,
        speed_km_per_h=1.0,
        processed_segments=[(TrackedPoint(0, 0), TrackedPoint(3, 3))],
    )

    track.handle([too_slow])
    frame = track.frame()

    assert frame.sum() == 0


def test_speed_track_applies_half_life_decay() -> None:
    track = _SpeedTrack(None, None, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, 1)
    update = _camera_update(
        first_point=TrackedPoint(0, 0),
        last_point=TrackedPoint(0, 0),
        current_point=TrackedPoint(3, 3),
        direction_label="right",
        speed_px_per_s=5.0,
        speed_km_per_h=5.0,
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
        _camera_update(current_point=TrackedPoint(10, 10), track_id=track_id)
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
    update = _camera_update(
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
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
    update = _camera_update(
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
        processed_segments=[(TrackedPoint(80, 40), TrackedPoint(85, 45))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_roi_track_draws_into_the_requested_bucket() -> None:
    # Rectangle covering x in [50, 100]; the update below lands inside it.
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiTrack(polygon, "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES)
    update = _camera_update(
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
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
    update = _camera_update(
        first_point=TrackedPoint(80, 40),
        last_point=TrackedPoint(80, 40),
        current_point=TrackedPoint(85, 45),
        direction_label="right",
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


# ---------------------------------------------------------------------------
# World-view (birdseye) tracks — mirror the camera-view tests above, but the
# grid is sized from the calibration/camera dims (see _GRID_SHAPE) rather
# than matching `_METADATA.width`/`_METADATA.height`, and the tracks read the
# `*_world` fields off `TrackUpdate` instead of the pixel fields.
# ---------------------------------------------------------------------------


def test_directional_birdseye_track_draws_into_the_requested_direction_bucket() -> None:
    track = _DirectionalBirdsEyeTrack(
        "right", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    update = _world_update(
        first_point_world=WorldPoint(1, 1),
        last_point_world=WorldPoint(1, 1),
        current_point_world=WorldPoint(5, 3),
        direction_label_world="right",
        processed_segments_world=[(WorldPoint(1, 1), WorldPoint(5, 3))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == _GRID_SHAPE
    assert frame.sum() > 0


def test_directional_birdseye_track_only_populates_requested_bucket() -> None:
    track = _DirectionalBirdsEyeTrack(
        "up", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    update = _world_update(
        first_point_world=WorldPoint(1, 1),
        last_point_world=WorldPoint(1, 1),
        current_point_world=WorldPoint(5, 3),
        direction_label_world="right",
        processed_segments_world=[(WorldPoint(1, 1), WorldPoint(5, 3))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_speed_birdseye_track_uses_km_per_h() -> None:
    track = _SpeedBirdsEyeTrack(
        None, None, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    update = _world_update(
        first_point_world=WorldPoint(1, 1),
        last_point_world=WorldPoint(1, 1),
        current_point_world=WorldPoint(5, 3),
        direction_label_world="right",
        speed_km_per_h=5.0,
        processed_segments_world=[(WorldPoint(1, 1), WorldPoint(5, 3))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == _GRID_SHAPE
    assert frame.sum() > 0


def test_speed_birdseye_track_respects_min_max_bounds() -> None:
    track = _SpeedBirdsEyeTrack(
        10.0, 20.0, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    too_slow = _world_update(
        first_point_world=WorldPoint(1, 1),
        last_point_world=WorldPoint(1, 1),
        current_point_world=WorldPoint(5, 3),
        direction_label_world="right",
        speed_km_per_h=1.0,
        processed_segments_world=[(WorldPoint(1, 1), WorldPoint(5, 3))],
    )

    track.handle([too_slow])
    frame = track.frame()

    assert frame.sum() == 0


def test_cluster_birdseye_track_renders_only_the_requested_group_size() -> None:
    close_pair = [
        _world_update(current_point_world=WorldPoint(7, 3), track_id=track_id)
        for track_id in (1, 2)
    ]

    track_for_2 = _ClusterBirdsEyeTrack(
        2, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    track_for_2.handle(close_pair)
    assert track_for_2.frame().shape == _GRID_SHAPE
    assert track_for_2.frame().sum() > 0

    track_for_3 = _ClusterBirdsEyeTrack(
        3, _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    track_for_3.handle(close_pair)
    assert track_for_3.frame().sum() == 0


def test_roi_birdseye_track_draws_into_the_requested_bucket() -> None:
    # Pixel-space rectangle covering camera x in [50, 100] — same shape as
    # the camera-view ROI test — projects to the right half of the grid.
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiBirdsEyeTrack(
        polygon, "inside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    update = _world_update(
        first_point_world=WorldPoint(12, 2),
        last_point_world=WorldPoint(12, 2),
        current_point_world=WorldPoint(12.75, 2.7),
        direction_label_world="right",
        processed_segments_world=[(WorldPoint(12, 2), WorldPoint(12.75, 2.7))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == _GRID_SHAPE
    assert frame.sum() > 0


def test_roi_birdseye_track_only_populates_requested_bucket() -> None:
    polygon = [(50, 0), (100, 0), (100, 100), (50, 100)]
    track = _RoiBirdsEyeTrack(
        polygon, "outside", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )
    update = _world_update(
        first_point_world=WorldPoint(12, 2),
        last_point_world=WorldPoint(12, 2),
        current_point_world=WorldPoint(12.75, 2.7),
        direction_label_world="right",
        processed_segments_world=[(WorldPoint(12, 2), WorldPoint(12.75, 2.7))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.sum() == 0


def test_tripwire_birdseye_track_draws_into_the_requested_bucket() -> None:
    # Vertical pixel-space line at x=50; inside_point (90, 50) makes camera
    # x > 50 the "inside" half — same setup as the camera-view test.
    track = _TripwireBirdsEyeTrack(
        (50, 0), (50, 100), (90, 50), "inside",
        _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER,
    )
    update = _world_update(
        first_point_world=WorldPoint(12, 2),
        last_point_world=WorldPoint(12, 2),
        current_point_world=WorldPoint(12.75, 2.7),
        direction_label_world="right",
        processed_segments_world=[(WorldPoint(12, 2), WorldPoint(12.75, 2.7))],
    )

    track.handle([update])
    frame = track.frame()

    assert frame.shape == _GRID_SHAPE
    assert frame.sum() > 0


def test_birdseye_track_grid_differs_from_camera_pixel_dimensions() -> None:
    # The whole point of world view: its grid is sized from calibration, not
    # from the source video's own pixel resolution.
    track = _DirectionalBirdsEyeTrack(
        "all", _METADATA, _SETTINGS, _MAX_LOST_FRAMES, _CAMERA_TO_WORLD_MAPPER
    )

    assert track.frame().shape != (_METADATA.height, _METADATA.width)
    assert track.frame().shape == _GRID_SHAPE


def test_resolve_output_dimensions_camera_view_matches_source_resolution() -> None:
    width, height = resolve_output_dimensions(
        "camera", _METADATA, _TRANSFORMATION_MATRIX, _SETTINGS
    )

    assert (width, height) == (_METADATA.width, _METADATA.height)


def test_resolve_output_dimensions_world_view_differs_from_source_resolution() -> None:
    width, height = resolve_output_dimensions(
        "world", _METADATA, _TRANSFORMATION_MATRIX, _SETTINGS
    )

    assert (width, height) == (
        _GRID.width * _SETTINGS.birdseye_display_scale,
        _GRID.height * _SETTINGS.birdseye_display_scale,
    )
    assert (width, height) != (_METADATA.width, _METADATA.height)
