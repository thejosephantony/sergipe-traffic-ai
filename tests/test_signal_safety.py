from sergipe_traffic_ai.controllers.adaptive_controller import (
    AdaptiveTrafficController,
)
from sergipe_traffic_ai.controllers.fixed_controller import (
    FixedTrafficController,
)


def scenario():
    return {
        "scenario": {
            "controller": {
                "min_green_s": 2.0,
                "max_green_s": 10.0,
                "yellow_s": 3.0,
                "all_red_s": 1.0,
                "cycle_duration_s": 78.0,
            }
        }
    }


def observation(
    queue_barao=0,
    queue_augusto=0,
    wait_barao=0.0,
    wait_augusto=0.0,
    time_step_s=0.2,
):
    return {
        "queue_barao": queue_barao,
        "queue_augusto": queue_augusto,
        "wait_barao": wait_barao,
        "wait_augusto": wait_augusto,
        "time_step_s": time_step_s,
    }


def test_fixed_controller_uses_yellow_and_all_red_between_greens():
    controller = FixedTrafficController()
    controller.reset(scenario())

    assert controller.decide({}, 0.0) == "BARAO_GREEN"
    assert controller.decide({}, 34.9) == "BARAO_GREEN"
    assert controller.decide({}, 35.0) == "BARAO_YELLOW"
    assert controller.decide({}, 37.9) == "BARAO_YELLOW"
    assert controller.decide({}, 38.0) == "ALL_RED_TO_AUGUSTO"
    assert controller.decide({}, 39.0) == "AUGUSTO_GREEN"
    assert controller.decide({}, 74.0) == "AUGUSTO_YELLOW"
    assert controller.decide({}, 77.0) == "ALL_RED_TO_BARAO"


def test_adaptive_controller_never_jumps_directly_between_conflicting_greens():
    controller = AdaptiveTrafficController(
        min_green_s=0.4,
        max_green_s=20.0,
        yellow_duration_s=0.4,
        all_red_s=0.2,
    )
    controller.reset(
        {
            "scenario": {
                "controller": {
                    "min_green_s": 0.4,
                    "max_green_s": 20.0,
                    "yellow_s": 0.4,
                    "all_red_s": 0.2,
                }
            }
        }
    )

    obs = observation(
        queue_barao=0,
        queue_augusto=10,
        time_step_s=0.2,
    )

    phases = [controller.current_phase]
    for step in range(10):
        phases.append(controller.decide(obs, step * 0.2))

    assert "BARAO_YELLOW" in phases
    assert "ALL_RED_TO_AUGUSTO" in phases
    assert "AUGUSTO_GREEN" in phases

    barao_index = phases.index("BARAO_YELLOW")
    all_red_index = phases.index("ALL_RED_TO_AUGUSTO")
    augusto_index = phases.index("AUGUSTO_GREEN")

    assert barao_index < all_red_index < augusto_index


def test_all_red_phase_has_no_axis_with_green():
    controller = FixedTrafficController(
        green_duration_s=1.0,
        yellow_duration_s=1.0,
        all_red_s=1.0,
    )

    assert controller.decide({}, 2.1) == "ALL_RED_TO_AUGUSTO"
