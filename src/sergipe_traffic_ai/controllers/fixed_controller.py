"""
Controlador Semafórico de Tempo Fixo (Baseline)
Sergipe Traffic AI
"""


class FixedTrafficController:
    def __init__(
        self,
        green_duration_s: float = 30.0,
        yellow_duration_s: float = 3.0,
        all_red_s: float = 1.0,
    ):
        self.green_duration_s = green_duration_s
        self.yellow_duration_s = yellow_duration_s
        self.all_red_s = all_red_s
        self.current_phase = "BARAO_GREEN"
        self._rebuild_cycle()

    def _rebuild_cycle(self) -> None:
        self.half_cycle_s = (
            self.green_duration_s
            + self.yellow_duration_s
            + self.all_red_s
        )
        self.cycle_duration_s = self.half_cycle_s * 2

    def reset(self, scenario):
        controller_cfg = scenario.get("scenario", {}).get("controller", {})

        self.yellow_duration_s = float(
            controller_cfg.get("yellow_s", self.yellow_duration_s)
        )
        self.all_red_s = float(
            controller_cfg.get("all_red_s", self.all_red_s)
        )

        configured_cycle = controller_cfg.get("cycle_duration_s")
        if configured_cycle is not None:
            cycle_duration_s = float(configured_cycle)
            clearance_per_cycle = 2 * (
                self.yellow_duration_s + self.all_red_s
            )
            remaining_green = max(
                2.0,
                cycle_duration_s - clearance_per_cycle,
            )
            self.green_duration_s = remaining_green / 2.0

        self._rebuild_cycle()
        self.current_phase = "BARAO_GREEN"

    def decide(self, observation: dict, now: float) -> str:
        time_in_cycle = now % self.cycle_duration_s

        barao_green_end = self.green_duration_s
        barao_yellow_end = (
            barao_green_end + self.yellow_duration_s
        )
        barao_all_red_end = barao_yellow_end + self.all_red_s

        augusto_green_end = (
            barao_all_red_end + self.green_duration_s
        )
        augusto_yellow_end = (
            augusto_green_end + self.yellow_duration_s
        )

        if time_in_cycle < barao_green_end:
            self.current_phase = "BARAO_GREEN"
        elif time_in_cycle < barao_yellow_end:
            self.current_phase = "BARAO_YELLOW"
        elif time_in_cycle < barao_all_red_end:
            self.current_phase = "ALL_RED_TO_AUGUSTO"
        elif time_in_cycle < augusto_green_end:
            self.current_phase = "AUGUSTO_GREEN"
        elif time_in_cycle < augusto_yellow_end:
            self.current_phase = "AUGUSTO_YELLOW"
        else:
            self.current_phase = "ALL_RED_TO_BARAO"

        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        pass
