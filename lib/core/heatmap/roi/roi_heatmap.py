from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

import cv2
import numpy as np

from core.helpers.smart_tracked_point_buffer import SmartTrackedPointBuffer
from core.momentum.domain import TrackedPoint, TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.roi.roi_heatmap_builder import RoiHeatmapBuilder

EPS = 0.01


class RoiHeatmap:
    def __init__(self, builder: "RoiHeatmapBuilder"):
        self.height = builder.height
        self.width = builder.width
        self.frames_count = builder.frames_count
        self.fps = builder.fps
        self.polygon = builder.polygon

        if (
            self.height is None
            or self.width is None
            or self.frames_count is None
            or self.polygon is None
        ):
            raise ValueError("Builder fields must be set before use.")

        self.frames_processed = 0
        self.heatmap = {
            "inside": np.zeros((self.height, self.width), dtype=np.float32),
            "outside": np.zeros((self.height, self.width), dtype=np.float32),
            "inside->outside": np.zeros((self.height, self.width), dtype=np.float32),
            "outside->inside": np.zeros((self.height, self.width), dtype=np.float32),
        }
        self.intermediate_heatmap = np.zeros(
            (self.height, self.width), dtype=np.float32
        )

        # Stores TrackedPoints accumulated since the start of the current region phase.
        self._phase_buffer: SmartTrackedPointBuffer[deque[TrackedPoint]] = SmartTrackedPointBuffer(
            factory=deque
        )
        # Stores (current_label, active_transition) for each track_id.
        self._state_buffer: SmartTrackedPointBuffer[deque[tuple[str | None, str | None]]] = SmartTrackedPointBuffer(
            factory=lambda: deque(maxlen=1)
        )

        if self.fps and builder.half_life_time:
            self.decay_factor = 0.5 ** (1 / (builder.half_life_time * self.fps))
        else:
            self.decay_factor = None

    def handle(self, updates: list[TrackUpdate]):
        for update in updates:
            self.handle_single_update(update)
        self._phase_buffer.next_frame()
        self._state_buffer.next_frame()
        self.frames_processed += 1

    def handle_single_update(self, update: TrackUpdate):
        if not update.was_tracked and update.current_point is not None:
            self._update_point_heatmap(update.current_point)
            return

        if (
            update.first_point is None
            or update.last_point is None
            or update.current_point is None
        ):
            raise RuntimeError("MomentumTracker returned incomplete track update.")

        first_point, second_point = update.last_point, update.current_point
        label = self._classify_point(second_point)
        self._draw_line(self.heatmap[label], first_point, second_point)
        self._handle_roi_transition(update.track_id, update.last_point, update.current_point)

    def _handle_roi_transition(
        self,
        track_id: int | None,
        last_point: TrackedPoint,
        current_point: TrackedPoint,
    ) -> None:
        current_label = self._classify_point(current_point)
        self._draw_line(self.heatmap[current_label], last_point, current_point)

        if track_id is None:
            return

        state_deque = self._state_buffer.id_pos_tracker[track_id]
        last_label, active_transition = state_deque[0] if state_deque else (None, None)

        if last_label is not None and last_label != current_label:
            # Transition detected: retroactively draw entire A phase to A->B heatmap.
            transition_key = f"{last_label}->{current_label}"
            phase_pts = list(self._phase_buffer.id_pos_tracker[track_id])
            self._draw_lines_through(self.heatmap[transition_key], phase_pts + [current_point])
            # Reset phase buffer — new phase starts from current point.
            self._phase_buffer.id_pos_tracker[track_id].clear()
            active_transition = transition_key
        elif active_transition is not None:
            # Still in same region; continue drawing to the active transition heatmap.
            phase_pts = self._phase_buffer.id_pos_tracker[track_id]
            if phase_pts:
                self._draw_line(self.heatmap[active_transition], phase_pts[-1], current_point)

        self._phase_buffer.update(track_id, current_point)
        self._state_buffer.update(track_id, (current_label, active_transition))

    def execute_track_update_batch(self, updates: list[TrackUpdate]):
        raise NotImplementedError("ROI heatmap updates its internals per frame so it shouldn't handle lost frames")

    def get_heatmap(self):
        return self.heatmap

    def get_polygon(self):
        return self.polygon

    def apply_decay(self):
        if self.decay_factor:
            self._apply_decay()

    def _classify_point(self, point: TrackedPoint) -> str:
        result = cv2.pointPolygonTest(
            self.polygon, (float(point.x), float(point.y)), measureDist=False
        )
        return "inside" if result >= 0 else "outside"

    def _update_point_heatmap(self, point: TrackedPoint):
        label = self._classify_point(point)
        self.heatmap[label][point.y, point.x] += 1

    def _draw_line(self, heatmap: np.ndarray, p1: TrackedPoint, p2: TrackedPoint):
        cv2.line(self.intermediate_heatmap, p1, p2, 1, 1)
        heatmap += self.intermediate_heatmap
        cv2.line(self.intermediate_heatmap, p1, p2, 0, 1)

    def _draw_lines_through(self, heatmap: np.ndarray, points: list[TrackedPoint]):
        if not points:
            return
        if len(points) == 1:
            heatmap[points[0].y, points[0].x] += 1
            return
        for i in range(len(points) - 1):
            self._draw_line(heatmap, points[i], points[i + 1])

    def _apply_decay(self):
        for key in self.heatmap:
            self.heatmap[key] *= self.decay_factor
            self.heatmap[key][self.heatmap[key] < EPS] = 0.0
