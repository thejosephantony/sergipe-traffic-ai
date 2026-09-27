from __future__ import annotations

import math
from array import array

import pygame


def synth_tone(
    frequency_hz: float,
    duration_s: float,
    volume: float = 0.18,
    sample_rate: int = 44_100,
) -> bytes:
    """Gera um tom PCM mono de 16 bits com envelope suave."""
    frame_count = max(1, int(duration_s * sample_rate))
    amplitude = int(32_767 * max(0.0, min(volume, 1.0)))
    samples = array("h")

    fade_frames = max(1, min(frame_count // 3, int(sample_rate * 0.02)))

    for index in range(frame_count):
        envelope = 1.0
        if index < fade_frames:
            envelope = index / fade_frames
        elif index >= frame_count - fade_frames:
            envelope = (frame_count - index - 1) / fade_frames

        value = amplitude * envelope * math.sin(
            2.0 * math.pi * frequency_hz * index / sample_rate
        )
        samples.append(int(value))

    return samples.tobytes()


class AudioManager:
    """Feedback sonoro discreto e opcional para mudanças de fase."""

    def __init__(self) -> None:
        self.available = False
        self.enabled = True
        self.sounds: dict[str, pygame.mixer.Sound] = {}

        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(
                    frequency=44_100,
                    size=-16,
                    channels=1,
                    buffer=512,
                )

            self.sounds = {
                "green": pygame.mixer.Sound(
                    buffer=synth_tone(660.0, 0.08, 0.12)
                ),
                "yellow": pygame.mixer.Sound(
                    buffer=synth_tone(420.0, 0.12, 0.12)
                ),
                "all_red": pygame.mixer.Sound(
                    buffer=synth_tone(260.0, 0.10, 0.10)
                ),
                "ui": pygame.mixer.Sound(
                    buffer=synth_tone(820.0, 0.05, 0.08)
                ),
            }
            self.available = True
        except pygame.error:
            self.available = False
            self.enabled = False

    @property
    def is_enabled(self) -> bool:
        return self.available and self.enabled

    def toggle(self) -> bool:
        if self.available:
            self.enabled = not self.enabled
        return self.is_enabled

    def play_ui(self) -> None:
        self._play("ui")

    def play_phase(self, phase: str) -> None:
        if phase in {"BARAO_YELLOW", "AUGUSTO_YELLOW"}:
            self._play("yellow")
        elif phase in {"ALL_RED_TO_AUGUSTO", "ALL_RED_TO_BARAO"}:
            self._play("all_red")
        elif phase in {"BARAO_GREEN", "AUGUSTO_GREEN"}:
            self._play("green")

    def _play(self, sound_name: str) -> None:
        if not self.is_enabled:
            return

        sound = self.sounds.get(sound_name)
        if sound is not None:
            sound.play()
