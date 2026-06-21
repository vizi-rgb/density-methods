from typing import Callable

from core.momentum.domain import TrackUpdate


class SpeedFilter:
    def __init__(
        self,
        name: str,
        get_speed_function: Callable[[TrackUpdate], float | None],
        min_speed: float = 0.0,
        max_speed: float = float("inf"),
    ) -> None:
        self.name = name
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.get_speed_function = get_speed_function

    def test(self, speed: float | None) -> bool:
        if speed is None:
            return False
        return self.min_speed <= speed <= self.max_speed
