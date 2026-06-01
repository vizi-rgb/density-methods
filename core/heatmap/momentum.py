from collections import deque, Counter
from dataclasses import dataclass
from typing import NamedTuple, Dict, Deque, List, Tuple, Set

class TrackedPoint(NamedTuple):
    x: int
    y: int


@dataclass(frozen=True)
class TrackUpdate:
    was_tracked: bool
    buffer_full: bool
    first_point: TrackedPoint | None
    last_point: TrackedPoint | None
    flushed_segments: List[Tuple[TrackedPoint, TrackedPoint]]


def _should_be_tracked(track_id: int) -> bool:
    return track_id != 0


class MomentumTracker:
    def __init__(self, momentum_buffer_size: int, max_lost_frames: int = 10) -> None:
        self.momentum_buffer_size: int = momentum_buffer_size
        self.max_lost_frames: int = max_lost_frames
        self.id_tracker: Dict[int, Deque[TrackedPoint]] = dict()
        self.lost_frames_counter: Dict[int, int] = Counter()

    def is_id_tracked(self, track_id: int) -> bool:
        return _should_be_tracked(track_id) and track_id in self.id_tracker

    def flush_momentum_buffer(
        self,
        track_id: int
    ) -> List[Tuple[TrackedPoint, TrackedPoint]]:
        history = self.id_tracker[track_id]
        if len(history) < 1:
            return []

        flushed_segments = []
        first = history.popleft()
        while history:
            second = history.popleft()
            flushed_segments.append((first, second))
            first = second

        return [(first, first)] if len(flushed_segments) == 0 else flushed_segments

    def get_track_history(self, track_id: int) -> List[TrackedPoint]:
        return list(self.id_tracker[track_id])

    def get_track_first_pos(self, track_id: int) -> TrackedPoint | None:
        if not self.is_id_tracked(track_id):
            return None

        return self.id_tracker[track_id][0]

    def get_track_last_pos(self, track_id: int) -> TrackedPoint | None:
        if not self.is_id_tracked(track_id):
            return None

        return self.id_tracker[track_id][-1]

    def update(self, track_id: int, current_pos: TrackedPoint) -> TrackUpdate:
        if not _should_be_tracked(track_id):
            return TrackUpdate(
                was_tracked=False,
                buffer_full=False,
                first_point=None,
                last_point=None,
                flushed_segments=[],
            )

        if not self.is_id_tracked(track_id):
            self.id_tracker[track_id] = deque(
                maxlen=self.momentum_buffer_size
            )

        history = self.id_tracker[track_id]
        if len(history) == 0:
            history.append(current_pos)
            return TrackUpdate(
                was_tracked=False,
                buffer_full=False,
                first_point=None,
                last_point=None,
                flushed_segments=[],
            )

        buffer_full = len(history) == self.momentum_buffer_size
        first_point = history[0]
        last_point = history[-1]
        flushed_segments: List[Tuple[TrackedPoint, TrackedPoint]] = []

        if buffer_full:
            flushed_segments = self.flush_momentum_buffer(track_id)

        history.append(current_pos)

        return TrackUpdate(
            was_tracked=True,
            buffer_full=buffer_full,
            first_point=first_point,
            last_point=last_point,
            flushed_segments=flushed_segments,
        )

    def flush_lost_tracks_buffers(self, current_track_ids: Set[int]):
        lost_frames_set = set(self.lost_frames_counter.keys())
        tracks_to_check_for_flush = lost_frames_set - current_track_ids
        track_updates: List[TrackUpdate] = []

        for track_id in current_track_ids:
            self.lost_frames_counter[track_id] = 0

        for track_id in tracks_to_check_for_flush:
            self.lost_frames_counter[track_id] += 1

            if self.lost_frames_counter[track_id] > self.max_lost_frames:
                self.lost_frames_counter.pop(track_id)

                history = self.id_tracker[track_id]
                if len(history) == 0:
                    self.id_tracker.pop(track_id)
                    continue

                first_point, second_point = history[0], history[-1]
                flushed_segments = self.flush_momentum_buffer(track_id)
                track_updates.append(TrackUpdate(
                    was_tracked=True,
                    buffer_full=False,
                    first_point=first_point,
                    last_point=second_point,
                    flushed_segments=flushed_segments,
                ))
                self.id_tracker.pop(track_id)

        return track_updates
