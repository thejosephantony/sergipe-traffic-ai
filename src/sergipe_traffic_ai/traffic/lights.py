from dataclasses import dataclass

from .models import Direction


@dataclass
class SignalPhase:
    green_direction: Direction
    remaining_steps: int
