"""Estimativa de demanda baseada em indicadores do IBGE e horário do dia."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SECONDS_PER_DAY = 24 * 60 * 60


@dataclass(frozen=True)
class PeakPeriod:
    """Faixa horária e multiplicador relativo da demanda."""

    name: str
    label: str
    start_hour: float
    end_hour: float
    multiplier: float

    def contains(self, hour: float) -> bool:
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        return hour >= self.start_hour or hour < self.end_hour


DEFAULT_PEAK_PERIODS = (
    PeakPeriod("madrugada", "Madrugada", 0.0, 6.0, 0.60),
    PeakPeriod("pico_manha", "Pico da manhã", 6.0, 10.0, 1.30),
    PeakPeriod("entre_picos", "Entre picos", 10.0, 16.0, 0.90),
    PeakPeriod("pico_tarde", "Pico da tarde", 16.0, 20.0, 1.35),
    PeakPeriod("noite", "Noite", 20.0, 24.0, 0.70),
)


def _parse_hour(value: Any, default: float = 7.0) -> float:
    if isinstance(value, (int, float)):
        return float(value) % 24.0
    if isinstance(value, str):
        try:
            hour, minute = value.split(":", maxsplit=1)
            return (int(hour) + int(minute) / 60.0) % 24.0
        except (ValueError, TypeError):
            pass
    return default


class IBGEDemandModel:
    """Transforma contexto demográfico em um fator de demanda explícito.

    O IBGE não fornece contagens de veículos para o cruzamento. Por isso,
    população e densidade são usadas somente como fatores relativos sobre as
    taxas-base calibradas no cenário, e o relatório registra essa hipótese.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        config = config or {}
        self.enabled = bool(config.get("enabled", False))
        self.population_2022 = float(config.get("population_2022", 0.0))
        self.density_2022 = float(
            config.get("density_2022_hab_km2", 0.0)
        )
        self.reference_population = float(
            config.get("reference_population_2022", self.population_2022)
        )
        self.reference_density = float(
            config.get(
                "reference_density_2022_hab_km2",
                self.density_2022,
            )
        )
        scaling = config.get("scaling", {})
        self.population_exponent = float(
            scaling.get("population_exponent", 0.25)
        )
        self.density_exponent = float(
            scaling.get("density_exponent", 0.25)
        )
        self.minimum_factor = float(scaling.get("minimum_factor", 0.75))
        self.maximum_factor = float(scaling.get("maximum_factor", 1.25))
        self.start_time_s = _parse_hour(
            config.get("simulation_start_time", "07:00")
        ) * 60.0 * 60.0
        self.periods = self._load_periods(config.get("peak_periods"))

    @staticmethod
    def _load_periods(raw_periods: Any) -> tuple[PeakPeriod, ...]:
        if not raw_periods:
            return DEFAULT_PEAK_PERIODS

        periods: list[PeakPeriod] = []
        for raw in raw_periods:
            try:
                periods.append(
                    PeakPeriod(
                        name=str(raw["name"]),
                        label=str(raw.get("label", raw["name"])),
                        start_hour=float(raw["start_hour"]),
                        end_hour=float(raw["end_hour"]),
                        multiplier=float(raw["multiplier"]),
                    )
                )
            except (KeyError, TypeError, ValueError):
                continue
        return tuple(periods) or DEFAULT_PEAK_PERIODS

    @property
    def demographic_factor(self) -> float:
        if not self.enabled:
            return 1.0

        if (
            self.population_2022 <= 0
            or self.density_2022 <= 0
            or self.reference_population <= 0
            or self.reference_density <= 0
        ):
            return 1.0

        population_ratio = self.population_2022 / self.reference_population
        density_ratio = self.density_2022 / self.reference_density
        factor = (
            population_ratio**self.population_exponent
            * density_ratio**self.density_exponent
        )
        return max(self.minimum_factor, min(self.maximum_factor, factor))

    def clock_time_s(self, simulated_time_s: float) -> float:
        return (self.start_time_s + simulated_time_s) % SECONDS_PER_DAY

    def period_at(self, simulated_time_s: float) -> PeakPeriod:
        hour = self.clock_time_s(simulated_time_s) / 3600.0
        for period in self.periods:
            if period.contains(hour):
                return period
        return PeakPeriod("indefinido", "Sem perfil", 0.0, 24.0, 1.0)

    def multiplier_at(self, simulated_time_s: float) -> float:
        if not self.enabled:
            return 1.0
        return self.period_at(simulated_time_s).multiplier

    def effective_rate(
        self,
        base_rate: float,
        simulated_time_s: float,
    ) -> float:
        return max(
            0.0,
            float(base_rate)
            * self.demographic_factor
            * self.multiplier_at(simulated_time_s),
        )

    def average_multiplier(
        self,
        duration_s: float,
        sample_step_s: float = 60.0,
    ) -> float:
        """Calcula o multiplicador médio ponderado durante um episódio."""
        if duration_s <= 0:
            return 1.0

        step = max(1.0, float(sample_step_s))
        elapsed = 0.0
        weighted_total = 0.0
        while elapsed < duration_s:
            interval = min(step, duration_s - elapsed)
            weighted_total += interval * self.multiplier_at(elapsed)
            elapsed += interval
        return weighted_total / duration_s

    def context(self, simulated_time_s: float) -> dict[str, Any]:
        period = self.period_at(simulated_time_s)
        clock_time = self.clock_time_s(simulated_time_s)
        hours = int(clock_time // 3600)
        minutes = int((clock_time % 3600) // 60)
        return {
            "enabled": self.enabled,
            "source": "IBGE Censo 2022",
            "population_2022": self.population_2022,
            "density_2022_hab_km2": self.density_2022,
            "demographic_factor": self.demographic_factor,
            "peak_period": period.name,
            "peak_label": period.label,
            "peak_multiplier": self.multiplier_at(simulated_time_s),
            "clock_time": f"{hours:02d}:{minutes:02d}",
        }


__all__ = ["IBGEDemandModel", "PeakPeriod", "DEFAULT_PEAK_PERIODS"]
