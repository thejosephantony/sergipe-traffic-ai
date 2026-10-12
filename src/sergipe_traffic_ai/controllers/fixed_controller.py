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
        self._clearance_delay_s = 0.0
        self._last_now = 0.0
        self.clearance_hold_active = False
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
        self._clearance_delay_s = 0.0
        self._last_now = 0.0
        self.clearance_hold_active = False

    def _scheduled_phase(self, now: float) -> str:
        time_in_cycle = now % self.cycle_duration_s
        barao_green_end = self.green_duration_s
        barao_yellow_end = barao_green_end + self.yellow_duration_s
        barao_all_red_end = barao_yellow_end + self.all_red_s
        augusto_green_end = barao_all_red_end + self.green_duration_s
        augusto_yellow_end = augusto_green_end + self.yellow_duration_s

        if time_in_cycle < barao_green_end:
            return "BARAO_GREEN"
        if time_in_cycle < barao_yellow_end:
            return "BARAO_YELLOW"
        if time_in_cycle < barao_all_red_end:
            return "ALL_RED_TO_AUGUSTO"
        if time_in_cycle < augusto_green_end:
            return "AUGUSTO_GREEN"
        if time_in_cycle < augusto_yellow_end:
            return "AUGUSTO_YELLOW"
        return "ALL_RED_TO_BARAO"

    def decide(self, observation: dict, now: float) -> str:
        elapsed = max(0.0, now - self._last_now)
        self._last_now = now

        effective_time = max(0.0, now - self._clearance_delay_s)
        requested = self._scheduled_phase(effective_time)
        occupied = bool(observation.get("conflict_zone_occupied", False))
        clearance_pending = (
            self.current_phase == "ALL_RED_TO_AUGUSTO"
            and requested == "AUGUSTO_GREEN"
        ) or (
            self.current_phase == "ALL_RED_TO_BARAO"
            and requested == "BARAO_GREEN"
        )

        self.clearance_hold_active = occupied and clearance_pending
        if self.clearance_hold_active:
            # Pausa o relógio do ciclo (inclusive após a liberação), de
            # modo que o verde seguinte não seja encurtado.
            self._clearance_delay_s += elapsed
            return self.current_phase

        self.current_phase = requested
        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        pass
