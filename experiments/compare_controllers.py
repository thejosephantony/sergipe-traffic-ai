"""Compara os três controladores nas mesmas seeds e no mesmo cenário."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any

from sergipe_traffic_ai.controllers.adaptive_controller import (
    AdaptiveTrafficController,
)
from sergipe_traffic_ai.controllers.fixed_controller import FixedTrafficController
from sergipe_traffic_ai.controllers.q_learning import QLearningAgent
from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment
from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    BARAO_AXIS,
    TrafficDemandSimulator,
)
from sergipe_traffic_ai.training.q_learning import run_episode, scenario_for_episode


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "aracaju_barao_augusto.json"
DEFAULT_MODEL = ROOT / "models" / "q_learning_aracaju.json"
DEFAULT_OUTPUT = ROOT / "experiments" / "output" / "comparison"


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def run_classical(
    scenario: dict[str, Any],
    controller: Any,
    seed: int,
) -> dict[str, float | int | str]:
    config = json.loads(json.dumps(scenario))
    config["scenario"]["seed"] = seed
    simulator = TrafficDemandSimulator(config)
    controller.reset(config)

    queue_sum = 0.0
    max_queue = 0
    steps = 0

    while simulator.current_time < simulator.duration_s:
        simulator.generate_vehicles_step()
        observation = {
            "queue_barao": simulator.queue_length(BARAO_AXIS),
            "queue_augusto": simulator.queue_length(AUGUSTO_AXIS),
            "wait_barao": simulator.average_wait(BARAO_AXIS),
            "wait_augusto": simulator.average_wait(AUGUSTO_AXIS),
            "time_step_s": simulator.time_step_s,
            "conflict_zone_occupied": simulator.conflict_zone_occupied(),
        }
        phase = controller.decide(observation, simulator.current_time)
        simulator.step(phase)

        total_queue = (
            observation["queue_barao"] + observation["queue_augusto"]
        )
        queue_sum += total_queue
        max_queue = max(max_queue, int(total_queue))
        steps += 1

    duration_minutes = max(simulator.current_time / 60.0, 1e-9)
    return {
        "controller": controller.__class__.__name__,
        "seed": seed,
        "vehicles_generated": simulator.vehicle_counter,
        "vehicles_completed": simulator.completed_vehicles_count,
        "average_completed_wait_s": round(
            simulator.average_completed_wait(), 4
        ),
        "mean_queue": round(queue_sum / max(steps, 1), 4),
        "max_queue": max_queue,
        "throughput_per_min": round(
            simulator.completed_vehicles_count / duration_minutes, 4
        ),
    }


def run_q_learning(
    scenario: dict[str, Any],
    model_path: Path,
    seed: int,
    duration_s: float,
) -> dict[str, float | int | str]:
    config = scenario_for_episode(scenario, duration_s)
    config["scenario"]["seed"] = seed
    environment = TrafficRLEnvironment(config)
    agent = QLearningAgent.load(model_path, seed=seed, epsilon=0.0)
    result = run_episode(environment, agent, seed=seed, training=False)
    return {
        "controller": "QLearningAgent",
        **result,
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = (
        "average_completed_wait_s",
        "mean_queue",
        "max_queue",
        "throughput_per_min",
        "vehicles_completed",
    )
    summary: dict[str, Any] = {}
    for controller in sorted({str(row["controller"]) for row in rows}):
        controller_rows = [
            row for row in rows if row["controller"] == controller
        ]
        values: dict[str, Any] = {}
        for metric in metrics:
            series = [float(row[metric]) for row in controller_rows]
            values[metric] = {
                "mean": round(statistics.mean(series), 4),
                "median": round(statistics.median(series), 4),
                "std": round(statistics.stdev(series), 4) if len(series) > 1 else 0.0,
                "min": round(min(series), 4),
                "max": round(max(series), 4),
            }
        summary[controller] = {
            "episodes": len(controller_rows),
            "metrics": values,
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara fixo, adaptativo e Q-Learning em seeds pareadas."
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed-start", type=int, default=1000)
    parser.add_argument("--duration", type=float, default=600.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if args.seeds < 2:
        raise ValueError("Use pelo menos duas seeds para estimar variabilidade.")
    if not args.model.exists():
        raise FileNotFoundError(
            f"Modelo não encontrado: {args.model}. Execute o treinamento primeiro."
        )

    scenario = load_scenario(args.scenario)
    scenario = scenario_for_episode(scenario, args.duration)
    rows: list[dict[str, Any]] = []

    for seed in range(args.seed_start, args.seed_start + args.seeds):
        rows.append(
            run_classical(
                scenario,
                FixedTrafficController(),
                seed,
            )
        )
        rows.append(
            run_classical(
                scenario,
                AdaptiveTrafficController(),
                seed,
            )
        )
        rows.append(run_q_learning(scenario, args.model, seed, args.duration))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "controller_comparison.csv"
    json_path = args.output_dir / "controller_comparison_summary.json"

    with csv_path.open("w", encoding="utf-8", newline="") as file:
        fieldnames = list(dict.fromkeys(
            key for row in rows for key in row.keys()
        ))
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "scenario": str(args.scenario),
        "duration_s": args.duration,
        "seed_start": args.seed_start,
        "seeds": args.seeds,
        "model": str(args.model),
        "controllers": aggregate(rows),
    }
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
        file.write("\n")

    print("=== COMPARAÇÃO DE CONTROLADORES ===")
    print(f"Episódios por controlador: {args.seeds}")
    for controller, data in summary["controllers"].items():
        metrics = data["metrics"]
        print(
            f"{controller}: espera={metrics['average_completed_wait_s']['mean']:.2f} s | "
            f"fila={metrics['mean_queue']['mean']:.2f} | "
            f"throughput={metrics['throughput_per_min']['mean']:.2f} veh/min"
        )
    print(f"CSV: {csv_path}")
    print(f"Resumo: {json_path}")


if __name__ == "__main__":
    main()
