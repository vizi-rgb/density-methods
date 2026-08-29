from dataclasses import dataclass
from typing import NamedTuple, List, Tuple


class TrackedPoint(NamedTuple):
    x: int
    y: int


@dataclass(frozen=True)
class TrackUpdate:
    was_tracked: bool
    first_point: TrackedPoint | None
    first_point_world: TrackedPoint | None
    last_point: TrackedPoint | None
    last_point_world: TrackedPoint | None
    current_point: TrackedPoint | None
    current_point_world: TrackedPoint | None
    direction_label: str | None
    speed_px_per_s: float | None
    speed_km_per_h: float | None
    track_id: int | None

    # emits when particular segments are processed, so when an appropriate update should happen in handlers
    # this is to ensure that noise does not affect the evaluated metrics
    processed_segments: List[Tuple[TrackedPoint, TrackedPoint]]
    processed_segments_world: List[Tuple[TrackedPoint, TrackedPoint]]
