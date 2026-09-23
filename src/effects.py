# -*- coding: utf-8 -*-
"""轻量视觉反馈：震动、击杀闪光与碎片。"""

import math
import random

import pygame

from .theme import WHITE_SOFT


class Effects:
    def __init__(self):
        self.shake_frames = 0
        self.shake_duration = 14
        self.flash_frames = 0
        self.flash_duration = 10
        self.shards = []

    def trigger_shake(self, duration=14):
        self.shake_duration = max(1, duration)
        self.shake_frames = self.shake_duration

    def trigger_kill(self, position, color, duration=60):
        self.flash_frames = self.flash_duration
        self.trigger_shake(16)
        self.shards.clear()
        for _ in range(18):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(1.4, 5.2)
            self.shards.append(
                {
                    "x": float(position[0]),
                    "y": float(position[1]),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - 0.8,
                    "angle": angle,
                    "spin": random.uniform(-0.22, 0.22),
                    "size": random.uniform(2.5, 7.0),
                    "life": duration,
                    "max_life": duration,
                    "color": color,
                }
            )

    @property
    def shake_offset(self):
        if self.shake_frames <= 0:
            return (0, 0)
        progress = self.shake_frames / self.shake_duration
        strength = 4.0 * progress
        phase = self.shake_frames * 1.7
        return (
            int(round(math.sin(phase) * strength)),
            int(round(math.cos(phase * 1.3) * strength * 0.45)),
        )

    def update(self):
        if self.shake_frames > 0:
            self.shake_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1

        alive = []
        for shard in self.shards:
            shard["life"] -= 1
            if shard["life"] <= 0:
                continue
            shard["x"] += shard["vx"]
            shard["y"] += shard["vy"]
            shard["vy"] += 0.11
            shard["vx"] *= 0.985
            shard["angle"] += shard["spin"]
            alive.append(shard)
        self.shards = alive

    def draw(self, surface):
        self._draw_shards(surface)
        self._draw_flash(surface)

    def _draw_shards(self, surface):
        for shard in self.shards:
            alpha = int(
                255 * (shard["life"] / shard["max_life"]) ** 0.85
            )
            size = shard["size"] * (
                0.65 + 0.35 * shard["life"] / shard["max_life"]
            )
            angle = shard["angle"]
            points = []
            for index in range(4):
                offset = angle + index * math.tau / 4
                points.append(
                    (
                        int(shard["x"] + math.cos(offset) * size),
                        int(
                            shard["y"]
                            + math.sin(offset) * size
                            * (0.55 if index % 2 else 1.0)
                        ),
                    )
                )
            layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
            color = (*shard["color"], alpha)
            pygame.draw.polygon(layer, color, points)
            surface.blit(layer, (0, 0))

    def _draw_flash(self, surface):
        if self.flash_frames <= 0:
            return
        ratio = self.flash_frames / self.flash_duration
        alpha = int(150 * ratio)
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        layer.fill((*WHITE_SOFT, alpha))
        surface.blit(layer, (0, 0))

