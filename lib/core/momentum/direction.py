import math
from enum import Enum

from core.momentum.domain import TrackedPoint


class Direction(Enum):
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    STATIC = "static"


class DirectionUtil:
    STATIC_THRESHOLD = 5
    WORLD_STATIC_THRESHOLD = 0.05

    @classmethod
    def get_direction_label(cls, p1: TrackedPoint, p2: TrackedPoint, static_threshold: float | None = None):
        threshold = cls.STATIC_THRESHOLD if static_threshold is None else static_threshold
        dx = p2.x - p1.x
        dy = p2.y - p1.y

        if math.hypot(dx, dy) < threshold:
            return Direction.STATIC.value

        angle = math.degrees(math.atan2(-dy, dx))
        if angle < 0:
            angle += 360

        if 45 <= angle < 135:
            return Direction.UP.value
        elif 135 <= angle < 225:
            return Direction.LEFT.value
        elif 225 <= angle < 315:
            return Direction.DOWN.value
        else:
            return Direction.RIGHT.value
