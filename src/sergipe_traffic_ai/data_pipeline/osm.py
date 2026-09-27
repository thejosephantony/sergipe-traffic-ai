from __future__ import annotations

import json
import re
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_ATTRIBUTION = "© OpenStreetMap contributors"
OSM_LICENSE = "ODbL 1.0"


def build_overpass_query(
    latitude: float,
    longitude: float,
    radius_m: int,
) -> str:
    radius = max(100, int(radius_m))
    return (
        "[out:json][timeout:30];"
        "("
        f'way["highway"](around:{radius},{latitude:.7f},{longitude:.7f});'
        ");"
        "out body;"
        ">;"
        "out skel qt;"
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def fetch_overpass(
    latitude: float,
    longitude: float,
    radius_m: int,
    destination: Path | None = None,
    endpoint: str = OVERPASS_URL,
) -> dict[str, Any]:
    query = build_overpass_query(latitude, longitude, radius_m)
    data = urllib.parse.urlencode({"data": query}).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={
            "User-Agent": "SergipeTrafficAI/0.1 academic-project",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if destination is not None:
        _write_json(destination, payload)

    return payload


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().strip().split())


def matches_alias(name: str | None, aliases: list[str]) -> bool:
    normalized_name = _normalize_text(name)
    if not normalized_name:
        return False

    return any(
        _normalize_text(alias) in normalized_name
        or normalized_name in _normalize_text(alias)
        for alias in aliases
        if alias.strip()
    )


def parse_int_tag(value: Any) -> int | None:
    if value is None:
        return None

    match = re.search(r"\d+", str(value))
    if not match:
        return None

    return int(match.group(0))


def parse_maxspeed_kmh(value: Any) -> int | None:
    if value is None:
        return None

    text = str(value).lower().strip()
    match = re.search(r"\d+(?:[.,]\d+)?", text)
    if not match:
        return None

    speed = float(match.group(0).replace(",", "."))

    if "mph" in text:
        speed *= 1.609344

    return int(round(speed))


def normalize_oneway(value: Any) -> bool:
    return str(value).lower().strip() in {
        "yes",
        "true",
        "1",
        "-1",
        "reversible",
    }


def osm_to_geojson(
    payload: dict[str, Any],
    pilot_road_aliases: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    aliases = pilot_road_aliases or []
    elements = payload.get("elements", [])

    nodes: dict[int, tuple[float, float]] = {}
    ways: list[dict[str, Any]] = []

    for element in elements:
        element_type = element.get("type")
        if element_type == "node":
            if "lat" in element and "lon" in element:
                nodes[int(element["id"])] = (
                    float(element["lon"]),
                    float(element["lat"]),
                )
        elif element_type == "way":
            ways.append(element)

    features: list[dict[str, Any]] = []
    highway_counts: Counter[str] = Counter()
    pilot_names: set[str] = set()
    named_count = 0
    oneway_count = 0

    for way in ways:
        tags = way.get("tags") or {}
        highway = str(tags.get("highway", "unknown"))
        node_ids = way.get("nodes") or []
        coordinates = [
            nodes[node_id]
            for node_id in node_ids
            if node_id in nodes
        ]

        if len(coordinates) < 2:
            continue

        name = tags.get("name")
        if name:
            named_count += 1

        pilot_match = matches_alias(name, aliases)
        if pilot_match and name:
            pilot_names.add(str(name))

        oneway = normalize_oneway(tags.get("oneway"))
        if oneway:
            oneway_count += 1

        highway_counts[highway] += 1

        properties = {
            "osm_id": int(way["id"]),
            "name": name,
            "highway": highway,
            "oneway": oneway,
            "oneway_raw": tags.get("oneway"),
            "lanes": parse_int_tag(tags.get("lanes")),
            "maxspeed_kmh": parse_maxspeed_kmh(tags.get("maxspeed")),
            "surface": tags.get("surface"),
            "access": tags.get("access"),
            "bridge": tags.get("bridge"),
            "tunnel": tags.get("tunnel"),
            "pilot_road_match": pilot_match,
            "source": "OpenStreetMap",
            "attribution": OSM_ATTRIBUTION,
            "license": OSM_LICENSE,
        }

        features.append(
            {
                "type": "Feature",
                "id": f"osm-way-{way['id']}",
                "properties": properties,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates,
                },
            }
        )

    all_coordinates = [
        coordinate
        for feature in features
        for coordinate in feature["geometry"]["coordinates"]
    ]

    bbox = None
    if all_coordinates:
        xs = [coordinate[0] for coordinate in all_coordinates]
        ys = [coordinate[1] for coordinate in all_coordinates]
        bbox = [min(xs), min(ys), max(xs), max(ys)]

    geojson = {
        "type": "FeatureCollection",
        "name": "sergipe_traffic_ai_osm_road_network",
        "attribution": OSM_ATTRIBUTION,
        "license": OSM_LICENSE,
        "features": features,
    }

    summary = {
        "source": "OpenStreetMap via Overpass API",
        "attribution": OSM_ATTRIBUTION,
        "license": OSM_LICENSE,
        "element_count": len(elements),
        "node_count": len(nodes),
        "way_count": len(ways),
        "road_feature_count": len(features),
        "named_road_count": named_count,
        "oneway_road_count": oneway_count,
        "highway_types": dict(sorted(highway_counts.items())),
        "pilot_road_names_found": sorted(pilot_names),
        "bbox_wgs84": bbox,
    }

    return geojson, summary


def integrate_osm_network(
    scenario: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    scenario_data = scenario["scenario"]
    road_network = scenario_data.get("road_network", {})
    reference = scenario_data["location"].get("reference_point")

    if not reference:
        raise ValueError(
            "O cenário precisa de location.reference_point para consultar o OSM."
        )

    latitude = float(reference["latitude"])
    longitude = float(reference["longitude"])
    radius_m = int(road_network.get("radius_m", 800))
    aliases = list(road_network.get("pilot_road_aliases", []))

    raw_path = output_dir / "osm_raw_overpass.json"
    geojson_path = output_dir / "osm_road_network.geojson"
    summary_path = output_dir / "osm_summary.json"

    payload = fetch_overpass(
        latitude=latitude,
        longitude=longitude,
        radius_m=radius_m,
        destination=raw_path,
        endpoint=road_network.get("endpoint", OVERPASS_URL),
    )
    geojson, summary = osm_to_geojson(payload, aliases)

    _write_json(geojson_path, geojson)
    _write_json(summary_path, summary)

    return {
        "status": "downloaded",
        "reference_point": {
            "latitude": latitude,
            "longitude": longitude,
            "radius_m": radius_m,
        },
        "raw_path": str(raw_path),
        "geojson_path": str(geojson_path),
        "summary_path": str(summary_path),
        "summary": summary,
    }
