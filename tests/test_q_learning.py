from pathlib import Path

from sergipe_traffic_ai.controllers.q_learning import (
    ACTION_HOLD,
    ACTION_REQUEST_SWITCH,
    ALL_RED_TO_AUGUSTO,
    AUGUSTO_GREEN,
    BARAO_GREEN,
    BARAO_YELLOW,
    QLearningAgent,
    QLearningStateEncoder,
    QLearningTrafficController,
    SafeSignalPhaseMachine,
)
from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment
from sergipe_traffic_ai.training.q_learning import train_q_learning


def scenario(
    duration_s: float = 10.0,
    model_path: str = "models/q_learning_aracaju.json",
):
    return {
        "scenario": {
            "id": "q_learning_test",
            "seed": 42,
            "duration_s": duration_s,
            "time_step_s": 0.2,
            "demand": {
                "axis_barao_maynard_rate": 0.0,
                "axis_augusto_franco_rate": 0.0,
            },
            "controller": {
                "min_green_s": 0.4,
                "max_green_s": 2.0,
                "yellow_s": 0.4,
                "all_red_s": 0.2,
            },
            "q_learning": {
                "model_path": model_path,
                "decision_interval_s": 0.2,
                "alpha": 0.5,
                "gamma": 0.9,
                "epsilon_start": 0.5,
                "epsilon_min": 0.05,
                "epsilon_decay": 0.9,
                "reward_queue_weight": 1.0,
                "reward_wait_weight": 0.05,
                "reward_throughput_weight": 0.5,
                "switch_penalty": 0.1,
            },
        }
    }


def test_state_encoder_discretizes_queues_and_phase():
    machine = SafeSignalPhaseMachine(
        min_green_s=5.0,
        max_green_s=20.0,
    )
    encoder = QLearningStateEncoder()

    state = encoder.encode(
        {
            "queue_barao": 4,
            "queue_augusto": 13,
        },
        machine,
    )

    assert state == (2, 4, 0, 0)


def test_q_learning_update_uses_bellman_equation():
    agent = QLearningAgent(
        alpha=0.5,
        gamma=0.9,
        epsilon=0.0,
    )
    state = (0, 0, 0, 0)
    next_state = (1, 0, 0, 0)
    agent.q_table[next_state] = [2.0, 1.0]

    agent.update(
        state,
        ACTION_HOLD,
        reward=1.0,
        next_state=next_state,
        done=False,
    )

    assert agent.q_values(state)[ACTION_HOLD] == 1.4


def test_safe_phase_machine_never_jumps_green_to_conflicting_green():
    machine = SafeSignalPhaseMachine(
        min_green_s=0.4,
        max_green_s=5.0,
        yellow_s=0.4,
        all_red_s=0.2,
    )

    phase, accepted = machine.tick(
        0.2,
        request_switch=True,
    )
    assert phase == BARAO_GREEN
    assert accepted is False

    phase, accepted = machine.tick(
        0.2,
        request_switch=True,
    )
    assert phase == BARAO_YELLOW
    assert accepted is True

    phases = [phase]
    for _ in range(4):
        phase, _ = machine.tick(0.2)
        phases.append(phase)

    assert ALL_RED_TO_AUGUSTO in phases
    assert AUGUSTO_GREEN in phases
    assert phases.index(ALL_RED_TO_AUGUSTO) < phases.index(AUGUSTO_GREEN)


def test_rl_environment_applies_action_through_safe_phase_machine():
    env = TrafficRLEnvironment(
        scenario(),
        decision_interval_s=0.2,
    )
    env.reset(seed=10)

    env.phase_machine.time_in_phase = 0.4
    _, _, _, info = env.step(ACTION_REQUEST_SWITCH)

    assert info["switch_requested"] is True
    assert info["switch_accepted"] is True
    assert info["phase"] == BARAO_YELLOW


def test_q_table_round_trip(tmp_path: Path):
    model_path = tmp_path / "q_table.json"
    agent = QLearningAgent(
        alpha=0.2,
        gamma=0.8,
        epsilon=0.3,
        seed=7,
    )
    agent.q_table[(1, 2, 0, 1)] = [1.25, -0.5]
    agent.save(model_path, metadata={"test": True})

    loaded = QLearningAgent.load(
        model_path,
        seed=7,
        epsilon=0.0,
    )

    assert loaded.q_table[(1, 2, 0, 1)] == [1.25, -0.5]
    assert loaded.epsilon == 0.0


def test_short_training_populates_q_table():
    agent, history = train_q_learning(
        scenario(duration_s=3.0),
        episodes=3,
        duration_s=3.0,
        seed=20,
    )

    assert len(history) == 3
    assert agent.q_table
    assert agent.epsilon < 0.5


def test_trained_controller_loads_model_and_respects_safety(tmp_path: Path):
    model_path = tmp_path / "trained.json"
    agent = QLearningAgent(
        epsilon=0.0,
        seed=42,
    )
    agent.q_table[(0, 0, 0, 0)] = [0.0, 10.0]
    agent.save(model_path)

    config = scenario(
        model_path=str(model_path),
    )
    controller = QLearningTrafficController(
        model_path=str(model_path),
        decision_interval_s=0.2,
    )
    controller.reset(config)

    first_phase = controller.decide(
        {
            "queue_barao": 0,
            "queue_augusto": 0,
            "time_step_s": 0.2,
        },
        0.0,
    )

    assert first_phase == BARAO_GREEN
