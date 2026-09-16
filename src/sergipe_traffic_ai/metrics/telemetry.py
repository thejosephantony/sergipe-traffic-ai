import csv
import json
from typing import List, Dict, Any

class TelemetryCollector:
    def __init__(self):
        self.records: List[Dict[str, Any]] = []

    def record_step(self, time_s: float, phase: str, queue_barao: int, queue_augusto: int, avg_wait_s: float, vehicles_completed: int, controller_action: str):
        step_data = {
            "time_s": time_s,
            "phase": phase,
            "queue_barao_maynard": queue_barao,
            "queue_augusto_franco": queue_augusto,
            "avg_wait_s": round(avg_wait_s, 2),
            "vehicles_completed": vehicles_completed,
            "controller_action": controller_action
        }
        self.records.append(step_data)

    def export_to_csv(self, filepath: str):
        if not self.records: return
        fieldnames = list(self.records[0].keys())
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.records)

    def export_to_json(self, filepath: str):
        with open(filepath, mode="w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=4, ensure_ascii=False)
