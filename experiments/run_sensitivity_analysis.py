"""Executa a análise de sensibilidade dos cenários de demanda e recompensa."""

from __future__ import annotations

import argparse
import copy
import csv
import json
from pathlib import Path
from typing import Any

from sergipe_traffic_ai.controllers.adaptive_controller import (
    AdaptiveTrafficController,
)
from sergipe_traffic_ai.controllers.fixed_controller import FixedTrafficController
from sergipe_traffic_ai.training.q_learning import train_q_learning

from compare_controllers import aggregate, run_classical, run_q_learning


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "aracaju_barao_augusto.json"
DEFAULT_VARIANTS = ROOT / "experiments" / "sensitivity_scenarios.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "output" / "sensitivity"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def scenario_for_variant(
    base_scenario: dict[str, Any],
    variant: dict[str, Any],
    duration_s: float,
) -> dict[str, Any]:
    scenario = copy.deepcopy(base_scenario)
    config = scenario["scenario"]
    config["id"] = f"{config['id']}_{variant['id']}"
    config["duration_s"] = float(duration_s)
    config["demand"].update(variant["demand"])
    config["demand"]["vehicle_mix"] = copy.deepcopy(
        variant["vehicle_mix"]
    )
    config["q_learning"].update(variant["reward"])
    return scenario


def train_variant(
    scenario: dict[str, Any],
    variant: dict[str, Any],
    episodes: int,
    duration_s: float,
    seed: int,
    model_dir: Path,
) -> Path:
    agent, _ = train_q_learning(
        scenario,
        episodes=episodes,
        duration_s=duration_s,
        seed=seed,
    )
    model_path = model_dir / f"q_learning_{variant['id']}.json"
    agent.save(
        model_path,
        metadata={
            "scenario": scenario["scenario"]["id"],
            "variant": variant["id"],
            "training_episodes": episodes,
            "episode_duration_s": duration_s,
            "training_seed": seed,
        },
    )
    return model_path


def run_variant(
    scenario: dict[str, Any],
    variant: dict[str, Any],
    model_path: Path,
    seeds: int,
    seed_start: int,
    duration_s: float,
    train_episodes: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for seed in range(seed_start, seed_start + seeds):
        classical = (
            ("FixedTrafficController", FixedTrafficController()),
            ("AdaptiveTrafficController", AdaptiveTrafficController()),
        )
        for controller_name, controller in classical:
            result = run_classical(scenario, controller, seed)
            result["controller"] = controller_name
            rows.append(result)

        q_result = run_q_learning(scenario, model_path, seed, duration_s)
        q_result["controller"] = "QLearningAgent"
        rows.append(q_result)

    for row in rows:
        row.update(
            {
                "scenario_id": variant["id"],
                "scenario_label": variant["label"],
                "train_episodes": train_episodes,
                "model_path": str(model_path),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa cenários de sensibilidade com três controladores."
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--variants", type=Path, default=DEFAULT_VARIANTS)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--train-seed", type=int, default=42)
    parser.add_argument("--train-episodes", type=int, default=100)
    parser.add_argument("--duration", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.seeds < 2:
        raise ValueError("Use pelo menos duas seeds para estimar variabilidade.")
    if args.train_episodes < 1:
        raise ValueError("O treinamento precisa de pelo menos um episódio.")

    base_scenario = load_json(args.scenario)
    variants = load_json(args.variants)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    model_dir = args.output_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    scenario_summaries: dict[str, Any] = {}
    for variant in variants:
        scenario = scenario_for_variant(
            base_scenario,
            variant,
            args.duration,
        )
        model_path = train_variant(
            scenario,
            variant,
            args.train_episodes,
            args.duration,
            args.train_seed,
            model_dir,
        )
        variant_rows = run_variant(
            scenario,
            variant,
            model_path,
            args.seeds,
            args.seed_start,
            args.duration,
            args.train_episodes,
        )
        rows.extend(variant_rows)
        scenario_summaries[variant["id"]] = {
            "label": variant["label"],
            "objective": variant["objective"],
            "parameters": variant,
            "model_path": str(model_path),
            "controllers": aggregate(variant_rows),
        }
        print(
            f"{variant['label']}: "
            + " | ".join(
                f"{name} espera="
                f"{data['metrics']['average_completed_wait_s']['mean']:.2f}s"
                for name, data in scenario_summaries[variant["id"]][
                    "controllers"
                ].items()
            )
        )

    csv_path = args.output_dir / "sensitivity_results.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        fieldnames = list(dict.fromkeys(
            key for row in rows for key in row.keys()
        ))
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "scenario": str(args.scenario),
        "variants_file": str(args.variants),
        "duration_s": args.duration,
        "seed_start": args.seed_start,
        "seeds": args.seeds,
        "train_seed": args.train_seed,
        "train_episodes": args.train_episodes,
        "scenarios": scenario_summaries,
    }
    summary_path = args.output_dir / "sensitivity_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"CSV: {csv_path}")
    print(f"Resumo: {summary_path}")


if __name__ == "__main__":
    main()
