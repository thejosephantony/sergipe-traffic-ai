"""
Controlador Semafórico de Tempo Fixo (Baseline)
Sergipe Traffic AI - Seção 10
"""

class FixedTrafficController:
    def __init__(self, green_duration_s: float = 30.0, yellow_duration_s: float = 3.0, all_red_s: float = 1.0):
        self.green_duration_s = green_duration_s
        self.yellow_duration_s = yellow_duration_s
        self.all_red_s = all_red_s
        self.phase_time = self.green_duration_s + self.yellow_duration_s + self.all_red_s
        self.cycle_duration_s = self.phase_time * 2
        self.current_phase = "BARAO_GREEN"

    def reset(self, scenario):
        self.current_phase = "BARAO_GREEN"

    def decide(self, observation: dict, now: float) -> str:
        time_in_cycle = now % self.cycle_duration_s
        if time_in_cycle < self.phase_time:
            self.current_phase = "BARAO_GREEN"
        else:
            self.current_phase = "AUGUSTO_GREEN"
        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        pass
