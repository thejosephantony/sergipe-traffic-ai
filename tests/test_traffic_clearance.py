import pygame

from sergipe_traffic_ai.controllers.adaptive_controller import (
    AdaptiveTrafficController,
)
from sergipe_traffic_ai.controllers.fixed_controller import (
    FixedTrafficController,
)
from sergipe_traffic_ai.controllers.q_learning import (
    ACTION_HOLD,
    ALL_RED_TO_AUGUSTO,
    AUGUSTO_GREEN,
    BARAO_GREEN,
    SafeSignalPhaseMachine,
)
from sergipe_traffic_ai.controllers.rl_environment import TrafficRLEnvironment
from sergipe_traffic_ai.traffic.demand import (
    BARAO_AXIS,
    BARAO_EASTBOUND,
    TrafficDemandSimulator,
    Vehicle,
)
from sergipe_traffic_ai.visual.app import draw_vehicle, world_to_screen
from sergipe_traffic_ai.visual.vehicle_style import (
    VEHICLE_SCALE_PX_PER_M,
    length_is_safe_for_gap,
    sprite_dimensions,
)


def scenario():
    return {
        "scenario": {
            "seed": 8,
            "time_step_s": 0.2,
            "duration_s": 30,
            "demand": {
                "axis_barao_maynard_rate": 0.0,
                "axis_augusto_franco_rate": 0.0,
            },
            "controller": {
                "min_green_s": 0.4,
                "max_green_s": 2.0,
                "yellow_s": 0.4,
                "all_red_s": 0.2,
                "cycle_duration_s": 5.2,
            },
            "q_learning": {
                "decision_interval_s": 0.2,
            },
        },
    }


def observation(occupied: bool) -> dict:
    return {
        "queue_barao": 0,
        "queue_augusto": 0,
        "time_step_s": 0.2,
        "conflict_zone_occupied": occupied,
    }


def test_sprite_lengths_fit_physical_spacing():
    for vehicle_type in ("car", "motorcycle", "bus"):
        length_px, width_px = sprite_dimensions(vehicle_type)
        assert length_px > width_px
        assert length_is_safe_for_gap(vehicle_type, 2.5)


def test_visual_vehicles_do_not_overlap_when_physically_spaced():
    leader = Vehicle(1, BARAO_AXIS, "Leste", "bus", BARAO_EASTBOUND)
    follower = Vehicle(2, BARAO_AXIS, "Leste", "car", BARAO_EASTBOUND)
    leader.position = -10.0
    follower.position = leader.position - leader.length_m - 2.5

    x1, y1, _ = world_to_screen(leader)
    x2, y2, _ = world_to_screen(follower)
    l1, w1 = sprite_dimensions("bus")
    l2, w2 = sprite_dimensions("car")

    leader_rect = pygame.Rect(x1 - l1 // 2, y1 - w1 // 2, l1, w1)
    follower_rect = pygame.Rect(x2 - l2 // 2, y2 - w2 // 2, l2, w2)

    assert not leader_rect.colliderect(follower_rect)
    assert x1 - x2 >= (
        (leader.length_m + follower.length_m) / 2.0
        + 2.5
    ) * VEHICLE_SCALE_PX_PER_M - 2


def test_render_all_vehicle_types_without_display():
    canvas = pygame.Surface((240, 160))
    for index, vehicle_type in enumerate(("car", "motorcycle", "bus")):
        for direction in ("east", "west", "north", "south"):
            draw_vehicle(
                canvas,
                x=30 + index * 80,
                y=20 + ("east", "west", "north", "south").index(direction) * 40,
                horizontal=direction in ("east", "west"),
                vehicle_type=vehicle_type,
                queued=index == 0,
                heading=direction,
            )


def test_conflict_occupancy_ignores_vehicles_before_stop_line():
    sim = TrafficDemandSimulator(scenario())
    vehicle = sim._spawn_vehicle(BARAO_AXIS, "Leste", "bus", BARAO_EASTBOUND)
    assert vehicle is not None
    assert not sim.conflict_zone_occupied()

    vehicle.position = 3.0
    assert sim.conflict_zone_occupied()

    vehicle.position = 0.0
    assert not sim.conflict_zone_occupied()


def test_fixed_controller_holds_all_red_during_crossing():
    controller = FixedTrafficController(
        green_duration_s=1.0,
        yellow_duration_s=0.2,
        all_red_s=0.2,
    )
    controller.decide(observation(False), 0.0)
    assert controller.decide(observation(False), 1.0) == "BARAO_YELLOW"
    assert controller.decide(observation(False), 1.2) == ALL_RED_TO_AUGUSTO

    for now in (1.4, 1.6, 1.8, 2.0):
        assert controller.decide(observation(True), now) == ALL_RED_TO_AUGUSTO
        assert controller.clearance_hold_active

    assert controller.decide(observation(False), 2.2) == AUGUSTO_GREEN
    assert not controller.clearance_hold_active


def test_adaptive_controller_holds_all_red_during_crossing():
    controller = AdaptiveTrafficController()
    controller.reset(scenario())
    controller.current_phase = ALL_RED_TO_AUGUSTO
    controller.time_in_current_phase = 0.2

    assert controller.decide(observation(True), 1.0) == ALL_RED_TO_AUGUSTO
    assert controller.decide(observation(False), 1.2) == AUGUSTO_GREEN


def test_q_learning_phase_machine_holds_all_red_during_crossing():
    machine = SafeSignalPhaseMachine(
        min_green_s=0.4,
        max_green_s=2.0,
        yellow_s=0.4,
        all_red_s=0.2,
    )
    machine.current_phase = ALL_RED_TO_AUGUSTO
    machine.time_in_phase = 0.2

    phase, _ = machine.tick(
        0.2,
        conflict_zone_occupied=True,
    )
    assert phase == ALL_RED_TO_AUGUSTO

    phase, _ = machine.tick(
        0.2,
        conflict_zone_occupied=False,
    )
    assert phase == AUGUSTO_GREEN


def test_rl_environment_does_not_release_green_until_vehicle_exits():
    env = TrafficRLEnvironment(scenario(), decision_interval_s=0.2)
    env.reset(seed=8)
    vehicle = env.simulator._spawn_vehicle(
        BARAO_AXIS,
        "Leste",
        "bus",
        BARAO_EASTBOUND,
    )
    assert vehicle is not None
    vehicle.position = 10.0
    env.phase_machine.current_phase = ALL_RED_TO_AUGUSTO
    env.phase_machine.time_in_phase = 0.2

    _, _, _, info = env.step(ACTION_HOLD)
    assert info["phase"] == ALL_RED_TO_AUGUSTO

    vehicle.position = env.simulator.exit_position_m - 0.01
    _, _, _, info = env.step(ACTION_HOLD)
    assert info["phase"] == ALL_RED_TO_AUGUSTO

    _, _, _, info = env.step(ACTION_HOLD)
    assert info["phase"] == AUGUSTO_GREEN


def test_simulator_preserves_minimum_gap_in_same_lane():
    config = scenario()
    config["scenario"]["duration_s"] = 50.0
    config["scenario"]["demand"] = {
        "axis_barao_maynard_rate": 2.0,
        "axis_augusto_franco_rate": 0.0,
    }
    sim = TrafficDemandSimulator(config)
    for _ in range(220):
        sim.generate_vehicles_step()
        sim.step(BARAO_GREEN)
        for movement in ("barao_eastbound", "barao_westbound"):
            vehicles = sorted(
                (v for v in sim.active_vehicles if v.movement == movement),
                key=lambda vehicle: vehicle.position,
                reverse=True,
            )
            for leader, follower in zip(vehicles, vehicles[1:]):
                assert (
                    leader.position - follower.position
                    >= leader.length_m + sim.min_gap_m - 1e-6
                )
