import math

from core.adapter.domain import Point
from core.momentum.domain import TrackedPoint


class PointUtil:
    @staticmethod
    def clamp_points_to_heatmap_points(points: list[Point], width: int, height: int):
        return [
            PointUtil.clamp_point_to_heatmap_point(point, width, height)
            for point in points
        ]

    @staticmethod
    def clamp_point_to_heatmap_point(
        point: Point, width: int, height: int
    ) -> TrackedPoint:
        return TrackedPoint(
            x=min(max(math.floor(point.x), 0), width - 1),
            y=min(max(math.floor(point.y), 0), height - 1),
        )
