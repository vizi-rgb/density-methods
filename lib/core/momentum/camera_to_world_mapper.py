import cv2
import numpy as np

from core.momentum.domain import TrackedPoint, WorldPoint


class CameraToWorldMapper:
    def __init__(self, transformation_matrix: np.ndarray):
        self.M = transformation_matrix

    def map(self, p: TrackedPoint) -> WorldPoint:
        result = cv2.perspectiveTransform(np.array(p, dtype=np.float32).reshape(-1, 1, 2), self.M).reshape(-1, 2)
        return WorldPoint(*result[0])

    def map_batch(self, p: list[TrackedPoint]) -> list[WorldPoint]:
        result = cv2.perspectiveTransform(np.array(p, dtype=np.float32).reshape(-1, 1, 2), self.M).reshape(-1, 2)
        return [WorldPoint(*row) for row in result]