from collections import defaultdict
from typing import TYPE_CHECKING

from sklearn.cluster import DBSCAN

import numpy as np

from core.momentum.domain import TrackUpdate, TrackedPoint

if TYPE_CHECKING:
    from core.heatmap.clusters.cluster_heatmap_builder import (
        ClusterHeatmapBuilder,
    )


class ClusterHeatmap:
    def __init__(self, builder: "ClusterHeatmapBuilder"):
        self.height = builder.height
        self.width = builder.width
        self.frames_count = builder.frames_count
        self.fps = builder.fps

        if (
                self.height is None
                or self.width is None
                or self.frames_count is None
                or self.fps is None
        ):
            raise ValueError("Builder fields must be set before use.")

        self.frames_processed = 0
        self.heatmap = defaultdict(lambda: np.zeros((self.height, self.width), dtype=np.float32))

        self.intermediate_heatmap = np.zeros(
            (self.height, self.width), dtype=np.float32
        )
        self.clustering = DBSCAN(eps=80, min_samples=2)
        if self.fps and builder.half_life_time:
            self.decay_factor = 0.5 ** (1 / (builder.half_life_time * self.fps))
        else:
            self.decay_factor = None

    def handle(self, updates: list[TrackUpdate]):
        points = np.array(
            [[u.current_point.x, u.current_point.y]
             for u in updates if u.current_point is not None],
            dtype=np.int32,
        )
        if len(points) >= 2:
            labels = self.clustering.fit_predict(points)

            mask = labels != -1
            valid_pts = points[mask]
            valid_labels = labels[mask]

            unique_labels, counts = np.unique(valid_labels, return_counts=True)

            clusters_by_size: dict[int, list] = defaultdict(list)
            for label, count in zip(unique_labels, counts):
                clusters_by_size[int(count)].extend(valid_pts[valid_labels == label].tolist())

            for cluster_size in clusters_by_size:
                for point in clusters_by_size[cluster_size]:
                    self._update_point_heatmap(TrackedPoint(point[0], point[1]), f"{cluster_size}")

        self.frames_processed += 1

    def get_heatmap(self):
        return self.heatmap

    def _update_point_heatmap(
            self,
            point: TrackedPoint,
            direction_label: str
    ):
        self.heatmap[direction_label][point.y, point.x] += 1
