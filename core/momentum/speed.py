import math

from core.momentum.domain import TrackedPoint


class SpeedUtil:
    MS_TO_KMH = 3.6

    @classmethod
    def get_speed(cls, p1: TrackedPoint, p2: TrackedPoint, dt: float):
        if dt == 0:
            raise ValueError("dt must be greater than 0")

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.hypot(dx, dy) / dt

    @classmethod
    def meters_per_s_to_kilometers_per_h(cls, speed_in_ms: float):
        return speed_in_ms * cls.MS_TO_KMH
