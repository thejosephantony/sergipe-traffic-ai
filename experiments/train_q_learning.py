from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from sergipe_traffic_ai.training.q_learning import train_q_learning


DEFAULT_SCENARIO = Path("scenarios/aracaju_barao_augusto.json")
DEFAULT_MODEL = Path("models/q_learning_aracaju.json")
DEFAULT_HISTORY = Path(
    "experiments/output/q_learning/training_history.csv"
)


def load_scenario(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_history(
    path: Path,
    history: list[dict],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not history:
        return

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(history[0].keys()),
        )
        writer.writeheader()
        writer.writerows(history)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Treina o controlador semafórico com Q-Learning tabular."
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=200,
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=600.0,
        help="Duração simulada de cada episódio em segundos.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )
    parser.add_argument(
        "--model",
        type=Path,
        default=DEFAULT_MODEL,
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=DEFAULT_HISTORY,
    )
    args = parser.parse_args()

    scenario = load_scenario(args.scenario)
    agent, history = train_q_learning(
        scenario,
        episodes=args.episodes,
        duration_s=args.duration,
        seed=args.seed,
    )

    agent.save(
        args.model,
        metadata={
            "scenario": scenario["scenario"]["id"],
            "episodes": args.episodes,
            "episode_duration_s": args.duration,
            "seed": args.seed,
            "training_seeds": [
                args.seed,
                args.seed + args.episodes - 1,
            ],
        },
    )
    write_history(args.history, history)

    last = history[-1]
    print("=== Q-LEARNING TREINADO ===")
    print(f"Episódios: {args.episodes}")
    print(f"Estados visitados: {len(agent.q_table)}")
    print(f"Epsilon final: {agent.epsilon:.4f}")
    print(f"Reward último episódio: {last['reward']}")
    print(
        "Espera média concluída (último): "
        f"{last['average_completed_wait_s']} s"
    )
    print(
        "Throughput último: "
        f"{last['throughput_per_min']} veh/min"
    )
    print(f"Modelo: {args.model}")
    print(f"Histórico: {args.history}")


if __name__ == "__main__":
    main()
