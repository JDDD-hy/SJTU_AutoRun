"""Offline distance checks using synthetic coordinates, without emulator access."""
from copy import deepcopy

from sjtuautorun.utils.math_functions import calculate_geo_distance
from sjtuautorun.utils.route_distance import route_for_distance


def distance(points):
    return sum(calculate_geo_distance(a[1], a[0], b[1], b[0]) for a, b in zip(points, points[1:]))


def main():
    points = [[0, 0], [0, 0], [0.01, 0], [0.01, 0.01], [0, 0]]
    saved = deepcopy(points)
    original_distance = distance(points)
    for target in (1, 100, original_distance, 4050, 4173, 4300):
        adjusted = route_for_distance(points, target)
        assert abs(distance(adjusted) - target) < 0.01
        assert points == saved and adjusted[0] == points[0]
        if target > original_distance:
            assert adjusted[:len(points) - 1] == points[:1] + points[2:]
        adjusted[0][0] = 1
        assert points == saved
    for invalid_points, target in ((points, 0), (points, -1), (points, float("nan")),
                                   (points, float("inf")), (points, 2 * original_distance + 100),
                                   ([], 100), ([[0, 0]], 100), ([[0, 0], [0, 0]], 100)):
        try:
            route_for_distance(invalid_points, target)
        except ValueError:
            pass
        else:
            raise AssertionError((invalid_points, target))
    print("PASS: trimming, retracing, distance bounds, duplicate points, and unchanged source coordinates.")


if __name__ == "__main__":
    main()
