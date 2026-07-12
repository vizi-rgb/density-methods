from collections import defaultdict, deque
from typing import Callable, Counter, Dict, Generic, TypeVar

T = TypeVar("T")


class SmartTrackedPointBuffer(Generic[T]):
    def __init__(self, factory: Callable[[], T] = deque, max_lost_frames: int = 10):
        self.max_lost_frames: int = max_lost_frames
        self.id_pos_tracker: Dict[int, T] = defaultdict(factory)
        self.lost_frames_counter: Dict[int, int] = Counter()
        self.updated_track_ids: set[int] = set()

    def update(self, track_id: int, current) -> None:
        self.lost_frames_counter[track_id] = 0
        self.id_pos_tracker[track_id].append(current)
        self.updated_track_ids.add(track_id)

    def get(self, track_id: int) -> T:
        return self.id_pos_tracker[track_id]

    def next_frame(self):
        lost_frames_set = set(self.lost_frames_counter.keys())
        tracks_to_check_for_flush = lost_frames_set - self.updated_track_ids

        for track_id in tracks_to_check_for_flush:
            self.lost_frames_counter[track_id] += 1

            if self.lost_frames_counter[track_id] > self.max_lost_frames:
                self.lost_frames_counter.pop(track_id)
                self.id_pos_tracker.pop(track_id)

        self.updated_track_ids.clear()
