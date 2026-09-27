import math

from sergipe_traffic_ai.data_pipeline.checkin2 import (
    normalize_weights,
    preprocess_scenario,
    summarize_geojson,
)


def scenario():
    return {
        "scenario": {
            "id": "test",
            "location": {
                "city": "Aracaju",
                "state": "SE",
            },
            "seed": 42,
            "duration_s": 100,
            "time_step_s": 0.2,
            "demand": {
                "axis_barao_maynard_rate": 0.8,
                "axis_augusto_franco_rate": 0.6,
                "vehicle_mix": {
                    "car": 72,
                    "motorcycle": 18,
                    "bus": 10,
                },
                "direction_split": {
                    "barao_eastbound": 3,
                    "barao_westbound": 1,
                    "augusto_northbound": 1,
                    "augusto_southbound": 3,
                },
            },
            "controller": {
                "type": "fixed",
                "yellow_s": 4,
                "all_red_s": 2,
            },
        }
    }


def test_normalize_weights():
    result = normalize_weights(
        {"car": 72, "motorcycle": 18, "bus": 10},
        ("car", "motorcycle", "bus"),
    )

    assert result == {
        "car": 0.72,
        "motorcycle": 0.18,
        "bus": 0.10,
    }


def test_preprocess_scenario_derives_directional_rates():
    processed = preprocess_scenario(scenario())
    rates = processed["cleaned_demand"]["directional_rates_veh_s"]

    assert math.isclose(rates["barao_eastbound"], 0.6)
    assert math.isclose(rates["barao_westbound"], 0.2)
    assert math.isclose(rates["augusto_northbound"], 0.15)
    assert math.isclose(rates["augusto_southbound"], 0.45)
    assert processed["baseline"]["machine_learning"] is False


def test_summarize_geojson_extracts_bbox():
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-37.1, -10.9],
                            [-37.0, -10.9],
                            [-37.0, -10.8],
                            [-37.1, -10.9],
                        ]
                    ],
                },
            }
        ],
    }

    result = summarize_geojson(geojson)

    assert result["feature_count"] == 1
    assert result["geometry_types"] == ["Polygon"]
    assert result["bbox_wgs84"] == [-37.1, -10.9, -37.0, -10.8]
