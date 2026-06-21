from core.heatmap.speed.speed_filter import SpeedFilter
from core.momentum.domain import TrackUpdate


class SpeedFilterChain:
    def __init__(self, filters: list[SpeedFilter]) -> None:
        self._filters = filters

    def evaluate(self, track_update: TrackUpdate) -> list[str]:
        return [
            f.name for f in self._filters if f.test(f.get_speed_function(track_update))
        ]

    def filter_names(self) -> list[str]:
        return [f.name for f in self._filters]

    def filters(self) -> list[SpeedFilter]:
        return self._filters
