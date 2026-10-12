"""Medidas visuais consistentes com a dinâmica longitudinal (metros → pixels)."""

from sergipe_traffic_ai.traffic.demand import VEHICLE_PROFILES

VEHICLE_SCALE_PX_PER_M = 3.0
# A folga visual (3 px) é menor do que o espaçamento físico mínimo (7,5 px).
VISUAL_BODY_PADDING_PX = 3

VEHICLE_WIDTH_PX = {
    "car": 14,
    "motorcycle": 8,
    "bus": 20,
}


def sprite_dimensions(vehicle_type: str) -> tuple[int, int]:
    length_m = float(VEHICLE_PROFILES[vehicle_type]["length_m"])
    length_px = round(length_m * VEHICLE_SCALE_PX_PER_M) + VISUAL_BODY_PADDING_PX
    return length_px, VEHICLE_WIDTH_PX[vehicle_type]


def front_to_center(
    front: float,
    heading: str,
    vehicle_type: str,
) -> float:
    """Centraliza o sprite sem deslocar seu para-choque além da linha de parada."""
    length_px, _ = sprite_dimensions(vehicle_type)
    half = length_px / 2.0
    if heading in {"east", "south"}:
        return front - half
    if heading in {"west", "north"}:
        return front + half
    raise ValueError(f"Direção visual inválida: {heading}")


def length_is_safe_for_gap(
    vehicle_type: str,
    min_gap_m: float,
) -> bool:
    """Verifica que um sprite não invade o espaço físico do próximo veículo."""
    rendered_length, _ = sprite_dimensions(vehicle_type)
    physical_length = float(VEHICLE_PROFILES[vehicle_type]["length_m"])
    maximum_length = (physical_length + min_gap_m) * VEHICLE_SCALE_PX_PER_M
    return rendered_length < maximum_length
