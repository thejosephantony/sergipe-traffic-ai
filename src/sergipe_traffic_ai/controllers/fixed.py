from sergipe_traffic_ai.controllers.base import TrafficController
from sergipe_traffic_ai.traffic.models import Direction, Intersection


class FixedController(TrafficController):
    name = "fixed"

    def __init__(self, phase_steps: int = 30) -> None:
        if phase_steps <= 0:
            raise ValueError("phase_steps must be positive")
        self.phase_steps = phase_steps

    def choose_green(self, intersection: Intersection, step: int) -> Direction:
        phase = (step // self.phase_steps) % 2
        return Direction.NORTH_SOUTH if phase == 0 else Direction.EAST_WEST
