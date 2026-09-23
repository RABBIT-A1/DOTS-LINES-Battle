# -*- coding: utf-8 -*-
"""Pygame 音效管理器。"""

from pathlib import Path

import pygame


class AudioManager:
    VOLUMES = {
        "ui_click": 0.34,
        "draw_start": 0.38,
        "turn": 0.42,
        "invalid": 0.40,
        "hit": 0.52,
        "victory": 0.55,
    }

    def __init__(self):
        self.enabled = False
        self.sounds = {}
        audio_dir = (
            Path(__file__).resolve().parents[1] / "assets" / "audio"
        )
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init()
            for name, volume in self.VOLUMES.items():
                path = audio_dir / f"{name}.wav"
                if not path.is_file():
                    continue
                sound = pygame.mixer.Sound(str(path))
                sound.set_volume(volume)
                self.sounds[name] = sound
            self.enabled = bool(self.sounds)
        except (pygame.error, OSError):
            self.enabled = False

    def play(self, name):
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
