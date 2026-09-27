from __future__ import annotations

import argparse
import json
import math
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sergipe_traffic_ai.data_pipeline.osm import integrate_osm_network


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SCENARIO = ROOT / "scenarios" / "aracaju_barao_augusto.json"
DEFAULT_CATALOG = ROOT / "data" / "checkin2" / "source_catalog.json"
DEFAULT_OUTPUT_DIR = ROOT / "experiments" / "output" / "checkin2"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def normalize_weights(
    raw: dict[str, Any],
    expected_keys: tuple[str, ...],
) -> dict[str, float]:
    values = {
        key: max(0.0, float(raw.get(key, 0.0)))
        for key in expected_keys
    }
    total = sum(values.values())
    if total <= 0:
        raise ValueError(
            f"Distribuição inválida para {expected_keys}: soma deve ser positiva."
        )
    return {
        key: value / total
        for key, value in values.items()
    }


def preprocess_scenario(raw: dict[str, Any]) -> dict[str, Any]:
    scenario = raw["scenario"]
    demand = scenario["demand"]

    barao_rate = float(demand["axis_barao_maynard_rate"])
    augusto_rate = float(demand["axis_augusto_franco_rate"])
    if barao_rate < 0 or augusto_rate < 0:
        raise ValueError("Taxas de chegada não podem ser negativas.")

    vehicle_mix = normalize_weights(
        demand.get("vehicle_mix", {}),
        ("car", "motorcycle", "bus"),
    )
    direction_split = normalize_weights(
        demand.get("direction_split", {}),
        (
            "barao_eastbound",
            "barao_westbound",
            "augusto_northbound",
            "augusto_southbound",
        ),
    )

    barao_direction_total = (
        direction_split["barao_eastbound"]
        + direction_split["barao_westbound"]
    )
    augusto_direction_total = (
        direction_split["augusto_northbound"]
        + direction_split["augusto_southbound"]
    )

    if barao_direction_total <= 0 or augusto_direction_total <= 0:
        raise ValueError("Cada eixo precisa ter pelo menos um sentido com peso positivo.")

    direction_split = {
        "barao_eastbound": (
            direction_split["barao_eastbound"] / barao_direction_total
        ),
        "barao_westbound": (
            direction_split["barao_westbound"] / barao_direction_total
        ),
        "augusto_northbound": (
            direction_split["augusto_northbound"] / augusto_direction_total
        ),
        "augusto_southbound": (
            direction_split["augusto_southbound"] / augusto_direction_total
        ),
    }

    directional_rates = {
        "barao_eastbound": barao_rate * direction_split["barao_eastbound"],
        "barao_westbound": barao_rate * direction_split["barao_westbound"],
        "augusto_northbound": augusto_rate * direction_split["augusto_northbound"],
        "augusto_southbound": augusto_rate * direction_split["augusto_southbound"],
    }

    mean_interarrival_s = {
        movement: (
            math.inf if rate <= 0 else 1.0 / rate
        )
        for movement, rate in directional_rates.items()
    }

    duration_s = float(scenario["duration_s"])
    expected_arrivals = {
        movement: rate * duration_s
        for movement, rate in directional_rates.items()
    }

    return {
        "scenario_id": scenario["id"],
        "location": scenario["location"],
        "provenance": {
            "geography": "IBGE (ingestão opcional ao vivo)",
            "road_network": "OpenStreetMap via Overpass API (integração ativa)",
            "traffic_demand": "sintético e reproduzível",
            "traffic_counts_real_world": False,
        },
        "road_network": {
            "source": scenario.get("road_network", {}).get("source"),
            "provider": scenario.get("road_network", {}).get("provider"),
            "radius_m": scenario.get("road_network", {}).get("radius_m"),
            "license": scenario.get("road_network", {}).get("license"),
            "attribution": scenario.get("road_network", {}).get("attribution"),
        },
        "reproducibility": {
            "seed": int(scenario["seed"]),
            "time_step_s": float(scenario["time_step_s"]),
            "duration_s": duration_s,
        },
        "cleaned_demand": {
            "axis_rates_veh_s": {
                "barao_maynard": barao_rate,
                "augusto_franco": augusto_rate,
            },
            "vehicle_mix": vehicle_mix,
            "direction_split": direction_split,
            "directional_rates_veh_s": directional_rates,
            "mean_interarrival_s": mean_interarrival_s,
            "expected_arrivals_over_scenario": expected_arrivals,
        },
        "baseline": {
            "model": "fixed_time_traffic_signal",
            "machine_learning": False,
            "controller": scenario["controller"],
            "role": (
                "Referência não-IA para comparação com controladores "
                "adaptativos e, posteriormente, Reinforcement Learning."
            ),
        },
        "preprocessing_steps": [
            "validar estrutura e tipos do cenário",
            "validar taxas de chegada não negativas",
            "normalizar composição da frota",
            "normalizar divisão de demanda por sentido em cada eixo",
            "derivar taxa de chegada por movimento",
            "fixar seed para reprodutibilidade",
            "registrar proveniência e distinguir dado oficial de dado sintético",
        ],
    }


def _iter_coordinates(value: Any):
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        yield float(value[0]), float(value[1])
        return

    if isinstance(value, list):
        for item in value:
            yield from _iter_coordinates(item)


def summarize_geojson(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("GeoJSON esperado no formato FeatureCollection.")

    coordinates: list[tuple[float, float]] = []
    geometry_types: set[str] = set()

    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        geometry_type = geometry.get("type")
        if geometry_type:
            geometry_types.add(str(geometry_type))
        coordinates.extend(_iter_coordinates(geometry.get("coordinates", [])))

    if not coordinates:
        raise ValueError("GeoJSON sem coordenadas utilizáveis.")

    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]

    return {
        "feature_count": len(payload.get("features", [])),
        "geometry_types": sorted(geometry_types),
        "bbox_wgs84": [min(xs), min(ys), max(xs), max(ys)],
        "coordinate_pairs_checked": len(coordinates),
        "checks": {
            "feature_collection": True,
            "has_geometry": True,
            "coordinate_order": "longitude, latitude",
        },
    }


def fetch_geojson(url: str, destination: Path) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "SergipeTrafficAI/0.1 academic-project"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))

    write_json(destination, payload)
    return payload


def prepare_checkin2(
    scenario_path: Path = DEFAULT_SCENARIO,
    catalog_path: Path = DEFAULT_CATALOG,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    fetch_geography: bool = False,
    fetch_osm: bool = False,
) -> dict[str, Any]:
    raw_scenario = load_json(scenario_path)
    catalog = load_json(catalog_path)

    processed = preprocess_scenario(raw_scenario)
    report: dict[str, Any] = {
        "checkin": "Check-in 2",
        "source_catalog": catalog,
        "processed_scenario": processed,
        "geography_ingestion": {
            "requested": fetch_geography,
            "results": [],
        },
        "osm_ingestion": {
            "requested": fetch_osm,
            "status": "not_requested",
        },
    }

    if fetch_geography:
        raw_dir = output_dir / "raw"
        for source in catalog["sources"]:
            if source.get("type") != "official_api":
                continue

            destination = raw_dir / f"{source['id']}.geojson"
            try:
                payload = fetch_geojson(source["endpoint"], destination)
                summary = summarize_geojson(payload)
                report["geography_ingestion"]["results"].append(
                    {
                        "source_id": source["id"],
                        "status": "downloaded",
                        "raw_file": str(destination.relative_to(ROOT)),
                        "summary": summary,
                    }
                )
            except (
                urllib.error.URLError,
                TimeoutError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                report["geography_ingestion"]["results"].append(
                    {
                        "source_id": source["id"],
                        "status": "unavailable",
                        "error": str(exc),
                    }
                )

    if fetch_osm:
        try:
            report["osm_ingestion"] = {
                "requested": True,
                **integrate_osm_network(
                    raw_scenario,
                    output_dir / "osm",
                ),
            }
        except (
            urllib.error.URLError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            report["osm_ingestion"] = {
                "requested": True,
                "status": "unavailable",
                "error": str(exc),
            }

    processed_path = output_dir / "preprocessed_scenario.json"
    report_path = output_dir / "checkin2_report.json"
    write_json(processed_path, processed)
    write_json(report_path, report)

    return {
        "processed_path": str(processed_path),
        "report_path": str(report_path),
        "report": report,
    }


def print_summary(result: dict[str, Any]) -> None:
    processed = result["report"]["processed_scenario"]
    demand = processed["cleaned_demand"]

    print("=== SERGIPE TRAFFIC AI | CHECK-IN 2 ===")
    print()
    print("1) FONTES DE DADOS")
    print("   • IBGE: malhas de Sergipe (UF 28) e Aracaju (2800308)")
    print("   • OpenStreetMap: rede viária integrada via Overpass API")
    print("   • Demanda atual: sintética, configurada no cenário")
    osm_status = result["report"]["osm_ingestion"].get("status")
    if result["report"]["osm_ingestion"].get("requested"):
        print(f"   • OSM nesta execução: {osm_status}")
    print()
    print("2) PRÉ-PROCESSAMENTO")
    for step in processed["preprocessing_steps"]:
        print(f"   • {step}")
    print()
    print("3) RESULTADO NORMALIZADO")
    print(
        "   • composição da frota: "
        f"{demand['vehicle_mix']}"
    )
    print(
        "   • taxas por sentido (veh/s): "
        f"{demand['directional_rates_veh_s']}"
    )
    print(
        "   • seed reproduzível: "
        f"{processed['reproducibility']['seed']}"
    )
    print()
    print("4) BASELINE")
    print("   • controlador semafórico de tempo fixo")
    print("   • não utiliza IA/ML")
    print("   • referência para comparação futura com RL")
    print()
    print(f"Relatório: {result['report_path']}")
    print(f"Cenário pré-processado: {result['processed_path']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Demonstração de fontes e pré-processamento do Check-in 2."
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--fetch-geography",
        action="store_true",
        help="Tenta baixar GeoJSON oficial do IBGE para Sergipe e Aracaju.",
    )
    parser.add_argument(
        "--fetch-osm",
        action="store_true",
        help="Baixa e pré-processa a rede viária do OpenStreetMap via Overpass.",
    )
    args = parser.parse_args()

    result = prepare_checkin2(
        scenario_path=args.scenario,
        catalog_path=args.catalog,
        output_dir=args.output_dir,
        fetch_geography=args.fetch_geography,
        fetch_osm=args.fetch_osm,
    )
    print_summary(result)


if __name__ == "__main__":
    main()
