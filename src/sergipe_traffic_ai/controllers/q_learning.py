from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


ACTION_HOLD = 0
ACTION_REQUEST_SWITCH = 1
ACTIONS = (ACTION_HOLD, ACTION_REQUEST_SWITCH)

BARAO_GREEN = "BARAO_GREEN"
BARAO_YELLOW = "BARAO_YELLOW"
ALL_RED_TO_AUGUSTO = "ALL_RED_TO_AUGUSTO"
AUGUSTO_GREEN = "AUGUSTO_GREEN"
AUGUSTO_YELLOW = "AUGUSTO_YELLOW"
ALL_RED_TO_BARAO = "ALL_RED_TO_BARAO"

GREEN_PHASES = {BARAO_GREEN, AUGUSTO_GREEN}
State = tuple[int, int, int, int]


class SafeSignalPhaseMachine:
    """Aplica as transições de segurança independentemente da decisão da IA."""

    def __init__(
        self,
        min_green_s: float = 15.0,
        max_green_s: float = 60.0,
        yellow_s: float = 3.0,
        all_red_s: float = 1.0,
    ) -> None:
        self.min_green_s = min_green_s
        self.max_green_s = max_green_s
        self.yellow_s = yellow_s
        self.all_red_s = all_red_s
        self.current_phase = BARAO_GREEN
        self.time_in_phase = 0.0

    def reset(self, scenario: dict[str, Any] | None = None) -> None:
        if scenario is not None:
            controller_cfg = scenario.get("scenario", {}).get("controller", {})
            self.min_green_s = float(
                controller_cfg.get("min_green_s", self.min_green_s)
            )
            self.max_green_s = float(
                controller_cfg.get("max_green_s", self.max_green_s)
            )
            self.yellow_s = float(
                controller_cfg.get("yellow_s", self.yellow_s)
            )
            self.all_red_s = float(
                controller_cfg.get("all_red_s", self.all_red_s)
            )

        self.current_phase = BARAO_GREEN
        self.time_in_phase = 0.0

    @property
    def can_request_switch(self) -> bool:
        return (
            self.current_phase in GREEN_PHASES
            and self.time_in_phase >= self.min_green_s
        )

    def _start_transition(self) -> None:
        if self.current_phase == BARAO_GREEN:
            self.current_phase = BARAO_YELLOW
        elif self.current_phase == AUGUSTO_GREEN:
            self.current_phase = AUGUSTO_YELLOW
        self.time_in_phase = 0.0

    def tick(
        self,
        time_step_s: float,
        request_switch: bool = False,
        conflict_zone_occupied: bool = False,
    ) -> tuple[str, bool]:
        """Avança a máquina e informa se uma transição verde->amarelo começou."""
        dt = max(0.0, float(time_step_s))
        self.time_in_phase += dt
        transition_started = False

        if self.current_phase in GREEN_PHASES:
            forced_switch = self.time_in_phase >= self.max_green_s
            requested_switch = (
                request_switch
                and self.time_in_phase >= self.min_green_s
            )

            if forced_switch or requested_switch:
                self._start_transition()
                transition_started = True

            return self.current_phase, transition_started

        if (
            self.current_phase == BARAO_YELLOW
            and self.time_in_phase >= self.yellow_s
        ):
            self.current_phase = ALL_RED_TO_AUGUSTO
            self.time_in_phase = 0.0
        elif (
            self.current_phase == AUGUSTO_YELLOW
            and self.time_in_phase >= self.yellow_s
        ):
            self.current_phase = ALL_RED_TO_BARAO
            self.time_in_phase = 0.0
        elif (
            self.current_phase == ALL_RED_TO_AUGUSTO
            and self.time_in_phase >= self.all_red_s
            and not conflict_zone_occupied
        ):
            self.current_phase = AUGUSTO_GREEN
            self.time_in_phase = 0.0
        elif (
            self.current_phase == ALL_RED_TO_BARAO
            and self.time_in_phase >= self.all_red_s
            and not conflict_zone_occupied
        ):
            self.current_phase = BARAO_GREEN
            self.time_in_phase = 0.0

        return self.current_phase, transition_started


class QLearningStateEncoder:
    """Discretiza o estado contínuo para Q-Learning tabular."""

    def __init__(
        self,
        queue_thresholds: tuple[int, ...] = (0, 3, 7, 12),
    ) -> None:
        self.queue_thresholds = queue_thresholds

    def queue_bin(self, queue_size: float) -> int:
        value = max(0.0, float(queue_size))
        for index, threshold in enumerate(self.queue_thresholds):
            if value <= threshold:
                return index
        return len(self.queue_thresholds)

    @staticmethod
    def phase_code(phase: str) -> int:
        if phase == BARAO_GREEN:
            return 0
        if phase == AUGUSTO_GREEN:
            return 1
        return 2

    @staticmethod
    def time_code(
        phase: str,
        time_in_phase: float,
        min_green_s: float,
        max_green_s: float,
    ) -> int:
        if phase not in GREEN_PHASES:
            return 0
        if time_in_phase < min_green_s:
            return 0

        late_threshold = max(
            min_green_s,
            0.75 * max_green_s,
        )
        if time_in_phase < late_threshold:
            return 1
        return 2

    def encode(
        self,
        observation: dict[str, float],
        phase_machine: SafeSignalPhaseMachine,
    ) -> State:
        return (
            self.queue_bin(observation.get("queue_barao", 0.0)),
            self.queue_bin(observation.get("queue_augusto", 0.0)),
            self.phase_code(phase_machine.current_phase),
            self.time_code(
                phase_machine.current_phase,
                phase_machine.time_in_phase,
                phase_machine.min_green_s,
                phase_machine.max_green_s,
            ),
        )


class QLearningAgent:
    """Agente tabular epsilon-greedy com persistência em JSON."""

    def __init__(
        self,
        alpha: float = 0.15,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.97,
        seed: int = 42,
    ) -> None:
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.epsilon = float(epsilon)
        self.epsilon_min = float(epsilon_min)
        self.epsilon_decay = float(epsilon_decay)
        self.rng = random.Random(seed)
        self.q_table: dict[State, list[float]] = {}

    def q_values(self, state: State) -> list[float]:
        return self.q_table.setdefault(state, [0.0, 0.0])

    def choose_action(
        self,
        state: State,
        explore: bool = True,
    ) -> int:
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(ACTIONS)

        values = self.q_values(state)
        best_value = max(values)
        best_actions = [
            action
            for action, value in enumerate(values)
            if value == best_value
        ]
        return self.rng.choice(best_actions)

    def update(
        self,
        state: State,
        action: int,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        if action not in ACTIONS:
            raise ValueError(f"Ação inválida para Q-Learning: {action}")

        values = self.q_values(state)
        current_q = values[action]

        if done:
            target = float(reward)
        else:
            target = float(reward) + self.gamma * max(
                self.q_values(next_state)
            )

        values[action] = current_q + self.alpha * (target - current_q)

    def decay_exploration(self) -> None:
        self.epsilon = max(
            self.epsilon_min,
            self.epsilon * self.epsilon_decay,
        )

    def save(
        self,
        path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "algorithm": "tabular_q_learning",
            "version": 1,
            "hyperparameters": {
                "alpha": self.alpha,
                "gamma": self.gamma,
                "epsilon": self.epsilon,
                "epsilon_min": self.epsilon_min,
                "epsilon_decay": self.epsilon_decay,
            },
            "metadata": metadata or {},
            "q_table": [
                {
                    "state": list(state),
                    "q_values": values,
                }
                for state, values in sorted(self.q_table.items())
            ],
        }

        with path.open("w", encoding="utf-8") as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")

    @classmethod
    def load(
        cls,
        path: Path,
        seed: int = 42,
        epsilon: float = 0.0,
    ) -> "QLearningAgent":
        with path.open("r", encoding="utf-8-sig") as file:
            payload = json.load(file)

        hyperparameters = payload.get("hyperparameters", {})
        agent = cls(
            alpha=float(hyperparameters.get("alpha", 0.15)),
            gamma=float(hyperparameters.get("gamma", 0.95)),
            epsilon=epsilon,
            epsilon_min=float(
                hyperparameters.get("epsilon_min", 0.05)
            ),
            epsilon_decay=float(
                hyperparameters.get("epsilon_decay", 0.97)
            ),
            seed=seed,
        )

        for row in payload.get("q_table", []):
            state = tuple(int(value) for value in row["state"])
            if len(state) != 4:
                raise ValueError("Estado inválido no arquivo Q-table.")
            agent.q_table[state] = [
                float(value)
                for value in row["q_values"]
            ]

        return agent


class QLearningTrafficController:
    """Executa uma Q-table treinada respeitando a máquina de segurança."""

    def __init__(
        self,
        model_path: str = "models/q_learning_aracaju.json",
        decision_interval_s: float = 1.0,
        seed: int = 42,
    ) -> None:
        self.model_path = Path(model_path)
        self.decision_interval_s = float(decision_interval_s)
        self.seed = seed
        self.phase_machine = SafeSignalPhaseMachine()
        self.encoder = QLearningStateEncoder()
        self.agent: QLearningAgent | None = None
        self.decision_elapsed_s = 0.0
        self.current_phase = BARAO_GREEN

    def reset(self, scenario: dict[str, Any]) -> None:
        q_cfg = scenario.get("scenario", {}).get("q_learning", {})
        self.model_path = Path(
            q_cfg.get("model_path", str(self.model_path))
        )
        self.decision_interval_s = float(
            q_cfg.get(
                "decision_interval_s",
                self.decision_interval_s,
            )
        )
        self.seed = int(
            scenario.get("scenario", {}).get("seed", self.seed)
        )

        if not self.model_path.exists():
            raise FileNotFoundError(
                "Modelo Q-Learning não encontrado em "
                f"{self.model_path}. Execute "
                "'python experiments/train_q_learning.py' primeiro."
            )

        self.agent = QLearningAgent.load(
            self.model_path,
            seed=self.seed,
            epsilon=0.0,
        )
        self.phase_machine.reset(scenario)
        self.current_phase = self.phase_machine.current_phase
        self.decision_elapsed_s = self.decision_interval_s

    def decide(
        self,
        observation: dict[str, float],
        now: float,
    ) -> str:
        del now

        if self.agent is None:
            raise RuntimeError("Controlador Q-Learning ainda não foi inicializado.")

        time_step_s = float(observation.get("time_step_s", 0.2))
        self.decision_elapsed_s += time_step_s
        request_switch = False

        if (
            self.phase_machine.current_phase in GREEN_PHASES
            and self.decision_elapsed_s >= self.decision_interval_s
        ):
            state = self.encoder.encode(
                observation,
                self.phase_machine,
            )
            action = self.agent.choose_action(
                state,
                explore=False,
            )
            request_switch = action == ACTION_REQUEST_SWITCH
            self.decision_elapsed_s = 0.0

        previous_phase = self.phase_machine.current_phase
        self.current_phase, _ = self.phase_machine.tick(
            time_step_s,
            request_switch=request_switch,
            conflict_zone_occupied=bool(
                observation.get("conflict_zone_occupied", False)
            ),
        )

        if (
            previous_phase != self.current_phase
            and self.current_phase in GREEN_PHASES
        ):
            self.decision_elapsed_s = 0.0

        return self.current_phase

    def on_transition(
        self,
        previous_phase: str,
        new_phase: str,
    ) -> None:
        del previous_phase, new_phase
