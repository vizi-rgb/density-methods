from collections import deque, Counter
from typing import Dict, Deque, List, Tuple, Set

import numpy as np

from core.momentum.camera_to_world_mapper import CameraToWorldMapper
from core.momentum.direction import DirectionUtil
from core.momentum.domain import TrackedPoint, TrackUpdate, WorldPoint
from core.momentum.speed import SpeedUtil


def _should_be_tracked(track_id: int) -> bool:
    return track_id != 0


class MomentumTracker:
    def __init__(
        self, fps: int, momentum_buffer_size: int, max_lost_frames: int = 10, camera_world_mapper: CameraToWorldMapper | None = None
    ) -> None:
        self.fps: int = fps
        self.momentum_buffer_size: int = momentum_buffer_size
        self.max_lost_frames: int = max_lost_frames
        self.id_pos_tracker: Dict[int, Deque[TrackedPoint]] = dict()
        self.id_speed_tracker: Dict[int, Deque[float]] = dict()
        self.lost_frames_counter: Dict[int, int] = Counter()
        self.get_direction_label = DirectionUtil.get_direction_label
        self.camera_to_world_mapper = camera_world_mapper

    def update_batch(
        self, track_ids: list[int], current_pos_list: list[TrackedPoint]
    ) -> List[TrackUpdate]:
        if self.camera_to_world_mapper:
            current_pos_list_to_world = self.camera_to_world_mapper.map_batch(current_pos_list)
            return [
                self.update(track_id, point, real_world_point)
                for track_id, point, real_world_point in zip(track_ids, current_pos_list, current_pos_list_to_world)
            ]

        return [
            self.update(track_id, point, None)
            for track_id, point in zip(track_ids, current_pos_list)
        ]

    def update(self, track_id: int, current_pos: TrackedPoint, current_world_pos: WorldPoint | None) -> TrackUpdate:
        if not _should_be_tracked(track_id):
            return TrackUpdate(
                was_tracked=False,
                first_point=None,
                first_point_world=None,
                last_point=None,
                last_point_world=None,
                current_point=None,
                current_point_world=None,
                direction_label=None,
                direction_label_world=None,
                speed_px_per_s=None,
                speed_km_per_h=None,
                processed_segments=[],
                processed_segments_world=[],
                track_id=track_id,
            )

        if not self.is_id_tracked(track_id):
            self.id_pos_tracker[track_id] = deque(maxlen=self.momentum_buffer_size)
            self.id_speed_tracker[track_id] = deque(maxlen=self.momentum_buffer_size)

        history = self.id_pos_tracker[track_id]
        if len(history) == 0:
            history.append(current_pos)
            return TrackUpdate(
                was_tracked=False,
                first_point=None,
                first_point_world=None,
                last_point=None,
                last_point_world=None,
                current_point=current_pos,
                current_point_world=current_world_pos,
                direction_label=None,
                direction_label_world=None,
                speed_px_per_s=None,
                speed_km_per_h=None,
                processed_segments=[],
                processed_segments_world=[],
                track_id=track_id,
            )

        first_point = history[0]
        last_point = history[-1]
        frames_cnt = len(history)
        processed_segments: List[Tuple[TrackedPoint, TrackedPoint]] = []
        direction: str = self.get_direction_label(first_point, current_pos)
        speed: float = self._get_camera_speed(first_point, current_pos, frames_cnt)
        real_speed: float | None = None
        direction_world: str | None = None

        first_point_world, last_point_world = self.camera_to_world_mapper.map_batch([first_point, last_point]) if self.camera_to_world_mapper else (None, None)

        if current_world_pos and self.camera_to_world_mapper:
            real_speed = self._get_real_speed(first_point_world, current_world_pos, track_id, frames_cnt)
            direction_world = self.get_direction_label(first_point_world, current_world_pos, DirectionUtil.WORLD_STATIC_THRESHOLD)

        history.append(current_pos)
        if len(history) == self.momentum_buffer_size:
            processed_segments = [(last_point, current_pos)]
        elif len(history) == self.momentum_buffer_size - 1:
            processed_segments = self._peek_momentum_buffer(track_id)

        processed_segments_world = self._map_processed_segments_to_processed_segments_world(processed_segments) if self.camera_to_world_mapper else []
        return TrackUpdate(
            was_tracked=True,
            first_point=first_point,
            first_point_world=first_point_world,
            last_point=last_point,
            last_point_world=last_point_world,
            current_point=current_pos,
            current_point_world=current_world_pos,
            direction_label=direction,
            direction_label_world=direction_world,
            speed_px_per_s=speed,
            speed_km_per_h=real_speed,
            processed_segments=processed_segments,
            processed_segments_world=processed_segments_world,
            track_id=track_id,
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

                history = self.id_pos_tracker[track_id]
                were_segments_processed = len(history) >= self.momentum_buffer_size - 1
                if len(history) == 0 or were_segments_processed:
                    self.id_pos_tracker.pop(track_id)
                    self.id_speed_tracker.pop(track_id, None)
                    continue

                first_point, last_point, frames_cnt = (
                    history[0],
                    history[-1],
                    len(history),
                )
                flushed_segments = self.flush_momentum_buffer(track_id)
                direction = self.get_direction_label(first_point, last_point)
                speed = self._get_camera_speed(first_point, last_point, frames_cnt)
                real_speed = None
                direction_world = None
                first_point_world, last_point_world = (None, None)
                if self.camera_to_world_mapper:
                    first_point_world, last_point_world = self.camera_to_world_mapper.map_batch([first_point, last_point])
                    real_speed = self._get_real_speed(first_point_world, last_point_world, track_id, frames_cnt)
                    direction_world = self.get_direction_label(first_point_world, last_point_world, DirectionUtil.WORLD_STATIC_THRESHOLD)

                flushed_segments_world = self._map_processed_segments_to_processed_segments_world(flushed_segments) if self.camera_to_world_mapper else []
                track_updates.append(
                    TrackUpdate(
                        was_tracked=True,
                        first_point=first_point,
                        first_point_world=first_point_world,
                        last_point=last_point,
                        last_point_world=last_point_world,
                        current_point=None,
                        current_point_world=None,
                        direction_label=direction,
                        direction_label_world=direction_world,
                        speed_px_per_s=speed,
                        speed_km_per_h=real_speed,
                        processed_segments=flushed_segments,
                        processed_segments_world=flushed_segments_world,
                        track_id=track_id,
                    )
                )
                self.id_pos_tracker.pop(track_id)
                self.id_speed_tracker.pop(track_id, None)

        return track_updates

    def is_id_tracked(self, track_id: int) -> bool:
        return _should_be_tracked(track_id) and track_id in self.id_pos_tracker

    def flush_momentum_buffer(
        self, track_id: int
    ) -> List[Tuple[TrackedPoint, TrackedPoint]]:
        history = self.id_pos_tracker[track_id]
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
        self, track_id: int
    ) -> List[Tuple[TrackedPoint, TrackedPoint]]:
        history = list(self.id_pos_tracker[track_id])
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
        return list(self.id_pos_tracker[track_id])

    def get_track_first_pos(self, track_id: int) -> TrackedPoint | None:
        if not self.is_id_tracked(track_id):
            return None

        return self.id_pos_tracker[track_id][0]

    def get_track_last_pos(self, track_id: int) -> TrackedPoint | None:
        if not self.is_id_tracked(track_id):
            return None

        return self.id_pos_tracker[track_id][-1]

    def _get_camera_speed(self, p1: TrackedPoint, p2: TrackedPoint, frames_cnt: int):
        return SpeedUtil.get_speed(p1, p2, frames_cnt / self.fps)

    def _get_real_speed(self, p1: WorldPoint, p2: WorldPoint, track_id: int, frames_cnt: int):
        intermediate_real_speed = SpeedUtil.meters_per_s_to_kilometers_per_h(
            SpeedUtil.get_speed(
                p1, p2, frames_cnt / self.fps
            )
        )
        self.id_speed_tracker[track_id].append(intermediate_real_speed)
        return self._get_stabilized_speed(track_id)

    def _get_stabilized_speed(self, track_id: int):
        speed_history = self.id_speed_tracker[track_id]
        return np.median(speed_history)

    def _map_processed_segments_to_processed_segments_world(self, processed_segments: List[Tuple[TrackedPoint, TrackedPoint]]) -> List[Tuple[WorldPoint, WorldPoint]]:
        return [(self.camera_to_world_mapper.map(p1), self.camera_to_world_mapper.map(p2)) for p1, p2 in processed_segments]

