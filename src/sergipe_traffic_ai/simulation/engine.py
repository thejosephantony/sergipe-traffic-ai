from __future__ import annotations

import random

from sergipe_traffic_ai.controllers.base import TrafficController
from sergipe_traffic_ai.metrics.collector import MetricsCollector
from sergipe_traffic_ai.traffic.models import Direction, Intersection, Vehicle


class Simulation:
    def __init__(
        self,
        controller: TrafficController,
        *,
        seed: int = 42,
        arrival_probability_ns: float = 0.35,
        arrival_probability_ew: float = 0.20,
        service_rate: int = 1,
    ) -> None:
        self.controller = controller
        self.random = random.Random(seed)
        self.intersection = Intersection()
        self.arrival_probability = {
            Direction.NORTH_SOUTH: arrival_probability_ns,
            Direction.EAST_WEST: arrival_probability_ew,
        }
        self.service_rate = service_rate
        self.metrics = MetricsCollector()
        self._next_vehicle_id = 1

    def _spawn(self, direction: Direction) -> None:
        if self.random.random() < self.arrival_probability[direction]:
            vehicle = Vehicle(id=self._next_vehicle_id, direction=direction)
            self._next_vehicle_id += 1
            self.intersection.lane(direction).queue.append(vehicle)
            self.metrics.generated += 1

    def _increment_wait(self) -> None:
        for lane in (self.intersection.ns, self.intersection.ew):
            for vehicle in lane.queue:
                vehicle.waiting_steps += 1

    def _serve(self, direction: Direction) -> None:
        lane = self.intersection.lane(direction)
        for _ in range(min(self.service_rate, lane.queue_length)):
            vehicle = lane.queue.pop(0)
            vehicle.stopped = False
            self.metrics.record_completion(vehicle.waiting_steps)

    def step(self, step_number: int) -> None:
        self._spawn(Direction.NORTH_SOUTH)
        self._spawn(Direction.EAST_WEST)
        self._increment_wait()
        green = self.controller.choose_green(self.intersection, step_number)
        self._serve(green)
        total_queue = self.intersection.ns.queue_length + self.intersection.ew.queue_length
        self.metrics.record_queue(total_queue)

    def run(self, steps: int) -> dict[str, float | int | str]:
        for step in range(steps):
            self.step(step)
        return {"controller": self.controller.name, **self.metrics.summary(steps)}
