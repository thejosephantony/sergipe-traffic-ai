from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    generated: int = 0
    completed: int = 0
    waiting_samples: list[int] = field(default_factory=list)
    queue_samples: list[int] = field(default_factory=list)

    def record_queue(self, total_queue: int) -> None:
        self.queue_samples.append(total_queue)

    def record_completion(self, waiting_steps: int) -> None:
        self.completed += 1
        self.waiting_samples.append(waiting_steps)

    def summary(self, steps: int) -> dict[str, float | int]:
        avg_wait = sum(self.waiting_samples) / len(self.waiting_samples) if self.waiting_samples else 0.0
        avg_queue = sum(self.queue_samples) / len(self.queue_samples) if self.queue_samples else 0.0
        max_queue = max(self.queue_samples, default=0)
        return {
            "steps": steps,
            "vehicles_generated": self.generated,
            "vehicles_completed": self.completed,
            "average_wait": round(avg_wait, 3),
            "average_queue": round(avg_queue, 3),
            "max_queue": max_queue,
            "throughput": round(self.completed / steps, 4) if steps else 0.0,
        }
