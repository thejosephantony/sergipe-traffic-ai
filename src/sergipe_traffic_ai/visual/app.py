from __future__ import annotations

import argparse
import json
from pathlib import Path

import pygame

from sergipe_traffic_ai.controllers.adaptive_controller import AdaptiveTrafficController
from sergipe_traffic_ai.controllers.fixed_controller import FixedTrafficController
from sergipe_traffic_ai.traffic.demand import (
    AUGUSTO_AXIS,
    BARAO_AXIS,
    TrafficDemandSimulator,
)


WIDTH = 1280
HEIGHT = 720
FPS = 60

BG = (22, 34, 45)
ROAD = (63, 68, 73)
LANE = (210, 210, 210)
PANEL = (245, 248, 250)
TEXT = (28, 42, 55)
MUTED = (92, 108, 120)
GREEN = (46, 160, 92)
RED = (205, 70, 70)
YELLOW = (225, 174, 62)
CAR_A = (52, 145, 210)
CAR_B = (235, 151, 62)
WHITE = (255, 255, 255)


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


def world_to_screen(vehicle) -> tuple[int, int]:
    center_x, center_y = 475, 360

    if vehicle.origin_axis == BARAO_AXIS:
        # Eixo horizontal: Oeste -> Leste
        x = center_x + int(vehicle.position * 2.15)
        y = center_y - 36
        return x, y

    # Eixo vertical: Sul -> Norte
    x = center_x + 36
    y = center_y - int(vehicle.position * 2.15)
    return x, y


def draw_road(screen: pygame.Surface) -> None:
    pygame.draw.rect(screen, ROAD, pygame.Rect(0, 285, 950, 150))
    pygame.draw.rect(screen, ROAD, pygame.Rect(400, 0, 150, 720))

    # Linhas centrais
    for x in range(10, 940, 42):
        pygame.draw.line(screen, LANE, (x, 360), (x + 22, 360), 2)
    for y in range(10, 710, 42):
        pygame.draw.line(screen, LANE, (475, y), (475, y + 22), 2)

    # Linhas de parada
    pygame.draw.line(screen, WHITE, (386, 290), (386, 430), 5)
    pygame.draw.line(screen, WHITE, (405, 450), (545, 450), 5)


def draw_signal(screen: pygame.Surface, phase: str) -> None:
    # Barão/Maynard
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(365, 245, 38, 82), border_radius=6)
    pygame.draw.circle(screen, GREEN if phase == "BARAO_GREEN" else RED, (384, 286), 11)

    # Augusto Franco
    pygame.draw.rect(screen, (25, 25, 25), pygame.Rect(560, 438, 82, 38), border_radius=6)
    pygame.draw.circle(screen, GREEN if phase == "AUGUSTO_GREEN" else RED, (601, 457), 11)


def draw_vehicles(screen: pygame.Surface, simulator: TrafficDemandSimulator) -> None:
    for vehicle in simulator.active_vehicles:
        x, y = world_to_screen(vehicle)
        if vehicle.origin_axis == BARAO_AXIS:
            rect = pygame.Rect(x - 18, y - 9, 36, 18)
            color = CAR_A
        else:
            rect = pygame.Rect(x - 9, y - 18, 18, 36)
            color = CAR_B

        if vehicle.state == "QUEUED":
            pygame.draw.rect(screen, color, rect, border_radius=4)
            pygame.draw.rect(screen, WHITE, rect, 2, border_radius=4)
        else:
            pygame.draw.rect(screen, color, rect, border_radius=4)


def draw_panel(
    screen: pygame.Surface,
    fonts: dict[str, pygame.font.Font],
    simulator: TrafficDemandSimulator,
    controller_name: str,
    phase: str,
    paused: bool,
    speed_multiplier: float,
) -> None:
    pygame.draw.rect(screen, PANEL, pygame.Rect(950, 0, 330, 720))

    def text(value: str, y: int, font: str = "body", color=TEXT):
        surface = fonts[font].render(value, True, color)
        screen.blit(surface, (980, y))

    text("SERGIPE TRAFFIC AI", 35, "title")
    text("Protótipo visual — Check-in 2", 73, "small", MUTED)

    text("Cenário piloto", 120, "heading")
    text("Aracaju / Sergipe", 154)
    text("Augusto Franco × Des. Maynard", 180, "small", MUTED)

    text("Controle", 230, "heading")
    text(f"Controlador: {controller_name.upper()}", 266)
    text(f"Fase: {phase}", 292, "small", MUTED)

    text("Telemetria", 342, "heading")
    text(f"Tempo: {simulator.current_time:6.1f} s", 378)
    text(f"Fila Barão/Maynard: {simulator.queue_length(BARAO_AXIS)}", 407)
    text(f"Fila Augusto Franco: {simulator.queue_length(AUGUSTO_AXIS)}", 436)
    text(f"Espera média: {simulator.average_wait():.1f} s", 465)
    text(f"Veículos ativos: {len(simulator.active_vehicles)}", 494)
    text(f"Veículos concluídos: {simulator.completed_vehicles_count}", 523)

    text("Dados", 573, "heading")
    text("Demanda: sintética / seed reproduzível", 607, "small", MUTED)
    text("Rede: cenário inspirado em Aracaju", 630, "small", MUTED)

    state = "PAUSADO" if paused else f"{speed_multiplier:g}x"
    text(f"[ESPAÇO] pausa  [R] reset  [1/2] controle  [{state}]", 674, "small", MUTED)


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

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Sergipe Traffic AI — Check-in 2")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("segoeui", 28, bold=True),
        "heading": pygame.font.SysFont("segoeui", 19, bold=True),
        "body": pygame.font.SysFont("segoeui", 17),
        "small": pygame.font.SysFont("segoeui", 13),
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
                    simulator.reset()
                    controller.reset(scenario)
                    current_phase = "BARAO_GREEN"
                elif event.key == pygame.K_1:
                    controller_name = "fixed"
                    controller = build_controller(controller_name)
                    controller.reset(scenario)
                elif event.key == pygame.K_2:
                    controller_name = "adaptive"
                    controller = build_controller(controller_name)
                    controller.reset(scenario)
                elif event.key == pygame.K_UP:
                    speed_multiplier = min(8.0, speed_multiplier * 2.0)
                elif event.key == pygame.K_DOWN:
                    speed_multiplier = max(0.5, speed_multiplier / 2.0)

        if not paused:
            accumulator += real_dt * speed_multiplier

            while accumulator >= simulator.time_step_s:
                simulator.generate_vehicles_step()
                observation = axis_observation(simulator)

                if controller_name == "fixed":
                    current_phase = controller.decide(observation, simulator.current_time)
                else:
                    current_phase = controller.decide(observation, simulator.current_time)

                simulator.step(current_phase)
                accumulator -= simulator.time_step_s

                if simulator.current_time >= simulator.duration_s:
                    paused = True
                    break

        screen.fill(BG)
        draw_road(screen)
        draw_signal(screen, current_phase)
        draw_vehicles(screen, simulator)
        draw_panel(
            screen,
            fonts,
            simulator,
            controller_name,
            current_phase,
            paused,
            speed_multiplier,
        )

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
