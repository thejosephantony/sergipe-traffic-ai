from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path

from sergipe_traffic_ai.controllers.q_learning import QLearningAgent
from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment
from sergipe_traffic_ai.training.q_learning import (
    run_episode,
    scenario_for_episode,
)


DEFAULT_SCENARIO = Path("scenarios/aracaju_barao_augusto.json")
DEFAULT_MODEL = Path("models/q_learning_aracaju.json")
DEFAULT_OUTPUT = Path(
    "experiments/output/q_learning/evaluation.csv"
)


def load_scenario(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Avalia uma Q-table sem exploração (epsilon=0)."
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
    )
    parser.add_argument(
        "--seeds",
        type=int,
        default=20,
        help="Quantidade de seeds consecutivas usadas na avaliação.",
    )
    parser.add_argument(
        "--seed-start",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=600.0,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    scenario = scenario_for_episode(
        load_scenario(args.scenario),
        args.duration,
    )
    environment = TrafficRLEnvironment(scenario)
    agent = QLearningAgent.load(
        args.model,
        seed=args.seed_start,
        epsilon=0.0,
    )

    results = []
    for offset in range(args.seeds):
        seed = args.seed_start + offset
        results.append(
            run_episode(
                environment,
                agent,
                seed=seed,
                training=False,
            )
        )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    with args.output.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(results[0].keys()),
        )
        writer.writeheader()
        writer.writerows(results)

    waits = [
        float(row["average_completed_wait_s"])
        for row in results
    ]
    queues = [
        float(row["mean_queue"])
        for row in results
    ]
    throughput = [
        float(row["throughput_per_min"])
        for row in results
    ]

    print("=== AVALIAÇÃO Q-LEARNING | EPSILON=0 ===")
    print(f"Seeds: {args.seeds}")
    print(
        "Espera média: "
        f"{statistics.mean(waits):.2f} s"
    )
    print(
        "Fila média: "
        f"{statistics.mean(queues):.2f}"
    )
    print(
        "Throughput médio: "
        f"{statistics.mean(throughput):.2f} veh/min"
    )
    print(f"CSV: {args.output}")


if __name__ == "__main__":
    main()
