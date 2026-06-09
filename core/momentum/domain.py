from dataclasses import dataclass
from typing import NamedTuple, List, Tuple


class TrackedPoint(NamedTuple):
    x: int
    y: int


@dataclass(frozen=True)
class TrackUpdate:
    was_tracked: bool
    first_point: TrackedPoint | None
    last_point: TrackedPoint | None
    current_point: TrackedPoint | None
    direction_label: str | None
    speed: float | None
    processed_segments: List[Tuple[TrackedPoint, TrackedPoint]]
