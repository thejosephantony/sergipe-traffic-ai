import math

from sergipe_traffic_ai.visual.osm_map import (
    build_osm_map_context,
    classify_pilot_axis,
    local_xy_m,
    vehicle_pose_on_osm,
)


def scenario():
    return {
        "scenario": {
            "location": {
                "reference_point": {
                    "latitude": -10.9187,
                    "longitude": -37.06943,
                }
            }
        }
    }


def geojson():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": "Avenida Desembargador Maynard",
                    "highway": "primary",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-37.0703, -10.9187],
                        [-37.06943, -10.9187],
                        [-37.0686, -10.9187],
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {
                    "name": "Avenida Augusto Franco",
                    "highway": "primary",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-37.06943, -10.9195],
                        [-37.06943, -10.9187],
                        [-37.06943, -10.9179],
                    ],
                },
            },
        ],
    }


def test_classify_pilot_axis():
    assert classify_pilot_axis("Av. Augusto Franco") == "augusto"
    assert classify_pilot_axis("Avenida Rio de Janeiro") == "augusto"
    assert classify_pilot_axis("Av. Barão de Maruim") == "barao"
    assert classify_pilot_axis("Desembargador Maynard") == "barao"
    assert classify_pilot_axis("Rua qualquer") is None


def test_local_projection_has_expected_orientation():
    origin = local_xy_m(
        -37.06943,
        -10.9187,
        -37.06943,
        -10.9187,
    )
    east = local_xy_m(
        -37.06843,
        -10.9187,
        -37.06943,
        -10.9187,
    )
    north = local_xy_m(
        -37.06943,
        -10.9177,
        -37.06943,
        -10.9187,
    )

    assert origin == (0.0, 0.0)
    assert east[0] > 0
    assert north[1] > 0


def test_context_aligns_pilot_axes_and_vehicle_directions():
    context = build_osm_map_context(
        geojson(),
        scenario(),
        width=1000,
        top=80,
        bottom=800,
    )

    barao = context["axis_vectors"]["barao"]
    augusto = context["axis_vectors"]["augusto"]

    assert barao[0] > 0
    assert abs(barao[1]) < 0.01
    assert augusto[1] < 0
    assert abs(augusto[0]) < 0.01

    east_front, east_direction = vehicle_pose_on_osm(
        "barao_eastbound",
        20.0,
        context,
    )
    west_front, west_direction = vehicle_pose_on_osm(
        "barao_westbound",
        20.0,
        context,
    )

    assert east_front[0] > context["anchor"][0]
    assert west_front[0] < context["anchor"][0]
    assert east_direction[0] > 0
    assert west_direction[0] < 0


def test_context_scale_is_positive():
    context = build_osm_map_context(
        geojson(),
        scenario(),
        width=1000,
        top=80,
        bottom=800,
    )

    assert math.isfinite(context["map_scale_px_per_m"])
    assert context["map_scale_px_per_m"] > 0
    assert context["traffic_scale_px_per_m"] > 0
