"""Gera figuras do relatório a partir dos artefatos do pipeline e da comparação."""

from __future__ import annotations

import io
import json
import math
import urllib.request
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "experiments" / "output" / "report"
OSM_GEOJSON = (
    ROOT
    / "experiments"
    / "output"
    / "checkin2"
    / "osm"
    / "osm_road_network.geojson"
)
SUMMARY = (
    ROOT
    / "experiments"
    / "output"
    / "comparison"
    / "controller_comparison_summary.json"
)
SENSITIVITY_SUMMARY = (
    ROOT
    / "experiments"
    / "output"
    / "sensitivity"
    / "sensitivity_summary.json"
)


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[float, float]:
    n = 2.0**zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def tile_to_lonlat(x: float, y: float, zoom: int) -> tuple[float, float]:
    n = 2.0**zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1.0 - 2.0 * y / n))))
    return lon, lat


def download_osm_basemap(
    bbox: list[float],
    zoom: int = 16,
) -> tuple[Image.Image, list[float]]:
    west, south, east, north = bbox
    west -= 0.0015
    east += 0.0015
    south -= 0.0015
    north += 0.0015
    x0, y1 = lonlat_to_tile(west, south, zoom)
    x1, y0 = lonlat_to_tile(east, north, zoom)
    min_x, max_x = math.floor(x0), math.floor(x1)
    min_y, max_y = math.floor(y0), math.floor(y1)
    canvas = Image.new(
        "RGB",
        ((max_x - min_x + 1) * 256, (max_y - min_y + 1) * 256),
        "white",
    )

    request_headers = {
        "User-Agent": "SergipeTrafficAI/0.1 academic report",
    }
    for tile_x in range(min_x, max_x + 1):
        for tile_y in range(min_y, max_y + 1):
            url = f"https://tile.openstreetmap.org/{zoom}/{tile_x}/{tile_y}.png"
            request = urllib.request.Request(url, headers=request_headers)
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    tile = Image.open(io.BytesIO(response.read())).convert("RGB")
                canvas.paste(
                    tile,
                    ((tile_x - min_x) * 256, (tile_y - min_y) * 256),
                )
            except Exception:
                continue

    extent_west, extent_north = tile_to_lonlat(min_x, min_y, zoom)
    extent_east, extent_south = tile_to_lonlat(max_x + 1, max_y + 1, zoom)
    return canvas, [extent_west, extent_east, extent_south, extent_north]


def create_osm_map() -> Path:
    payload = json.loads(OSM_GEOJSON.read_text(encoding="utf-8"))
    features = payload["features"]
    bbox = [
        min(point[0] for f in features for point in f["geometry"]["coordinates"]),
        min(point[1] for f in features for point in f["geometry"]["coordinates"]),
        max(point[0] for f in features for point in f["geometry"]["coordinates"]),
        max(point[1] for f in features for point in f["geometry"]["coordinates"]),
    ]
    basemap, extent = download_osm_basemap(bbox)

    fig, ax = plt.subplots(figsize=(12, 8), dpi=180)
    ax.imshow(basemap, extent=extent, interpolation="bilinear", zorder=0)

    colors = {
        "primary": "#b33b34",
        "secondary": "#d28a2e",
        "tertiary": "#4d7ea8",
        "residential": "#6c757d",
        "service": "#9aa0a6",
        "footway": "#7b6d8d",
        "cycleway": "#2a9d8f",
    }
    highlighted = {"Avenida Augusto Franco", "Avenida Desembargador Maynard"}
    for feature in features:
        properties = feature.get("properties", {})
        highway = properties.get("highway", "")
        name = properties.get("name")
        coords = feature["geometry"]["coordinates"]
        xs = [point[0] for point in coords]
        ys = [point[1] for point in coords]
        is_pilot = name in highlighted
        ax.plot(
            xs,
            ys,
            color="#e63946" if is_pilot else colors.get(highway, "#8d99ae"),
            linewidth=2.8 if is_pilot else (1.3 if highway in colors else 0.7),
            alpha=0.95 if is_pilot else 0.78,
            zorder=2,
        )

    reference_lon = -37.06943
    reference_lat = -10.9187
    ax.scatter(
        [reference_lon],
        [reference_lat],
        s=70,
        color="#111111",
        edgecolor="white",
        linewidth=1.2,
        zorder=5,
        label="Ponto de referência do cenário",
    )
    ax.annotate(
        "Cruzamento piloto aproximado",
        (reference_lon, reference_lat),
        xytext=(8, 10),
        textcoords="offset points",
        fontsize=9,
        color="#111111",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.85},
        zorder=6,
    )
    ax.set_xlim(bbox[0] - 0.002, bbox[2] + 0.002)
    ax.set_ylim(bbox[1] - 0.002, bbox[3] + 0.002)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title(
        "Contexto geográfico do cenário piloto em Aracaju",
        fontsize=16,
        weight="bold",
    )
    ax.legend(loc="lower left", framealpha=0.9)
    ax.grid(alpha=0.25)
    fig.text(
        0.01,
        0.01,
        "Fonte cartográfica: © OpenStreetMap contributors | Dados consultados via Overpass API | ODbL 1.0",
        fontsize=8,
        color="#333333",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "osm_context_map.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def create_comparison_chart() -> Path:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    labels = {
        "FixedTrafficController": "Fixo",
        "AdaptiveTrafficController": "Adaptativo",
        "QLearningAgent": "Q-Learning",
    }
    colors = ["#6c757d", "#2a9d8f", "#e76f51"]
    controllers = list(labels)
    x = list(range(len(controllers)))

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.8), dpi=180)
    chart_data = [
        ("average_completed_wait_s", "Espera média dos concluídos (s)", "menor é melhor"),
        ("mean_queue", "Fila média (veículos)", "menor é melhor"),
        ("throughput_per_min", "Throughput (veículos/min)", "maior é melhor"),
    ]
    for ax, (metric, title, subtitle) in zip(axes, chart_data):
        means = [
            summary["controllers"][controller]["metrics"][metric]["mean"]
            for controller in controllers
        ]
        stds = [
            summary["controllers"][controller]["metrics"][metric]["std"]
            for controller in controllers
        ]
        ax.bar(x, means, yerr=stds, color=colors, capsize=4, alpha=0.9)
        ax.set_xticks(x, [labels[controller] for controller in controllers])
        ax.set_title(title, fontsize=10, weight="bold", pad=10)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
        for index, value in enumerate(means):
            ax.text(index, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)

    fig.suptitle("Comparação controlada dos controladores", fontsize=15, weight="bold")
    fig.text(
        0.5,
        0.01,
        "Média ± desvio-padrão em 20 episódios de 600 s; seeds 1000 a 1019",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "controller_comparison.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def create_sensitivity_chart() -> Path:
    summary = json.loads(SENSITIVITY_SUMMARY.read_text(encoding="utf-8"))
    labels = {
        "FixedTrafficController": "Fixo",
        "AdaptiveTrafficController": "Adaptativo",
        "QLearningAgent": "Q-Learning",
    }
    colors = ["#6c757d", "#2a9d8f", "#e76f51"]
    controllers = list(labels)
    scenarios = [
        ("base", "Base"),
        ("pico_barao", "Pico\nBarão"),
        ("pico_augusto", "Pico\nAugusto"),
        ("frota_pesada", "Frota\npesada"),
        ("prioridade_fluidez", "Prioridade\nfluidez"),
    ]
    metrics = [
        ("average_completed_wait_s", "Espera média dos concluídos (s)", "menor é melhor"),
        ("mean_queue", "Fila média (veículos)", "menor é melhor"),
        ("throughput_per_min", "Throughput (veículos/min)", "maior é melhor"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.4), dpi=180)
    x = list(range(len(scenarios)))
    width = 0.24
    for ax, (metric, title, subtitle) in zip(axes, metrics):
        for index, controller in enumerate(controllers):
            means = []
            stds = []
            for scenario_id, _ in scenarios:
                metric_data = summary["scenarios"][scenario_id]["controllers"][controller]["metrics"][metric]
                means.append(metric_data["mean"])
                stds.append(metric_data["std"])
            offsets = [value + (index - 1) * width for value in x]
            ax.bar(
                offsets,
                means,
                width,
                yerr=stds,
                capsize=3,
                color=colors[index],
                alpha=0.9,
                label=labels[controller],
            )
            for offset, value in zip(offsets, means):
                ax.text(offset, value, f"{value:.1f}", ha="center", va="bottom", fontsize=7)
        ax.set_xticks(x, [label for _, label in scenarios])
        ax.set_title(title, fontsize=10, weight="bold", pad=10)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)
        ax.text(0.5, 1.01, subtitle, transform=ax.transAxes, ha="center", fontsize=8, color="#5b6573")

    axes[0].legend(loc="upper left", fontsize=8, framealpha=0.95)
    fig.suptitle("Sensibilidade dos controladores em cinco cenários", fontsize=15, weight="bold")
    fig.text(
        0.5,
        0.01,
        "Média ± desvio-padrão em 20 episódios de 600 s por cenário; seeds 1000 a 1019",
        ha="center",
        fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.05, 1, 0.92))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / "sensitivity_comparison.png"
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


if __name__ == "__main__":
    print(create_osm_map())
    print(create_comparison_chart())
    print(create_sensitivity_chart())
