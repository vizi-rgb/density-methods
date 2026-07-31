from dataclasses import dataclass, field

import numpy as np


@dataclass
class Point:
    x: float
    y: float
    track_id: int = 0


@dataclass
class Prediction:
    points: list[Point] = field(default_factory=list)
    image: np.ndarray = None
