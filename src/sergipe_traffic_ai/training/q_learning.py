from __future__ import annotations

import copy
from typing import Any

from sergipe_traffic_ai.controllers.q_learning import QLearningAgent
from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment


def q_learning_config(
    scenario: dict[str, Any],
) -> dict[str, Any]:
    return scenario.get("scenario", {}).get("q_learning", {})


def build_agent(
    scenario: dict[str, Any],
    seed: int,
) -> QLearningAgent:
    cfg = q_learning_config(scenario)
    return QLearningAgent(
        alpha=float(cfg.get("alpha", 0.15)),
        gamma=float(cfg.get("gamma", 0.95)),
        epsilon=float(cfg.get("epsilon_start", 1.0)),
        epsilon_min=float(cfg.get("epsilon_min", 0.05)),
        epsilon_decay=float(cfg.get("epsilon_decay", 0.97)),
        seed=seed,
    )


def scenario_for_episode(
    scenario: dict[str, Any],
    duration_s: float | None,
) -> dict[str, Any]:
    config = copy.deepcopy(scenario)
    if duration_s is not None:
        config["scenario"]["duration_s"] = float(duration_s)
    return config


def run_episode(
    environment: TrafficRLEnvironment,
    agent: QLearningAgent,
    seed: int,
    training: bool,
) -> dict[str, float | int]:
    state = environment.reset(seed=seed)
    done = False
    total_reward = 0.0
    decision_count = 0
    queue_sum = 0.0
    max_queue = 0.0
    accepted_switches = 0

    while not done:
        action = agent.choose_action(
            state,
            explore=training,
        )
        next_state, reward, done, info = environment.step(action)

        if training:
            agent.update(
                state,
                action,
                reward,
                next_state,
                done,
            )

        state = next_state
        total_reward += reward
        decision_count += 1

        queue_total = float(info["queue_total"])
        queue_sum += queue_total
        max_queue = max(max_queue, queue_total)
        accepted_switches += int(
            bool(info["switch_accepted"])
        )

    simulator = environment.simulator
    mean_queue = (
        queue_sum / decision_count
        if decision_count
        else 0.0
    )
    duration_minutes = max(
        simulator.current_time / 60.0,
        1e-9,
    )
    throughput_per_min = (
        simulator.completed_vehicles_count
        / duration_minutes
    )

    return {
        "seed": seed,
        "reward": round(total_reward, 4),
        "decisions": decision_count,
        "vehicles_generated": simulator.vehicle_counter,
        "vehicles_completed": simulator.completed_vehicles_count,
        "average_completed_wait_s": round(
            simulator.average_completed_wait(),
            4,
        ),
        "mean_queue": round(mean_queue, 4),
        "max_queue": int(max_queue),
        "throughput_per_min": round(
            throughput_per_min,
            4,
        ),
        "accepted_switches": accepted_switches,
    }


def train_q_learning(
    scenario: dict[str, Any],
    episodes: int = 200,
    duration_s: float | None = 600.0,
    seed: int = 42,
) -> tuple[QLearningAgent, list[dict[str, Any]]]:
    config = scenario_for_episode(
        scenario,
        duration_s,
    )
    environment = TrafficRLEnvironment(config)
    agent = build_agent(config, seed=seed)
    history: list[dict[str, Any]] = []

    for episode in range(episodes):
        episode_seed = seed + episode
        metrics = run_episode(
            environment,
            agent,
            seed=episode_seed,
            training=True,
        )
        metrics["episode"] = episode + 1
        metrics["epsilon"] = round(agent.epsilon, 6)
        metrics["q_states"] = len(agent.q_table)
        history.append(metrics)
        agent.decay_exploration()

    return agent, history
