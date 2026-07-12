from __future__ import annotations

from typing import TYPE_CHECKING

from core.heatmap.roi.roi_heatmap import RoiHeatmap
from core.heatmap.roi.roi_heatmap_builder import RoiHeatmapBuilder
from core.momentum.domain import TrackUpdate

if TYPE_CHECKING:
    from core.heatmap.tripwire.tripwire_heatmap_builder import TripwireHeatmapBuilder


class TripwireHeatmap:
    def __init__(self, builder: "TripwireHeatmapBuilder"):
        polygon_points = _compute_tripwire_polygon(
            p1=builder._p1,
            p2=builder._p2,
            inside_point=builder._inside_point,
            width=builder.width,
            height=builder.height,
        )

        roi_builder = (
            RoiHeatmapBuilder()
            .with_height(builder.height)
            .with_width(builder.width)
            .with_frames(builder.frames_count)
            .with_fps(builder.fps)
            .with_polygon(polygon_points)
        )
        if builder.half_life_time is not None:
            roi_builder.with_half_life_time(builder.half_life_time)

        self._roi_heatmap: RoiHeatmap = roi_builder.build()
        self.polygon = polygon_points

    def handle(self, updates: list[TrackUpdate]) -> None:
        self._roi_heatmap.handle(updates)

    def handle_single_update(self, update: TrackUpdate) -> None:
        self._roi_heatmap.handle_single_update(update)

    def execute_track_update_batch(self, updates: list[TrackUpdate]) -> None:
        self._roi_heatmap.execute_track_update_batch(updates)

    def get_heatmap(self):
        return self._roi_heatmap.get_heatmap()

    def apply_decay(self) -> None:
        self._roi_heatmap.apply_decay()

    def get_polygon(self):
        return self.polygon

    def get_tripwire(self):
        return self.polygon[0], self.polygon[-1]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _compute_tripwire_polygon(
    p1: tuple[int, int],
    p2: tuple[int, int],
    inside_point: tuple[int, int],
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    """Extend the line p1-p2 to image borders and build the ROI polygon for the
    half-plane that contains inside_point."""
    e1, e2 = _extend_line_to_borders(p1, p2, width, height)

    corners = [(0, 0), (width, 0), (width, height), (0, height)]

    def _side(pt: tuple[float, float]) -> float:
        """Signed area / cross product: positive = left of p1→p2, negative = right."""
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return dx * (pt[1] - p1[1]) - dy * (pt[0] - p1[0])

    inside_sign = _side(inside_point)
    inside_corners = [c for c in corners if _side(c) * inside_sign > 0]

    # Order all candidate points (E1, inside corners, E2) by clockwise perimeter
    # position so they form a valid (non-self-intersecting) polygon.
    def _perimeter_param(pt: tuple[float, float]) -> float:
        x, y = pt
        if abs(y) < 1e-9:
            return x / width                    # top edge  [0, 1)
        if abs(x - width) < 1e-9:
            return 1.0 + y / height             # right edge [1, 2)
        if abs(y - height) < 1e-9:
            return 2.0 + (width - x) / width   # bottom edge [2, 3)
        return 3.0 + (height - y) / height      # left edge  [3, 4)

    e1_param = _perimeter_param(e1)
    e2_param = _perimeter_param(e2)

    # Walk clockwise from e1 to e2, collecting inside corners in between.
    def _between_cw(param: float) -> bool:
        if e1_param <= e2_param:
            return e1_param < param < e2_param
        return param > e1_param or param < e2_param

    arc_corners = sorted(
        [c for c in inside_corners if _between_cw(_perimeter_param(c))],
        key=_perimeter_param,
    )

    # If the clockwise arc from e1 to e2 does NOT contain the inside corners,
    # the inside half is on the other (counter-clockwise) arc — reverse the walk.
    if not arc_corners and inside_corners:
        def _between_ccw(param: float) -> bool:
            if e2_param <= e1_param:
                return e2_param < param < e1_param
            return param > e2_param or param < e1_param

        # Sort by distance going backwards (CCW) from e1
        arc_corners = sorted(
            [c for c in inside_corners if _between_ccw(_perimeter_param(c))],
            key=lambda c: (e1_param - _perimeter_param(c)) % 4,
        )

    polygon: list[tuple[int, int]] = (
        [_to_int(e1)] + [_to_int(c) for c in arc_corners] + [_to_int(e2)]
    )
    return polygon


def _extend_line_to_borders(
    p1: tuple[int, int],
    p2: tuple[int, int],
    width: int,
    height: int,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return the two points where the infinite line through p1 and p2 intersects
    the image border rectangle."""
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    dx, dy = x2 - x1, y2 - y1

    candidates: list[tuple[float, tuple[float, float]]] = []

    if abs(dx) > 1e-9:
        # Left border x=0
        t = -x1 / dx
        y = y1 + t * dy
        if 0 <= y <= height:
            candidates.append((t, (0.0, y)))
        # Right border x=width
        t = (width - x1) / dx
        y = y1 + t * dy
        if 0 <= y <= height:
            candidates.append((t, (float(width), y)))

    if abs(dy) > 1e-9:
        # Top border y=0
        t = -y1 / dy
        x = x1 + t * dx
        if 0 <= x <= width:
            candidates.append((t, (x, 0.0)))
        # Bottom border y=height
        t = (height - y1) / dy
        x = x1 + t * dx
        if 0 <= x <= width:
            candidates.append((t, (x, float(height))))

    # Deduplicate (corners can appear twice) and sort by t
    unique: list[tuple[float, tuple[float, float]]] = []
    for t, pt in sorted(candidates, key=lambda c: c[0]):
        if not any(abs(pt[0] - u[1][0]) < 1e-6 and abs(pt[1] - u[1][1]) < 1e-6 for u in unique):
            unique.append((t, pt))

    if len(unique) < 2:
        raise ValueError(
            f"Line through {p1} and {p2} does not cross the image border at two distinct points."
        )

    return unique[0][1], unique[-1][1]


def _to_int(pt: tuple[float, float] | tuple[int, int]) -> tuple[int, int]:
    return (int(round(pt[0])), int(round(pt[1])))
