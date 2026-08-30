from __future__ import annotations

import dataclasses
from typing import List, Tuple, TYPE_CHECKING

from core.momentum.domain import TrackedPoint, TrackUpdate, WorldPoint

if TYPE_CHECKING:
    from core.heatmap.birdseye.birds_eye_view_heatmap_builder import BirdsEyeViewHeatmapBuilder


class BirdsEyeViewHeatmap:
    """Shared geometry + world-to-grid projection base for the birds-eye-view heatmap
    types. Not a heatmap type on its own — it has no bucket state or handle()."""

    def __init__(self, builder: "BirdsEyeViewHeatmapBuilder"):
        self.camera_to_world_mapper = builder.camera_to_world_mapper
        self.granularity = builder.granularity

        origin, x_edge = self.camera_to_world_mapper.map_batch([(0, 0), (builder.width, 0)])
        _, y_edge = self.camera_to_world_mapper.map_batch([(0, 0), (0, builder.height)])
        world_width = abs(x_edge.x - origin.x)
        world_height = abs(y_edge.y - origin.y)

        self.scale = builder.width / world_width
        self.offset = (origin.x, origin.y)
        self.width = 2 * max(int(world_width * self.scale / 2), 1)
        self.height = 2 * max(int(world_height * self.scale / 2), 1)

    def _project_point(self, point: WorldPoint | None) -> TrackedPoint | None:
        if point is None:
            return None

        grid_x = round((point.x - self.offset[0]) * self.scale)
        grid_y = round((point.y - self.offset[1]) * self.scale)
        grid_x = min(max(grid_x, 0), self.width - 1)
        grid_y = min(max(grid_y, 0), self.height - 1)
        return TrackedPoint(grid_x, grid_y)

    def _project_segments(
        self, segments: List[Tuple[WorldPoint, WorldPoint]]
    ) -> List[Tuple[TrackedPoint, TrackedPoint]]:
        return [(self._project_point(p1), self._project_point(p2)) for p1, p2 in segments]

    def _project_update(self, update: TrackUpdate) -> TrackUpdate:
        return dataclasses.replace(
            update,
            first_point=self._project_point(update.first_point_world),
            last_point=self._project_point(update.last_point_world),
            current_point=self._project_point(update.current_point_world),
            direction_label=update.direction_label_world,
            processed_segments=self._project_segments(update.processed_segments_world),
        )

    def _project_polygon(self, pixel_points: list[tuple[int, int]]) -> list[tuple[int, int]]:
        world_points = self.camera_to_world_mapper.map_batch(pixel_points)
        return [self._project_point(point) for point in world_points]
