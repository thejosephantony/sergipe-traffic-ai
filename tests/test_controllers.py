from sergipe_traffic_ai.controllers import AdaptiveController, FixedController
from sergipe_traffic_ai.traffic.models import Direction, Intersection, Vehicle


def test_fixed_controller_alternates_phases():
    controller = FixedController(phase_steps=10)
    intersection = Intersection()
    assert controller.choose_green(intersection, 0) is Direction.NORTH_SOUTH
    assert controller.choose_green(intersection, 10) is Direction.EAST_WEST


def test_adaptive_controller_prefers_larger_queue_after_minimum_green():
    controller = AdaptiveController(min_green_steps=1)
    intersection = Intersection()
    intersection.ew.queue.extend([Vehicle(i, Direction.EAST_WEST) for i in range(5)])
    assert controller.choose_green(intersection, 1) is Direction.EAST_WEST
