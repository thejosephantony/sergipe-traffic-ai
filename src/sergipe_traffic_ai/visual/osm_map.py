from __future__ import annotations

import math
import unicodedata
from typing import Any


EARTH_METERS_PER_DEGREE_LAT = 110_540.0
EARTH_METERS_PER_DEGREE_LON = 111_320.0


def normalize_road_name(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().strip().split())


def classify_pilot_axis(name: str | None) -> str | None:
    normalized = normalize_road_name(name)

    if "augusto franco" in normalized or "rio de janeiro" in normalized:
        return "augusto"

    if "maynard" in normalized or "barao de maruim" in normalized:
        return "barao"

    return None


def local_xy_m(
    longitude: float,
    latitude: float,
    reference_longitude: float,
    reference_latitude: float,
) -> tuple[float, float]:
    latitude_radians = math.radians(reference_latitude)
    x_m = (
        longitude - reference_longitude
    ) * EARTH_METERS_PER_DEGREE_LON * math.cos(latitude_radians)
    y_m = (
        latitude - reference_latitude
    ) * EARTH_METERS_PER_DEGREE_LAT
    return x_m, y_m


def _principal_axis(points: list[tuple[float, float]]) -> tuple[float, float]:
    if len(points) < 2:
        return 1.0, 0.0

    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)

    xx = sum((point[0] - mean_x) ** 2 for point in points)
    yy = sum((point[1] - mean_y) ** 2 for point in points)
    xy = sum(
        (point[0] - mean_x) * (point[1] - mean_y)
        for point in points
    )

    angle = 0.5 * math.atan2(2.0 * xy, xx - yy)
    return math.cos(angle), math.sin(angle)


def _nearest_midpoint(
    first: list[tuple[float, float]],
    second: list[tuple[float, float]],
    fallback: tuple[float, float],
) -> tuple[float, float]:
    if not first or not second:
        return fallback

    best_distance = math.inf
    best_pair: tuple[tuple[float, float], tuple[float, float]] | None = None

    for first_point in first:
        for second_point in second:
            distance = (
                (first_point[0] - second_point[0]) ** 2
                + (first_point[1] - second_point[1]) ** 2
            )
            if distance < best_distance:
                best_distance = distance
                best_pair = (first_point, second_point)

    if best_pair is None:
        return fallback

    return (
        (best_pair[0][0] + best_pair[1][0]) / 2.0,
        (best_pair[0][1] + best_pair[1][1]) / 2.0,
    )


def road_width_for_highway(highway: str | None) -> int:
    return {
        "motorway": 7,
        "trunk": 7,
        "primary": 6,
        "secondary": 5,
        "tertiary": 4,
        "residential": 3,
        "unclassified": 3,
        "service": 2,
    }.get(str(highway or ""), 2)


def build_osm_map_context(
    geojson: dict[str, Any],
    scenario: dict[str, Any],
    width: int,
    top: int,
    bottom: int,
    padding: int = 32,
) -> dict[str, Any]:
    reference = scenario["scenario"]["location"]["reference_point"]
    reference_latitude = float(reference["latitude"])
    reference_longitude = float(reference["longitude"])

    local_roads: list[dict[str, Any]] = []
    all_points: list[tuple[float, float]] = []

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue

        coordinates = geometry.get("coordinates") or []
        local_points = [
            local_xy_m(
                float(longitude),
                float(latitude),
                reference_longitude,
                reference_latitude,
            )
            for longitude, latitude in coordinates
            if len((longitude, latitude)) == 2
        ]

        if len(local_points) < 2:
            continue

        properties = feature.get("properties") or {}
        axis = classify_pilot_axis(properties.get("name"))
        local_roads.append(
            {
                "points_m": local_points,
                "name": properties.get("name"),
                "highway": properties.get("highway"),
                "axis": axis,
                "oneway": bool(properties.get("oneway")),
            }
        )
        all_points.extend(local_points)

    if not all_points:
        raise ValueError("GeoJSON OSM sem LineStrings utilizáveis.")

    min_x = min(point[0] for point in all_points)
    max_x = max(point[0] for point in all_points)
    min_y = min(point[1] for point in all_points)
    max_y = max(point[1] for point in all_points)

    drawable_width = max(1, width - 2 * padding)
    drawable_height = max(1, (bottom - top) - 2 * padding)
    span_x = max(1.0, max_x - min_x)
    span_y = max(1.0, max_y - min_y)
    scale = min(drawable_width / span_x, drawable_height / span_y)

    used_width = span_x * scale
    used_height = span_y * scale
    offset_x = (width - used_width) / 2.0 - min_x * scale
    offset_y = (
        top
        + (bottom - top - used_height) / 2.0
        + max_y * scale
    )

    def project(point: tuple[float, float]) -> tuple[float, float]:
        return (
            offset_x + point[0] * scale,
            offset_y - point[1] * scale,
        )

    screen_roads: list[dict[str, Any]] = []
    axis_points = {
        "barao": [],
        "augusto": [],
    }

    for road in local_roads:
        points = [project(point) for point in road["points_m"]]
        screen_roads.append(
            {
                **road,
                "points": points,
                "width": road_width_for_highway(road["highway"]),
            }
        )
        if road["axis"] in axis_points:
            axis_points[road["axis"]].extend(points)

    reference_screen = project((0.0, 0.0))
    anchor = _nearest_midpoint(
        axis_points["barao"],
        axis_points["augusto"],
        reference_screen,
    )

    barao_vector = _principal_axis(axis_points["barao"])
    augusto_vector = _principal_axis(axis_points["augusto"])

    if barao_vector[0] < 0:
        barao_vector = (-barao_vector[0], -barao_vector[1])

    if augusto_vector[1] > 0:
        augusto_vector = (-augusto_vector[0], -augusto_vector[1])

    if not axis_points["barao"]:
        barao_vector = (1.0, 0.0)

    if not axis_points["augusto"]:
        augusto_vector = (0.0, -1.0)

    return {
        "roads": screen_roads,
        "anchor": anchor,
        "reference_screen": reference_screen,
        "axis_vectors": {
            "barao": barao_vector,
            "augusto": augusto_vector,
        },
        "map_scale_px_per_m": scale,
        "traffic_scale_px_per_m": max(1.55, min(2.2, scale * 2.5)),
        "pilot_feature_counts": {
            "barao": sum(1 for road in screen_roads if road["axis"] == "barao"),
            "augusto": sum(1 for road in screen_roads if road["axis"] == "augusto"),
        },
        "road_count": len(screen_roads),
    }


def vehicle_pose_on_osm(
    movement: str,
    position_m: float,
    context: dict[str, Any],
) -> tuple[tuple[float, float], tuple[float, float]]:
    barao = context["axis_vectors"]["barao"]
    augusto = context["axis_vectors"]["augusto"]

    direction_by_movement = {
        "barao_eastbound": barao,
        "barao_westbound": (-barao[0], -barao[1]),
        "augusto_northbound": augusto,
        "augusto_southbound": (-augusto[0], -augusto[1]),
    }

    if movement not in direction_by_movement:
        raise ValueError(f"Movimento OSM desconhecido: {movement}")

    direction = direction_by_movement[movement]
    anchor_x, anchor_y = context["anchor"]
    traffic_scale = context["traffic_scale_px_per_m"]

    front = (
        anchor_x + direction[0] * position_m * traffic_scale,
        anchor_y + direction[1] * position_m * traffic_scale,
    )
    return front, direction
