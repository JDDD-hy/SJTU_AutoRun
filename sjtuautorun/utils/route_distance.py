"""Adjust a coordinate route to a planned distance without changing its source."""
import math
from itertools import chain

from sjtuautorun.utils.math_functions import calculate_geo_distance


def route_for_distance(points, target_meters):
    """Follow the route, then retrace it if necessary, stopping at the target."""
    if not math.isfinite(target_meters) or target_meters <= 0:
        raise ValueError("Target distance must be positive and finite")
    if len(points) < 2:
        raise ValueError("At least two route points are required")
    adjusted = [list(points[0])]
    remaining = target_meters
    for end in chain(points[1:], points[-2::-1]):
        start = adjusted[-1]
        length = calculate_geo_distance(start[1], start[0], end[1], end[0])
        if length == 0:
            continue
        if remaining <= length:
            ratio = remaining / length
            adjusted.append([a + (b - a) * ratio for a, b in zip(start, end)])
            return adjusted
        adjusted.append(list(end))
        remaining -= length
    raise ValueError("Target distance exceeds the route plus one retracing")
