from __future__ import annotations

from typing import Any

from sergipe_traffic_ai.controllers.q_learning import (
    ACTION_REQUEST_SWITCH,
    QLearningStateEncoder,
    SafeSignalPhaseMachine,
    State,
)
from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    BARAO_AXIS,
    TrafficDemandSimulator,
)


class TrafficRLEnvironment:
    """Ambiente causal e seguro para treinamento de Q-Learning tabular."""

    def __init__(
        self,
        scenario_config: dict[str, Any],
        decision_interval_s: float | None = None,
    ) -> None:
        self.scenario_config = scenario_config
        q_cfg = scenario_config.get("scenario", {}).get("q_learning", {})

        self.decision_interval_s = float(
            decision_interval_s
            if decision_interval_s is not None
            else q_cfg.get("decision_interval_s", 1.0)
        )
        self.queue_weight = float(
            q_cfg.get("reward_queue_weight", 1.0)
        )
        self.wait_weight = float(
            q_cfg.get("reward_wait_weight", 0.05)
        )
        self.throughput_weight = float(
            q_cfg.get("reward_throughput_weight", 0.5)
        )
        self.switch_penalty = float(
            q_cfg.get("switch_penalty", 0.1)
        )

        self.simulator = TrafficDemandSimulator(scenario_config)
        self.phase_machine = SafeSignalPhaseMachine()
        self.encoder = QLearningStateEncoder()
        self.phase_machine.reset(scenario_config)

    def reset(self, seed: int | None = None) -> State:
        if seed is not None:
            self.simulator.seed = int(seed)

        self.simulator.reset()
        self.phase_machine.reset(self.scenario_config)
        return self.state()

    def observation(self) -> dict[str, float]:
        return {
            "queue_barao": float(
                self.simulator.queue_length(BARAO_AXIS)
            ),
            "queue_augusto": float(
                self.simulator.queue_length(AUGUSTO_AXIS)
            ),
            "wait_barao": self.simulator.average_wait(BARAO_AXIS),
            "wait_augusto": self.simulator.average_wait(AUGUSTO_AXIS),
            "time_step_s": float(self.simulator.time_step_s),
            "conflict_zone_occupied": self.simulator.conflict_zone_occupied(),
        }

    def state(self) -> State:
        return self.encoder.encode(
            self.observation(),
            self.phase_machine,
        )

    def step(
        self,
        action: int,
    ) -> tuple[State, float, bool, dict[str, Any]]:
        if action not in (0, 1):
            raise ValueError(f"Ação inválida: {action}")

        time_step_s = float(self.simulator.time_step_s)
        substeps = max(
            1,
            round(self.decision_interval_s / time_step_s),
        )

        completed_before = self.simulator.completed_vehicles_count
        transition_started = False
        is_running = True

        for substep in range(substeps):
            request_switch = (
                action == ACTION_REQUEST_SWITCH
                and substep == 0
            )
            phase, started = self.phase_machine.tick(
                time_step_s,
                request_switch=request_switch,
                conflict_zone_occupied=self.simulator.conflict_zone_occupied(),
            )
            transition_started = transition_started or started

            self.simulator.generate_vehicles_step()
            is_running = self.simulator.step(phase)
            if not is_running:
                break

        observation = self.observation()
        queue_total = (
            observation["queue_barao"]
            + observation["queue_augusto"]
        )
        wait_total = (
            observation["wait_barao"]
            + observation["wait_augusto"]
        )
        completed_delta = (
            self.simulator.completed_vehicles_count
            - completed_before
        )

        reward = (
            -self.queue_weight * queue_total
            -self.wait_weight * wait_total
            +self.throughput_weight * completed_delta
        )
        if transition_started:
            reward -= self.switch_penalty

        done = (
            not is_running
            or self.simulator.current_time
            >= self.simulator.duration_s
        )
        next_state = self.state()

        info = {
            "phase": self.phase_machine.current_phase,
            "time_in_phase": self.phase_machine.time_in_phase,
            "switch_requested": action == ACTION_REQUEST_SWITCH,
            "switch_accepted": transition_started,
            "completed_delta": completed_delta,
            "completed_vehicles": (
                self.simulator.completed_vehicles_count
            ),
            "average_completed_wait_s": (
                self.simulator.average_completed_wait()
            ),
            "queue_total": queue_total,
        }

        return next_state, float(reward), done, info
