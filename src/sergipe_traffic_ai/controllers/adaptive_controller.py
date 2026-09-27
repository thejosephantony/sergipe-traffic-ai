"""
Controlador Semafórico Adaptativo Baseado em Regras
Sergipe Traffic AI
"""


class AdaptiveTrafficController:
    """
    Controlador adaptativo com intervalo de segurança entre verdes.

    Sequência de troca:
    VERDE -> AMARELO -> TODOS VERMELHOS -> VERDE CONFLITANTE.
    """

    def __init__(
        self,
        min_green_s: float = 10.0,
        max_green_s: float = 60.0,
        yellow_duration_s: float = 3.0,
        all_red_s: float = 1.0,
        alpha: float = 1.0,
        beta: float = 0.5,
    ):
        self.min_green_s = min_green_s
        self.max_green_s = max_green_s
        self.yellow_duration_s = yellow_duration_s
        self.all_red_s = all_red_s
        self.alpha = alpha
        self.beta = beta

        self.current_phase = "BARAO_GREEN"
        self.time_in_current_phase = 0.0

    def reset(self, scenario):
        controller_cfg = scenario.get("scenario", {}).get("controller", {})

        self.min_green_s = float(
            controller_cfg.get("min_green_s", self.min_green_s)
        )
        self.max_green_s = float(
            controller_cfg.get("max_green_s", self.max_green_s)
        )
        self.yellow_duration_s = float(
            controller_cfg.get("yellow_s", self.yellow_duration_s)
        )
        self.all_red_s = float(
            controller_cfg.get("all_red_s", self.all_red_s)
        )

        self.current_phase = "BARAO_GREEN"
        self.time_in_current_phase = 0.0

    def _begin_transition(self) -> None:
        if self.current_phase == "BARAO_GREEN":
            self.current_phase = "BARAO_YELLOW"
        elif self.current_phase == "AUGUSTO_GREEN":
            self.current_phase = "AUGUSTO_YELLOW"
        self.time_in_current_phase = 0.0

    def _advance_clearance_phase(self) -> None:
        if (
            self.current_phase == "BARAO_YELLOW"
            and self.time_in_current_phase >= self.yellow_duration_s
        ):
            self.current_phase = "ALL_RED_TO_AUGUSTO"
            self.time_in_current_phase = 0.0
        elif (
            self.current_phase == "AUGUSTO_YELLOW"
            and self.time_in_current_phase >= self.yellow_duration_s
        ):
            self.current_phase = "ALL_RED_TO_BARAO"
            self.time_in_current_phase = 0.0
        elif (
            self.current_phase == "ALL_RED_TO_AUGUSTO"
            and self.time_in_current_phase >= self.all_red_s
        ):
            self.current_phase = "AUGUSTO_GREEN"
            self.time_in_current_phase = 0.0
        elif (
            self.current_phase == "ALL_RED_TO_BARAO"
            and self.time_in_current_phase >= self.all_red_s
        ):
            self.current_phase = "BARAO_GREEN"
            self.time_in_current_phase = 0.0

    def decide(self, observation: dict, now: float) -> str:
        del now

        time_step_s = float(observation.get("time_step_s", 0.2))
        self.time_in_current_phase += time_step_s

        if self.current_phase not in {
            "BARAO_GREEN",
            "AUGUSTO_GREEN",
        }:
            self._advance_clearance_phase()
            return self.current_phase

        queue_barao = observation.get("queue_barao", 0)
        queue_augusto = observation.get("queue_augusto", 0)
        wait_barao = observation.get("wait_barao", 0.0)
        wait_augusto = observation.get("wait_augusto", 0.0)

        score_barao = (
            self.alpha * queue_barao
            + self.beta * wait_barao
        )
        score_augusto = (
            self.alpha * queue_augusto
            + self.beta * wait_augusto
        )

        if self.time_in_current_phase >= self.min_green_s:
            should_switch = False

            if self.current_phase == "BARAO_GREEN":
                should_switch = (
                    score_augusto > score_barao
                    or self.time_in_current_phase >= self.max_green_s
                )
            else:
                should_switch = (
                    score_barao > score_augusto
                    or self.time_in_current_phase >= self.max_green_s
                )

            if should_switch:
                self._begin_transition()

        return self.current_phase

    def on_transition(self, previous_phase: str, new_phase: str):
        pass
