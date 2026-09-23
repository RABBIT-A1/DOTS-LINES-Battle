# -*- coding: utf-8 -*-
"""可复用的 Pygame UI 组件。"""

from dataclasses import dataclass
from typing import Optional

import pygame

from .theme import (
    BUTTON_BORDER,
    BUTTON_DISABLED,
    BUTTON_PRIMARY,
    BUTTON_PRIMARY_HOVER,
    BUTTON_SECONDARY,
    BUTTON_SECONDARY_HOVER,
    BUTTON_TEXT,
    INK_FAINT,
    INK_SOFT,
    PANEL_BORDER,
    PANEL_SHADOW,
    WHITE_SOFT,
)


def draw_soft_shadow(
    surface,
    rect,
    radius=14,
    offset=(0, 5),
    color=PANEL_SHADOW,
):
    shadow_rect = pygame.Rect(rect)
    shadow_rect.move_ip(*offset)
    pygame.draw.rect(
        surface, color, shadow_rect, border_radius=radius
    )


def draw_panel(
    surface,
    rect,
    radius=14,
    fill=(245, 248, 248, 238),
    border=PANEL_BORDER,
    shadow=True,
):
    if shadow:
        draw_soft_shadow(surface, rect, radius)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(
        surface, border, rect, width=1, border_radius=radius
    )


@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str
    kind: str = "secondary"
    enabled: bool = True

    def contains(self, position):
        return self.rect.collidepoint(position)

    def hovered(self, mouse_position):
        return self.enabled and self.contains(mouse_position)

    def draw(self, surface, font, mouse_position):
        hovered = self.hovered(mouse_position)
        if not self.enabled:
            fill = BUTTON_DISABLED
            text_color = INK_FAINT
        elif self.kind == "primary":
            fill = BUTTON_PRIMARY_HOVER if hovered else BUTTON_PRIMARY
            text_color = BUTTON_TEXT
        else:
            fill = (
                BUTTON_SECONDARY_HOVER
                if hovered
                else BUTTON_SECONDARY
            )
            text_color = INK_SOFT

        draw_soft_shadow(
            surface,
            self.rect,
            radius=12,
            offset=(0, 4 if hovered else 3),
        )
        pygame.draw.rect(
            surface, fill, self.rect, border_radius=12
        )
        pygame.draw.rect(
            surface,
            BUTTON_BORDER if self.enabled else BUTTON_DISABLED,
            self.rect,
            width=1,
            border_radius=12,
        )

        label = font.render(self.label, True, text_color)
        surface.blit(
            label,
            (
                self.rect.centerx - label.get_width() // 2,
                self.rect.centery - label.get_height() // 2,
            ),
        )


def draw_badge(surface, rect, text, font, fill, text_color=WHITE_SOFT):
    pygame.draw.rect(surface, fill, rect, border_radius=rect.height // 2)
    label = font.render(text, True, text_color)
    surface.blit(
        label,
        (
            rect.centerx - label.get_width() // 2,
            rect.centery - label.get_height() // 2,
        ),
    )


def draw_wrapped_text(
    surface,
    text,
    font,
    color,
    rect,
    line_gap=7,
    max_width: Optional[int] = None,
):
    width = max_width or rect.width
    lines = []
    current = ""
    for character in text:
        candidate = current + character
        if font.size(candidate)[0] > width and current:
            lines.append(current)
            current = character
        else:
            current = candidate
    if current:
        lines.append(current)

    y = rect.y
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        rendered = font.render(line, True, color)
        surface.blit(rendered, (rect.x, y))
        y += font.get_height() + line_gap
    return y
