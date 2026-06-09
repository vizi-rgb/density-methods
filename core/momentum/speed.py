import math

from core.momentum.domain import TrackedPoint


class SpeedUtil:

    @classmethod
    def get_speed_px(cls, p1: TrackedPoint, p2: TrackedPoint, dt: float):
        if dt == 0:
            raise ValueError("dt must be greater than 0")

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.hypot(dx, dy) / dt