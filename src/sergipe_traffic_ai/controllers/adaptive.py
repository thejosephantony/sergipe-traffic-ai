from sergipe_traffic_ai.controllers.base import TrafficController
from sergipe_traffic_ai.traffic.models import Direction, Intersection


class AdaptiveController(TrafficController):
    name = "adaptive"

    def __init__(self, min_green_steps: int = 8) -> None:
        self.min_green_steps = min_green_steps
        self._current = Direction.NORTH_SOUTH
        self._last_change = 0

    def choose_green(self, intersection: Intersection, step: int) -> Direction:
        if step - self._last_change < self.min_green_steps:
            return self._current

        ns_score = intersection.ns.queue_length + sum(v.waiting_steps for v in intersection.ns.queue) / 10
        ew_score = intersection.ew.queue_length + sum(v.waiting_steps for v in intersection.ew.queue) / 10
        desired = Direction.NORTH_SOUTH if ns_score >= ew_score else Direction.EAST_WEST

        if desired != self._current:
            self._current = desired
            self._last_change = step
        return self._current
