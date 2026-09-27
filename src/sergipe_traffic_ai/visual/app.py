from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

import pygame

from sergipe_traffic_ai.controllers.adaptive_controller import AdaptiveTrafficController
from sergipe_traffic_ai.controllers.fixed_controller import FixedTrafficController
from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    AUGUSTO_NORTHBOUND,
    AUGUSTO_SOUTHBOUND,
    BARAO_AXIS,
    BARAO_EASTBOUND,
    BARAO_WESTBOUND,
    TrafficDemandSimulator,
)
from sergipe_traffic_ai.visual.audio import AudioManager


WIDTH = 1440
HEIGHT = 820
FPS = 60

SIM_WIDTH = 1030
PANEL_X = SIM_WIDTH
PANEL_WIDTH = WIDTH - PANEL_X
HEADER_HEIGHT = 86

# Identidade visual
BG = (12, 24, 36)
SURFACE = (18, 34, 49)
SURFACE_2 = (24, 43, 60)
CARD = (28, 49, 67)
CARD_ALT = (33, 56, 75)
BORDER = (48, 73, 91)

ROAD = (55, 61, 67)
ROAD_EDGE = (89, 96, 102)
SIDEWALK = (91, 98, 104)
LANE = (225, 228, 230)

TEXT = (237, 242, 246)
MUTED = (154, 171, 183)
SUBTLE = (104, 126, 141)
WHITE = (255, 255, 255)

ACCENT = (31, 167, 201)
GREEN = (54, 190, 116)
RED = (226, 83, 83)
YELLOW = (239, 190, 64)
ORANGE = (235, 151, 62)
BLUE = (66, 154, 220)

CAR_A = BLUE
CAR_B = ORANGE

VEHICLE_CAR = (70, 155, 225)
VEHICLE_MOTORCYCLE = (238, 190, 70)
VEHICLE_BUS = (84, 190, 130)

BUILDING = (20, 37, 51)
BUILDING_EDGE = (38, 60, 75)
VEGETATION = (42, 101, 79)
GLOW_ALPHA = 52

CENTER_X = 505
CENTER_Y = 430


def load_scenario(path: str) -> dict:
    with open(path, "r", encoding="utf-8-sig") as file:
        return json.load(file)


def build_controller(name: str):
    if name == "fixed":
        return FixedTrafficController()
    if name == "adaptive":
        return AdaptiveTrafficController()
    raise ValueError(f"Controlador desconhecido: {name}")


def axis_observation(simulator: TrafficDemandSimulator) -> dict:
    return {
        "queue_barao": simulator.queue_length(BARAO_AXIS),
        "queue_augusto": simulator.queue_length(AUGUSTO_AXIS),
        "wait_barao": simulator.average_wait(BARAO_AXIS),
        "wait_augusto": simulator.average_wait(AUGUSTO_AXIS),
        "time_step_s": simulator.time_step_s,
    }


def world_to_screen(vehicle) -> tuple[int, int, str]:
    """
    Converte a coordenada longitudinal em posição de tela.

    vehicle.position representa o para-choque dianteiro.
    Em position == 0, o veículo encosta na linha de retenção e
    permanece completamente antes da faixa de pedestres.
    """
    scale = 3.0
    visual_half_length_px = {
        "car": 20.0,
        "motorcycle": 13.0,
        "bus": 31.0,
    }[vehicle.vehicle_type]

    if vehicle.movement == BARAO_EASTBOUND:
        front_x = 365 + vehicle.position * scale
        return (
            int(front_x - visual_half_length_px),
            470,
            "east",
        )

    if vehicle.movement == BARAO_WESTBOUND:
        front_x = 665 - vehicle.position * scale
        return (
            int(front_x + visual_half_length_px),
            390,
            "west",
        )

    if vehicle.movement == AUGUSTO_NORTHBOUND:
        front_y = 585 - vehicle.position * scale
        return (
            550,
            int(front_y + visual_half_length_px),
            "north",
        )

    front_y = 295 + vehicle.position * scale
    return (
        460,
        int(front_y - visual_half_length_px),
        "south",
    )


def rounded_rect(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int = 12,
    border_color: tuple[int, int, int] | None = None,
    border_width: int = 1,
) -> None:
    pygame.draw.rect(screen, color, rect, border_radius=radius)
    if border_color is not None:
        pygame.draw.rect(
            screen,
            border_color,
            rect,
            border_width,
            border_radius=radius,
        )


def draw_elevated_rect(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: tuple[int, int, int],
    radius: int = 12,
    border_color: tuple[int, int, int] = BORDER,
) -> None:
    shadow = rect.move(0, 4)
    pygame.draw.rect(
        screen,
        (7, 15, 23),
        shadow,
        border_radius=radius,
    )
    rounded_rect(
        screen,
        rect,
        color,
        radius,
        border_color,
    )


def draw_urban_context(screen: pygame.Surface) -> None:
    blocks = [
        pygame.Rect(18, 104, 360, 210),
        pygame.Rect(630, 104, 370, 210),
        pygame.Rect(18, 548, 360, 242),
        pygame.Rect(630, 548, 370, 242),
    ]

    for block in blocks:
        pygame.draw.rect(
            screen,
            BUILDING,
            block,
            border_radius=18,
        )
        pygame.draw.rect(
            screen,
            BUILDING_EDGE,
            block,
            1,
            border_radius=18,
        )

    building_rects = [
        pygame.Rect(690, 130, 110, 62),
        pygame.Rect(820, 130, 142, 62),
        pygame.Rect(680, 220, 126, 64),
        pygame.Rect(826, 220, 136, 64),
        pygame.Rect(52, 615, 130, 70),
        pygame.Rect(205, 615, 130, 70),
        pygame.Rect(690, 615, 122, 70),
        pygame.Rect(835, 615, 128, 70),
    ]

    for building in building_rects:
        pygame.draw.rect(
            screen,
            (28, 48, 63),
            building,
            border_radius=8,
        )
        pygame.draw.rect(
            screen,
            BUILDING_EDGE,
            building,
            1,
            border_radius=8,
        )

        for window_x in range(
            building.x + 14,
            building.right - 8,
            24,
        ):
            pygame.draw.rect(
                screen,
                (57, 84, 99),
                pygame.Rect(
                    window_x,
                    building.y + 15,
                    9,
                    8,
                ),
                border_radius=2,
            )

    tree_positions = [
        (650, 145), (650, 260), (975, 160), (975, 270),
        (42, 585), (350, 590), (650, 590), (982, 590),
        (42, 745), (350, 745), (650, 745), (982, 745),
    ]
    for position in tree_positions:
        pygame.draw.circle(
            screen,
            (23, 49, 42),
            (position[0] + 2, position[1] + 3),
            10,
        )
        pygame.draw.circle(
            screen,
            VEGETATION,
            position,
            9,
        )


def draw_text(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    value: str,
    position: tuple[int, int],
    font: str = "body",
    color: tuple[int, int, int] = TEXT,
) -> pygame.Rect:
    surface = fonts[font].render(value, True, color)
    rect = surface.get_rect(topleft=position)
    screen.blit(surface, rect)
    return rect


def draw_badge(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    label: str,
    position: tuple[int, int],
    color: tuple[int, int, int],
) -> int:
    text_surface = fonts["badge"].render(label, True, WHITE)
    width = text_surface.get_width() + 24
    rect = pygame.Rect(position[0], position[1], width, 28)
    pygame.draw.rect(screen, color, rect, border_radius=14)
    screen.blit(text_surface, (rect.x + 12, rect.y + 5))
    return width


def draw_header(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    controller_name: str,
    paused: bool,
    speed_multiplier: float,
) -> None:
    pygame.draw.rect(screen, SURFACE, pygame.Rect(0, 0, SIM_WIDTH, HEADER_HEIGHT))
    pygame.draw.line(
        screen,
        BORDER,
        (0, HEADER_HEIGHT - 1),
        (SIM_WIDTH, HEADER_HEIGHT - 1),
        1,
    )

    # Marca visual
    rounded_rect(screen, pygame.Rect(28, 20, 44, 44), ACCENT, 11)
    pygame.draw.circle(screen, WHITE, (50, 31), 5)
    pygame.draw.circle(screen, WHITE, (50, 42), 5)
    pygame.draw.circle(screen, WHITE, (50, 53), 5)

    draw_text(
        screen,
        fonts,
        "SERGIPE TRAFFIC AI",
        (88, 17),
        "title",
    )
    draw_text(
        screen,
        fonts,
        "Laboratório virtual de controle semafórico • Aracaju/SE",
        (89, 51),
        "small",
        MUTED,
    )

    controller_color = ACCENT if controller_name == "adaptive" else BLUE
    controller_label = "ADAPTATIVO" if controller_name == "adaptive" else "BASELINE FIXO"
    badge_x = 715
    first_width = draw_badge(
        screen,
        fonts,
        controller_label,
        (badge_x, 28),
        controller_color,
    )
    status_color = YELLOW if paused else GREEN
    status_label = "PAUSADO" if paused else f"RODANDO {speed_multiplier:g}×"
    draw_badge(
        screen,
        fonts,
        status_label,
        (badge_x + first_width + 12, 28),
        status_color,
    )


def draw_direction_arrow(
    screen: pygame.Surface,
    center: tuple[int, int],
    orientation: str,
) -> None:
    x, y = center
    if orientation == "right":
        points = [
            (x - 11, y - 6), (x + 3, y - 6),
            (x + 3, y - 11), (x + 14, y),
            (x + 3, y + 11), (x + 3, y + 6),
            (x - 11, y + 6),
        ]
    elif orientation == "left":
        points = [
            (x + 11, y - 6), (x - 3, y - 6),
            (x - 3, y - 11), (x - 14, y),
            (x - 3, y + 11), (x - 3, y + 6),
            (x + 11, y + 6),
        ]
    elif orientation == "up":
        points = [
            (x - 6, y + 11), (x - 6, y - 3),
            (x - 11, y - 3), (x, y - 14),
            (x + 11, y - 3), (x + 6, y - 3),
            (x + 6, y + 11),
        ]
    else:
        points = [
            (x - 6, y - 11), (x - 6, y + 3),
            (x - 11, y + 3), (x, y + 14),
            (x + 11, y + 3), (x + 6, y + 3),
            (x + 6, y - 11),
        ]
    pygame.draw.polygon(screen, (185, 192, 197), points)


def draw_crosswalk(
    screen: pygame.Surface,
    horizontal: bool,
    position: tuple[int, int],
) -> None:
    x, y = position
    if horizontal:
        for index in range(10):
            pygame.draw.rect(
                screen,
                (215, 219, 222),
                pygame.Rect(x + index * 17, y, 10, 42),
                border_radius=2,
            )
    else:
        for index in range(7):
            pygame.draw.rect(
                screen,
                (215, 219, 222),
                pygame.Rect(x, y + index * 17, 42, 10),
                border_radius=2,
            )


def draw_road(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
) -> None:
    # Área de simulação
    pygame.draw.rect(
        screen,
        BG,
        pygame.Rect(0, HEADER_HEIGHT, SIM_WIDTH, HEIGHT - HEADER_HEIGHT),
    )

    draw_urban_context(screen)

    # Quadras / calçadas
    pygame.draw.rect(screen, SIDEWALK, pygame.Rect(0, 326, SIM_WIDTH, 208))
    pygame.draw.rect(screen, SIDEWALK, pygame.Rect(401, HEADER_HEIGHT, 208, HEIGHT - HEADER_HEIGHT))

    # Vias
    pygame.draw.rect(screen, ROAD, pygame.Rect(0, 342, SIM_WIDTH, 176))
    pygame.draw.rect(screen, ROAD, pygame.Rect(417, HEADER_HEIGHT, 176, HEIGHT - HEADER_HEIGHT))

    # Bordas
    pygame.draw.line(screen, ROAD_EDGE, (0, 342), (SIM_WIDTH, 342), 2)
    pygame.draw.line(screen, ROAD_EDGE, (0, 518), (SIM_WIDTH, 518), 2)
    pygame.draw.line(screen, ROAD_EDGE, (417, HEADER_HEIGHT), (417, HEIGHT), 2)
    pygame.draw.line(screen, ROAD_EDGE, (593, HEADER_HEIGHT), (593, HEIGHT), 2)

    # Zona de conflito do cruzamento
    conflict_zone = pygame.Rect(417, 342, 176, 176)
    pygame.draw.rect(
        screen,
        (50, 57, 63),
        conflict_zone,
    )
    pygame.draw.rect(
        screen,
        (82, 92, 99),
        conflict_zone,
        2,
    )

    # Divisão dos sentidos
    for x in range(10, SIM_WIDTH - 20, 48):
        if x < 345 or x > 665:
            pygame.draw.line(
                screen,
                LANE,
                (x, CENTER_Y),
                (x + 25, CENTER_Y),
                2,
            )

    for y in range(HEADER_HEIGHT + 8, HEIGHT - 20, 48):
        if y < 285 or y > 575:
            pygame.draw.line(
                screen,
                LANE,
                (CENTER_X, y),
                (CENTER_X, y + 25),
                2,
            )

    # Quatro faixas de pedestres, uma em cada borda do cruzamento
    draw_crosswalk(screen, False, (378, 350))
    draw_crosswalk(screen, False, (610, 350))
    draw_crosswalk(screen, True, (423, 307))
    draw_crosswalk(screen, True, (423, 527))

    # Linhas de retenção antes das faixas
    # Barão/Maynard: leste (faixa inferior) e oeste (faixa superior)
    pygame.draw.line(screen, WHITE, (365, 434), (365, 510), 5)
    pygame.draw.line(screen, WHITE, (665, 350), (665, 426), 5)

    # Augusto Franco: norte (faixa direita) e sul (faixa esquerda)
    pygame.draw.line(screen, WHITE, (508, 585), (590, 585), 5)
    pygame.draw.line(screen, WHITE, (420, 295), (502, 295), 5)

    # Setas dos quatro sentidos
    draw_direction_arrow(screen, (245, 470), "right")
    draw_direction_arrow(screen, (790, 390), "left")
    draw_direction_arrow(screen, (550, 690), "up")
    draw_direction_arrow(screen, (460, 175), "down")

    # Rótulos das vias
    rounded_rect(screen, pygame.Rect(35, 548, 284, 34), SURFACE_2, 9, BORDER)
    draw_text(
        screen,
        fonts,
        "AV. BARÃO DE MARUIM / DES. MAYNARD",
        (49, 557),
        "road",
        TEXT,
    )

    vertical_label = fonts["road"].render("AV. AUGUSTO FRANCO", True, TEXT)
    vertical_label = pygame.transform.rotate(vertical_label, 90)
    vertical_box = pygame.Rect(626, 121, 36, 204)
    rounded_rect(screen, vertical_box, SURFACE_2, 9, BORDER)
    screen.blit(vertical_label, vertical_label.get_rect(center=vertical_box.center))

    # Identificação do cruzamento
    rounded_rect(screen, pygame.Rect(28, 108, 310, 70), SURFACE, 12, BORDER)
    draw_text(screen, fonts, "CENÁRIO PILOTO", (45, 122), "eyebrow", ACCENT)
    draw_text(
        screen,
        fonts,
        "Augusto Franco × Des. Maynard",
        (45, 146),
        "body_bold",
        TEXT,
    )


def draw_fleet_legend(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
) -> None:
    rect = pygame.Rect(28, 192, 310, 88)
    rounded_rect(screen, rect, SURFACE, 12, BORDER)
    draw_text(screen, fonts, "AGENTES VEICULARES", (45, 205), "eyebrow", ACCENT)

    items = [
        ("Carro", VEHICLE_CAR),
        ("Moto", VEHICLE_MOTORCYCLE),
        ("Ônibus", VEHICLE_BUS),
    ]
    x = 46
    for label, color in items:
        pygame.draw.circle(screen, color, (x + 6, 245), 6)
        draw_text(screen, fonts, label, (x + 18, 237), "tiny", TEXT)
        x += 88


def draw_traffic_light(
    screen: pygame.Surface,
    position: tuple[int, int],
    active: str,
    orientation: str = "vertical",
) -> None:
    x, y = position
    if orientation == "vertical":
        rect = pygame.Rect(x, y, 42, 104)
        centers = [(x + 21, y + 22), (x + 21, y + 52), (x + 21, y + 82)]
    else:
        rect = pygame.Rect(x, y, 104, 42)
        centers = [(x + 22, y + 21), (x + 52, y + 21), (x + 82, y + 21)]

    rounded_rect(screen, rect, (15, 20, 25), 9, (83, 91, 98))
    colors = {
        "red": RED if active == "red" else (74, 43, 43),
        "yellow": YELLOW if active == "yellow" else (76, 68, 41),
        "green": GREEN if active == "green" else (39, 71, 53),
    }

    for center, name in zip(centers, ("red", "yellow", "green")):
        pygame.draw.circle(screen, (8, 12, 15), center, 11)

        if active == name:
            glow = pygame.Surface((54, 54), pygame.SRCALPHA)
            glow_color = (*colors[name], GLOW_ALPHA)
            pygame.draw.circle(glow, glow_color, (27, 27), 22)
            screen.blit(
                glow,
                (center[0] - 27, center[1] - 27),
            )

        pygame.draw.circle(screen, colors[name], center, 8)
        pygame.draw.circle(
            screen,
            (255, 255, 255),
            (center[0] - 2, center[1] - 2),
            2,
        )


def draw_signals(screen: pygame.Surface, phase: str) -> None:
    if phase == "BARAO_GREEN":
        barao_active = "green"
    elif phase == "BARAO_YELLOW":
        barao_active = "yellow"
    else:
        barao_active = "red"

    if phase == "AUGUSTO_GREEN":
        augusto_active = "green"
    elif phase == "AUGUSTO_YELLOW":
        augusto_active = "yellow"
    else:
        augusto_active = "red"

    # Sentidos opostos do mesmo eixo recebem a mesma indicação.
    draw_traffic_light(screen, (326, 451), barao_active, "vertical")
    draw_traffic_light(screen, (680, 305), barao_active, "vertical")
    draw_traffic_light(screen, (568, 600), augusto_active, "horizontal")
    draw_traffic_light(screen, (341, 242), augusto_active, "horizontal")


def draw_vehicle(
    screen: pygame.Surface,
    x: int,
    y: int,
    horizontal: bool,
    vehicle_type: str,
    queued: bool,
    heading: str,
) -> None:
    if vehicle_type == "bus":
        color = VEHICLE_BUS
        if horizontal:
            body = pygame.Rect(x - 31, y - 12, 62, 24)
            windows = [
                pygame.Rect(x - 20, y - 8, 12, 10),
                pygame.Rect(x - 4, y - 8, 12, 10),
                pygame.Rect(x + 12, y - 8, 12, 10),
            ]
            wheels = [(x - 20, y + 12), (x + 20, y + 12)]
        else:
            body = pygame.Rect(x - 12, y - 31, 24, 62)
            windows = [
                pygame.Rect(x - 8, y - 20, 10, 12),
                pygame.Rect(x - 8, y - 4, 10, 12),
                pygame.Rect(x - 8, y + 12, 10, 12),
            ]
            wheels = [(x + 12, y - 20), (x + 12, y + 20)]

        pygame.draw.rect(screen, (8, 14, 19), body.move(2, 3), border_radius=6)
        pygame.draw.rect(screen, color, body, border_radius=6)
        for window in windows:
            pygame.draw.rect(screen, (177, 213, 229), window, border_radius=2)
        for wheel in wheels:
            pygame.draw.circle(screen, (20, 24, 28), wheel, 4)

    elif vehicle_type == "motorcycle":
        color = VEHICLE_MOTORCYCLE
        if horizontal:
            body = pygame.Rect(x - 13, y - 5, 26, 10)
            pygame.draw.circle(screen, (18, 22, 26), (x - 9, y + 6), 4)
            pygame.draw.circle(screen, (18, 22, 26), (x + 9, y + 6), 4)
            pygame.draw.circle(screen, color, (x, y - 3), 5)
            pygame.draw.line(screen, color, (x - 7, y), (x + 8, y), 4)
        else:
            body = pygame.Rect(x - 5, y - 13, 10, 26)
            pygame.draw.circle(screen, (18, 22, 26), (x + 6, y - 9), 4)
            pygame.draw.circle(screen, (18, 22, 26), (x + 6, y + 9), 4)
            pygame.draw.circle(screen, color, (x - 3, y), 5)
            pygame.draw.line(screen, color, (x, y - 7), (x, y + 8), 4)
        pygame.draw.rect(screen, color, body, border_radius=4)

    else:
        color = VEHICLE_CAR
        if horizontal:
            body = pygame.Rect(x - 20, y - 10, 40, 20)
            window = pygame.Rect(x - 5, y - 7, 13, 14)
            wheels = [(x - 13, y + 10), (x + 13, y + 10)]
        else:
            body = pygame.Rect(x - 10, y - 20, 20, 40)
            window = pygame.Rect(x - 7, y - 5, 14, 13)
            wheels = [(x + 10, y - 13), (x + 10, y + 13)]

        pygame.draw.rect(screen, (8, 14, 19), body.move(2, 3), border_radius=5)
        pygame.draw.rect(screen, color, body, border_radius=5)
        pygame.draw.rect(screen, (177, 213, 229), window, border_radius=3)
        for wheel in wheels:
            pygame.draw.circle(screen, (20, 24, 28), wheel, 3)

    # Indicador sutil da dianteira do veículo
    if heading == "east":
        pygame.draw.circle(screen, WHITE, (body.right - 3, body.centery), 2)
    elif heading == "west":
        pygame.draw.circle(screen, WHITE, (body.left + 3, body.centery), 2)
    elif heading == "north":
        pygame.draw.circle(screen, WHITE, (body.centerx, body.top + 3), 2)
    else:
        pygame.draw.circle(screen, WHITE, (body.centerx, body.bottom - 3), 2)

    if queued:
        pygame.draw.rect(screen, WHITE, body, 2, border_radius=5)


def draw_vehicles(screen: pygame.Surface, simulator: TrafficDemandSimulator) -> None:
    for vehicle in simulator.active_vehicles:
        x, y, heading = world_to_screen(vehicle)
        horizontal = vehicle.origin_axis == BARAO_AXIS
        draw_vehicle(
            screen,
            x,
            y,
            horizontal=horizontal,
            vehicle_type=vehicle.vehicle_type,
            queued=vehicle.state == "QUEUED",
            heading=heading,
        )


def draw_metric_card(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    rect: pygame.Rect,
    label: str,
    value: str,
    accent: tuple[int, int, int] = ACCENT,
) -> None:
    draw_elevated_rect(screen, rect, CARD, 12, BORDER)
    pygame.draw.rect(
        screen,
        accent,
        pygame.Rect(rect.x, rect.y, 4, rect.height),
        border_radius=2,
    )
    draw_text(screen, fonts, label.upper(), (rect.x + 16, rect.y + 13), "metric_label", MUTED)
    draw_text(screen, fonts, value, (rect.x + 16, rect.y + 35), "metric_value", TEXT)


def draw_queue_chart(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    rect: pygame.Rect,
    barao_history: deque[int],
    augusto_history: deque[int],
) -> None:
    rounded_rect(screen, rect, CARD, 12, BORDER)
    draw_text(screen, fonts, "FILAS AO VIVO", (rect.x + 16, rect.y + 12), "metric_label", MUTED)

    chart = pygame.Rect(rect.x + 16, rect.y + 43, rect.width - 32, rect.height - 64)
    pygame.draw.line(screen, BORDER, (chart.x, chart.bottom), (chart.right, chart.bottom), 1)
    pygame.draw.line(screen, BORDER, (chart.x, chart.y), (chart.x, chart.bottom), 1)

    values = list(barao_history) + list(augusto_history)
    max_value = max(4, max(values, default=0))

    def draw_series(history: deque[int], color: tuple[int, int, int]) -> None:
        if len(history) < 2:
            return
        points = []
        items = list(history)
        for index, value in enumerate(items):
            x = chart.x + (index / max(1, len(items) - 1)) * chart.width
            y = chart.bottom - (value / max_value) * chart.height
            points.append((int(x), int(y)))
        pygame.draw.lines(screen, color, False, points, 2)

    draw_series(barao_history, CAR_A)
    draw_series(augusto_history, CAR_B)

    pygame.draw.circle(screen, CAR_A, (rect.x + 18, rect.bottom - 13), 4)
    draw_text(screen, fonts, "Barão/Maynard", (rect.x + 28, rect.bottom - 21), "tiny", MUTED)
    pygame.draw.circle(screen, CAR_B, (rect.x + 140, rect.bottom - 13), 4)
    draw_text(screen, fonts, "Augusto Franco", (rect.x + 150, rect.bottom - 21), "tiny", MUTED)


def draw_panel(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    simulator: TrafficDemandSimulator,
    controller_name: str,
    phase: str,
    paused: bool,
    speed_multiplier: float,
    scenario: dict,
    barao_history: deque[int],
    augusto_history: deque[int],
    audio_enabled: bool,
) -> None:
    pygame.draw.rect(screen, SURFACE, pygame.Rect(PANEL_X, 0, PANEL_WIDTH, HEIGHT))
    pygame.draw.line(screen, BORDER, (PANEL_X, 0), (PANEL_X, HEIGHT), 1)

    left = PANEL_X + 24
    width = PANEL_WIDTH - 48

    draw_text(screen, fonts, "PAINEL DE OPERAÇÃO", (left, 24), "eyebrow", ACCENT)
    draw_text(screen, fonts, "Telemetria do cenário", (left, 47), "panel_title", TEXT)

    scenario_id = scenario.get("scenario", {}).get("id", "cenário")
    seed = scenario.get("scenario", {}).get("seed", 42)
    draw_text(screen, fonts, scenario_id, (left, 78), "tiny", MUTED)

    controller_label = (
        "Adaptativo por regras"
        if controller_name == "adaptive"
        else "Tempo fixo (baseline)"
    )

    phase_labels = {
        "BARAO_GREEN": ("Barão/Maynard liberado", GREEN),
        "BARAO_YELLOW": ("Barão/Maynard em amarelo", YELLOW),
        "ALL_RED_TO_AUGUSTO": ("Todos vermelhos • limpeza do cruzamento", RED),
        "AUGUSTO_GREEN": ("Augusto Franco liberado", GREEN),
        "AUGUSTO_YELLOW": ("Augusto Franco em amarelo", YELLOW),
        "ALL_RED_TO_BARAO": ("Todos vermelhos • limpeza do cruzamento", RED),
    }
    phase_label, phase_color = phase_labels.get(
        phase,
        ("Fase de segurança", MUTED),
    )

    draw_elevated_rect(
        screen,
        pygame.Rect(left, 107, width, 76),
        CARD_ALT,
        12,
        BORDER,
    )
    draw_text(screen, fonts, "CONTROLADOR", (left + 16, 119), "metric_label", MUTED)
    draw_text(screen, fonts, controller_label, (left + 16, 141), "body_bold", TEXT)
    draw_text(
        screen,
        fonts,
        phase_label,
        (left + 16, 162),
        "tiny",
        phase_color,
    )

    gap = 10
    card_width = (width - gap) // 2
    draw_metric_card(
        screen,
        fonts,
        pygame.Rect(left, 199, card_width, 78),
        "Tempo simulado",
        f"{simulator.current_time:.1f} s",
        ACCENT,
    )
    draw_metric_card(
        screen,
        fonts,
        pygame.Rect(left + card_width + gap, 199, card_width, 78),
        "Concluídos",
        str(simulator.completed_vehicles_count),
        GREEN,
    )
    draw_metric_card(
        screen,
        fonts,
        pygame.Rect(left, 287, card_width, 78),
        "Fila Barão",
        str(simulator.queue_length(BARAO_AXIS)),
        CAR_A,
    )
    draw_metric_card(
        screen,
        fonts,
        pygame.Rect(left + card_width + gap, 287, card_width, 78),
        "Fila Augusto",
        str(simulator.queue_length(AUGUSTO_AXIS)),
        CAR_B,
    )

    draw_metric_card(
        screen,
        fonts,
        pygame.Rect(left, 375, width, 72),
        "Espera média dos veículos ativos",
        f"{simulator.average_wait():.1f} s",
        YELLOW,
    )

    draw_queue_chart(
        screen,
        fonts,
        pygame.Rect(left, 463, width, 180),
        barao_history,
        augusto_history,
    )

    draw_elevated_rect(
        screen,
        pygame.Rect(left, 660, width, 82),
        CARD_ALT,
        12,
        BORDER,
    )
    draw_text(screen, fonts, "FROTA ATIVA • DADOS SINTÉTICOS", (left + 16, 672), "metric_label", MUTED)
    fleet_text = (
        f"Carros {simulator.active_count_by_type('car')}  •  "
        f"Motos {simulator.active_count_by_type('motorcycle')}  •  "
        f"Ônibus {simulator.active_count_by_type('bus')}"
    )
    draw_text(screen, fonts, fleet_text, (left + 16, 696), "small", TEXT)
    draw_text(screen, fonts, f"Seed {seed} • composição configurável no cenário", (left + 16, 718), "tiny", MUTED)

    state = "PAUSADO" if paused else f"{speed_multiplier:g}×"
    audio_state = "ÁUDIO ON" if audio_enabled else "ÁUDIO OFF"
    draw_elevated_rect(
        screen,
        pygame.Rect(left, 756, width, 42),
        SURFACE_2,
        10,
        BORDER,
    )
    draw_text(
        screen,
        fonts,
        (
            f"ESPAÇO pausa • R reset • 1/2 controle • "
            f"M áudio • ↑↓ velocidade • {state} • {audio_state}"
        ),
        (left + 11, 769),
        "tiny",
        MUTED,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Protótipo visual do Sergipe Traffic AI")
    parser.add_argument(
        "--scenario",
        default="scenarios/aracaju_barao_augusto.json",
        help="Arquivo JSON do cenário.",
    )
    parser.add_argument("--controller", choices=["fixed", "adaptive"], default="fixed")
    args = parser.parse_args()

    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        raise FileNotFoundError(f"Cenário não encontrado: {scenario_path}")

    pygame.mixer.pre_init(
        frequency=44_100,
        size=-16,
        channels=1,
        buffer=512,
    )
    pygame.init()
    audio = AudioManager()

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sergipe Traffic AI • Laboratório de Controle Semafórico")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("segoeui", 27, bold=True),
        "panel_title": pygame.font.SysFont("segoeui", 22, bold=True),
        "body": pygame.font.SysFont("segoeui", 16),
        "body_bold": pygame.font.SysFont("segoeui", 16, bold=True),
        "small": pygame.font.SysFont("segoeui", 13),
        "tiny": pygame.font.SysFont("segoeui", 11),
        "road": pygame.font.SysFont("segoeui", 12, bold=True),
        "badge": pygame.font.SysFont("segoeui", 11, bold=True),
        "eyebrow": pygame.font.SysFont("segoeui", 11, bold=True),
        "metric_label": pygame.font.SysFont("segoeui", 10, bold=True),
        "metric_value": pygame.font.SysFont("segoeui", 24, bold=True),
    }

    scenario = load_scenario(str(scenario_path))
    simulator = TrafficDemandSimulator(scenario)
    controller_name = args.controller
    controller = build_controller(controller_name)
    controller.reset(scenario)

    paused = False
    running = True
    accumulator = 0.0
    speed_multiplier = 1.0
    current_phase = "BARAO_GREEN"

    barao_history: deque[int] = deque(maxlen=80)
    augusto_history: deque[int] = deque(maxlen=80)
    barao_history.append(0)
    augusto_history.append(0)
    last_history_second = -1

    while running:
        real_dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    audio.play_ui()
                    simulator.reset()
                    controller.reset(scenario)
                    current_phase = "BARAO_GREEN"
                    barao_history.clear()
                    augusto_history.clear()
                    barao_history.append(0)
                    augusto_history.append(0)
                    last_history_second = -1
                elif event.key == pygame.K_1:
                    audio.play_ui()
                    controller_name = "fixed"
                    controller = build_controller(controller_name)
                    controller.reset(scenario)
                elif event.key == pygame.K_2:
                    audio.play_ui()
                    controller_name = "adaptive"
                    controller = build_controller(controller_name)
                    controller.reset(scenario)
                elif event.key == pygame.K_m:
                    audio.toggle()
                    if audio.is_enabled:
                        audio.play_ui()
                elif event.key == pygame.K_UP:
                    speed_multiplier = min(
                        8.0,
                        speed_multiplier * 2.0,
                    )
                elif event.key == pygame.K_DOWN:
                    speed_multiplier = max(0.5, speed_multiplier / 2.0)

        if not paused:
            accumulator += real_dt * speed_multiplier

            while accumulator >= simulator.time_step_s:
                simulator.generate_vehicles_step()
                observation = axis_observation(simulator)
                previous_phase = current_phase
                current_phase = controller.decide(
                    observation,
                    simulator.current_time,
                )
                if current_phase != previous_phase:
                    audio.play_phase(current_phase)

                simulator.step(current_phase)
                accumulator -= simulator.time_step_s

                current_second = int(simulator.current_time)
                if current_second != last_history_second:
                    barao_history.append(simulator.queue_length(BARAO_AXIS))
                    augusto_history.append(simulator.queue_length(AUGUSTO_AXIS))
                    last_history_second = current_second

                if simulator.current_time >= simulator.duration_s:
                    paused = True
                    break

        screen.fill(BG)
        draw_header(
            screen,
            fonts,
            controller_name,
            paused,
            speed_multiplier,
        )
        draw_road(screen, fonts)
        draw_fleet_legend(screen, fonts)
        draw_signals(screen, current_phase)
        draw_vehicles(screen, simulator)
        draw_panel(
            screen,
            fonts,
            simulator,
            controller_name,
            current_phase,
            paused,
            speed_multiplier,
            scenario,
            barao_history,
            augusto_history,
            audio.is_enabled,
        )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
