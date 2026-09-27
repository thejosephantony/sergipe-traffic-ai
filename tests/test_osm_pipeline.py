from sergipe_traffic_ai.data_pipeline.osm import (
    build_overpass_query,
    matches_alias,
    normalize_oneway,
    osm_to_geojson,
    parse_int_tag,
    parse_maxspeed_kmh,
)


def sample_osm():
    return {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": -10.9187,
                "lon": -37.0695,
            },
            {
                "type": "node",
                "id": 2,
                "lat": -10.9186,
                "lon": -37.0694,
            },
            {
                "type": "node",
                "id": 3,
                "lat": -10.9185,
                "lon": -37.0693,
            },
            {
                "type": "way",
                "id": 100,
                "nodes": [1, 2, 3],
                "tags": {
                    "highway": "primary",
                    "name": "Avenida Augusto Franco",
                    "oneway": "yes",
                    "lanes": "3",
                    "maxspeed": "50 km/h",
                    "surface": "asphalt",
                },
            },
        ]
    }


def test_build_overpass_query_contains_highway_and_radius():
    query = build_overpass_query(-10.9187, -37.0694, 800)

    assert 'way["highway"]' in query
    assert "around:800,-10.9187000,-37.0694000" in query


def test_osm_to_geojson_normalizes_road_attributes():
    geojson, summary = osm_to_geojson(
        sample_osm(),
        ["Augusto Franco", "Desembargador Maynard"],
    )

    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1

    properties = geojson["features"][0]["properties"]
    assert properties["lanes"] == 3
    assert properties["maxspeed_kmh"] == 50
    assert properties["oneway"] is True
    assert properties["pilot_road_match"] is True

    assert summary["road_feature_count"] == 1
    assert summary["pilot_road_names_found"] == ["Avenida Augusto Franco"]


def test_osm_tag_parsers_are_tolerant():
    assert parse_int_tag("2;3") == 2
    assert parse_int_tag(None) is None
    assert parse_maxspeed_kmh("30 mph") == 48
    assert parse_maxspeed_kmh("signals") is None
    assert normalize_oneway("-1") is True


def test_alias_matching_ignores_accents_and_case():
    assert matches_alias(
        "Avenida Desembargador Maynard",
        ["desembargador maynard"],
    )
