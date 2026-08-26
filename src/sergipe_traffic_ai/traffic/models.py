from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Direction(str, Enum):
    NORTH_SOUTH = "north_south"
    EAST_WEST = "east_west"


class LightState(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class Vehicle:
    id: int
    direction: Direction
    waiting_steps: int = 0
    stopped: bool = True


@dataclass
class Lane:
    direction: Direction
    queue: list[Vehicle] = field(default_factory=list)

    @property
    def queue_length(self) -> int:
        return len(self.queue)


@dataclass
class Intersection:
    ns: Lane = field(default_factory=lambda: Lane(Direction.NORTH_SOUTH))
    ew: Lane = field(default_factory=lambda: Lane(Direction.EAST_WEST))

    def lane(self, direction: Direction) -> Lane:
        return self.ns if direction is Direction.NORTH_SOUTH else self.ew
