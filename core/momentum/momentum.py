from collections import deque, Counter
from typing import Dict, Deque, List, Tuple, Set

from core.momentum.direction import DirectionUtil
from core.momentum.domain import TrackedPoint, TrackUpdate
from core.momentum.speed import SpeedUtil


def _should_be_tracked(track_id: int) -> bool:
    return track_id != 0


class MomentumTracker:
    def __init__(self, fps: int, momentum_buffer_size: int, max_lost_frames: int = 10) -> None:
        self.fps: int = fps
        self.momentum_buffer_size: int = momentum_buffer_size
        self.max_lost_frames: int = max_lost_frames
        self.id_tracker: Dict[int, Deque[TrackedPoint]] = dict()
        self.lost_frames_counter: Dict[int, int] = Counter()
        self.get_direction_label = DirectionUtil.get_direction_label
        self.get_speed = SpeedUtil.get_speed_px

    def update(self, track_id: int, current_pos: TrackedPoint) -> TrackUpdate:
        if not _should_be_tracked(track_id):
            return TrackUpdate(
                was_tracked=False,
                first_point=None,
                last_point=None,
                current_point=None,
                direction_label=None,
                speed=None,
                processed_segments=[],
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
                first_point=None,
                last_point=None,
                current_point=current_pos,
                direction_label=None,
                speed=None,
                processed_segments=[],
            )

        first_point = history[0]
        last_point = history[-1]
        processed_segments: List[Tuple[TrackedPoint, TrackedPoint]] = []
        direction: str = self.get_direction_label(first_point, current_pos)
        speed: float = self.get_speed(first_point, current_pos, self.momentum_buffer_size / self.fps)

        history.append(current_pos)
        if len(history) == self.momentum_buffer_size:
            processed_segments = [(last_point, current_pos)]
        elif len(history) == self.momentum_buffer_size - 1:
            processed_segments = self._peek_momentum_buffer(track_id)

        return TrackUpdate(
            was_tracked=True,
            first_point=first_point,
            last_point=last_point,
            current_point=current_pos,
            direction_label=direction,
            speed=speed,
            processed_segments=processed_segments,
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
                were_segments_processed = len(history) >= self.momentum_buffer_size - 1
                if len(history) == 0 or were_segments_processed:
                    self.id_tracker.pop(track_id)
                    continue

                first_point, second_point, frames_cnt = history[0], history[-1], len(history)
                flushed_segments = self.flush_momentum_buffer(track_id)
                direction = self.get_direction_label(first_point, second_point)
                speed = self.get_speed(first_point, second_point, frames_cnt / self.fps)
                track_updates.append(TrackUpdate(
                    was_tracked=True,
                    first_point=first_point,
                    last_point=second_point,
                    current_point=None,
                    direction_label=direction,
                    speed=speed,
                    processed_segments=flushed_segments,
                ))
                self.id_tracker.pop(track_id)

        return track_updates

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

    def _peek_momentum_buffer(
            self,
            track_id: int
    ) -> List[Tuple[TrackedPoint, TrackedPoint]]:
        history = list(self.id_tracker[track_id])
        if len(history) < 1:
            return []

        peeked_segments = []
        first = history[0]
        for i in range(len(history) - 1):
            first = history[i]
            second = history[i + 1]
            peeked_segments.append((first, second))

        return [(first, first)] if len(peeked_segments) == 0 else peeked_segments

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