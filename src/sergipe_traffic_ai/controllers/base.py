from __future__ import annotations

from abc import ABC, abstractmethod

from sergipe_traffic_ai.traffic.models import Direction, Intersection


class TrafficController(ABC):
    name = "base"

    @abstractmethod
    def choose_green(self, intersection: Intersection, step: int) -> Direction:
        """Choose which axis receives green at this simulation step."""
