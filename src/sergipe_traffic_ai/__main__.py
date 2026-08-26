from __future__ import annotations

import argparse

from sergipe_traffic_ai.controllers import AdaptiveController, FixedController
from sergipe_traffic_ai.simulation import Simulation


def build_controller(name: str):
    if name == "fixed":
        return FixedController()
    if name == "adaptive":
        return AdaptiveController()
    raise ValueError(f"Unknown controller: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sergipe Traffic AI MVP")
    parser.add_argument("--controller", choices=["fixed", "adaptive"], default="fixed")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    simulation = Simulation(build_controller(args.controller), seed=args.seed)
    summary = simulation.run(args.steps)
    for key, value in summary.items():
        print(f"{key}={value}")


if __name__ == "__main__":
    main()
