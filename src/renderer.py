# -*- coding: utf-8 -*-
"""LoFi 日系动画插画风格的 Pygame 渲染层与 UI V1。"""

import os

import pygame

from .config import (
    ARENA_H,
    ARENA_W,
    ARENA_X,
    ARENA_Y,
    CONFIRMED_LINE_WIDTH,
    DEFAULT_LERP_SPEED,
    DIM_TEXT,
    DOT_RADIUS,
    MARGIN,
    MAX_LERP_SPEED,
    MIN_LERP_SPEED,
    SCREEN_H,
    SCREEN_W,
)
from .geometry import clamp
from .theme import (
    ACCENT_DEEP,
    ACCENT_SOFT,
    BG_COLOR,
    CLOUD,
    HILL_FAR,
    HILL_MID,
    HILL_NEAR,
    HUD_BG,
    INK_SOFT,
    KILL_COLOR,
    MOON,
    P1_COLOR,
    P1_LIGHT,
    P2_COLOR,
    PANEL_BG,
    PANEL_BORDER,
    SKY_BOTTOM,
    SKY_TOP,
    TEXT_COLOR,
    TOAST_DEEP,
    TOAST_LIGHT,
    TOAST_TEXT_DARK,
    TOAST_TEXT_LIGHT,
    TRAIL_COLOR_P1,
    TRAIL_COLOR_P2,
    WARN_COLOR,
    WHITE_SOFT,
)
from .ui import Button, draw_panel, draw_wrapped_text

RULE_SECTIONS = (
    (
        "基本规则",
        (
            "每名玩家控制一个点，按住鼠标左键画线；松开左键结束回合。",
            "线穿过对方的点即可击杀。每名玩家第一次离开出生点的行动为“出击”，出击不能杀人。",
            "一次行动最多允许一次明显掉头；方向再次反转会立即停止并结算当前轨迹。",
        ),
    ),
    (
        "画线判定",
        (
            "画线需要快速且连续。明显停顿、持续减速或超过时间上限时，本次画线无效。",
            "无效画线会回到本回合起点，玩家仍可继续尝试，不会直接跳过回合。",
            "点不能停留在地图边缘；结算时会沿路径回退到安全区域。",
        ),
    ),
    (
        "AI 与提示",
        (
            "AI 出击回合完全随机，从第二回合开始寻找红点，并在目标附近加入瞄准偏差。",
            "AI 使用慢—快—慢的自然速度完成掉头，回合结束后不保留轨迹。",
            "所有重要消息都会从顶部弹出并淡出。",
        ),
    ),
)


def lerp_color(color_a, color_b, ratio):
    ratio = clamp(ratio, 0.0, 1.0)
    return tuple(
        int(round(a + (b - a) * ratio))
        for a, b in zip(color_a, color_b)
    )


def load_game_font(size, bold=False):
    """直接加载字体文件，绕过旧版 pygame 的 SysFont 枚举崩溃。"""
    windows_dir = os.environ.get("WINDIR", r"C:\Windows")
    font_dir = os.path.join(windows_dir, "Fonts")
    candidates = (
        "msyh.ttc",
        "msyh.ttf",
        "simhei.ttf",
        "simsun.ttc",
        "arial.ttf",
    )

    for filename in candidates:
        font_path = os.path.join(font_dir, filename)
        if not os.path.isfile(font_path):
            continue
        try:
            font = pygame.font.Font(font_path, size)
            font.set_bold(bold)
            return font
        except (IOError, OSError, TypeError, pygame.error):
            continue

    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


class Slider:
    def __init__(self, x, y, w, h, min_val, max_val, default_val, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.min_val = min_val
        self.max_val = max_val
        self.value = default_val
        self.label = label
        self.dragging = False

    def get_knob_x(self):
        ratio = (
            (self.value - self.min_val)
            / (self.max_val - self.min_val)
        )
        return self.rect.x + int(ratio * self.rect.w)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            knob_x = self.get_knob_x()
            knob_rect = pygame.Rect(
                knob_x - 11, self.rect.y - 7, 22, self.rect.h + 14
            )
            if (
                knob_rect.collidepoint(event.pos)
                or self.rect.collidepoint(event.pos)
            ):
                self.dragging = True
                self._update_value(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._update_value(event.pos[0])

    def _update_value(self, mouse_x):
        ratio = clamp(
            (mouse_x - self.rect.x) / self.rect.w, 0, 1
        )
        self.value = (
            self.min_val
            + ratio * (self.max_val - self.min_val)
        )

    def draw(self, surface, font):
        label = font.render(
            f"{self.label}  {self.value:.2f}", True, TEXT_COLOR
        )
        surface.blit(label, (self.rect.x, self.rect.y - 29))

        track = pygame.Rect(
            self.rect.x, self.rect.y + 4, self.rect.w, 6
        )
        pygame.draw.rect(
            surface, (190, 207, 214), track, border_radius=3
        )
        fill = pygame.Rect(
            self.rect.x,
            self.rect.y + 4,
            self.get_knob_x() - self.rect.x,
            6,
        )
        if fill.width > 0:
            pygame.draw.rect(
                surface, ACCENT_DEEP, fill, border_radius=3
            )
        knob = (self.get_knob_x(), self.rect.y + 7)
        pygame.draw.circle(surface, WHITE_SOFT, knob, 10)
        pygame.draw.circle(surface, ACCENT_DEEP, knob, 10, 2)


class Renderer:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("点线大作战 — LoFi UI V1")
        self.clock = pygame.time.Clock()
        self.surface = self.screen

        self.font_logo = load_game_font(64, bold=True)
        self.font_large = load_game_font(42, bold=True)
        self.font_medium = load_game_font(26)
        self.font_small = load_game_font(18)
        self.font_tiny = load_game_font(14)

        self.slider = Slider(
            430,
            408,
            420,
            20,
            MIN_LERP_SPEED,
            MAX_LERP_SPEED,
            DEFAULT_LERP_SPEED,
            "鼠标灵敏度",
        )

        self.title_buttons = (
            Button(
                pygame.Rect(450, 478, 380, 50),
                "开始游戏",
                "start",
                "primary",
            ),
            Button(
                pygame.Rect(450, 540, 380, 46),
                "查看规则",
                "rules",
                "secondary",
            ),
        )
        self.rules_buttons = (
            Button(
                pygame.Rect(468, 574, 150, 46),
                "返回标题",
                "back",
                "secondary",
            ),
            Button(
                pygame.Rect(662, 574, 150, 46),
                "开始游戏",
                "start",
                "primary",
            ),
        )
        self.game_over_buttons = (
            Button(
                pygame.Rect(438, 438, 190, 48),
                "重新开始",
                "restart",
                "primary",
            ),
            Button(
                pygame.Rect(652, 438, 190, 48),
                "返回标题",
                "menu",
                "secondary",
            ),
        )

        self.rules_tab_rects = tuple(
            pygame.Rect(254 + index * 252, 137, 232, 44)
            for index in range(len(RULE_SECTIONS))
        )

        self.background = self._create_background()

    # ------------------------------------------------------------------
    # 背景插画
    # ------------------------------------------------------------------
    def _create_background(self):
        surface = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            ratio = y / max(SCREEN_H - 1, 1)
            color = lerp_color(SKY_TOP, SKY_BOTTOM, ratio)
            pygame.draw.line(surface, color, (0, y), (SCREEN_W, y))

        pygame.draw.circle(surface, MOON, (1060, 128), 54)
        pygame.draw.circle(surface, (239, 237, 218), (1060, 128), 43)

        # 少量、完整的大云团。
        for cloud in (
            ((170, 135), (145, 34)),
            ((275, 154), (105, 27)),
            ((870, 208), (130, 30)),
        ):
            center, radius = cloud
            pygame.draw.ellipse(
                surface,
                CLOUD,
                pygame.Rect(
                    center[0] - radius[0],
                    center[1] - radius[1],
                    radius[0] * 2,
                    radius[1] * 2,
                ),
            )

        far = [(0, 430), (160, 350), (330, 415), (520, 320),
               (710, 410), (900, 345), (1090, 405), (1280, 335),
               (1280, 720), (0, 720)]
        mid = [(0, 505), (185, 430), (405, 505), (640, 420),
               (855, 510), (1080, 435), (1280, 495),
               (1280, 720), (0, 720)]
        near = [(0, 590), (235, 520), (470, 600), (735, 505),
                (1000, 595), (1280, 525), (1280, 720), (0, 720)]
        pygame.draw.polygon(surface, HILL_FAR, far)
        pygame.draw.polygon(surface, HILL_MID, mid)
        pygame.draw.polygon(surface, HILL_NEAR, near)

        # 概括化的树影，不添加厚重纹理。
        for x, height in ((95, 86), (170, 60), (1160, 78), (1225, 105)):
            pygame.draw.rect(
                surface,
                (86, 122, 137),
                pygame.Rect(x, 600 - height, 10, height + 120),
                border_radius=5,
            )
            pygame.draw.circle(
                surface,
                (96, 135, 145),
                (x + 5, 600 - height),
                34,
            )
        return surface

    # ------------------------------------------------------------------
    # 基础场景
    # ------------------------------------------------------------------
    def draw_arena(self):
        rect = pygame.Rect(ARENA_X, ARENA_Y, ARENA_W, ARENA_H)
        draw_panel(
            self.surface,
            rect,
            radius=24,
            fill=(225, 235, 238, 238),
            border=(126, 155, 170, 235),
            shadow=True,
        )
        inner = pygame.Rect(
            ARENA_X + MARGIN,
            ARENA_Y + MARGIN,
            ARENA_W - 2 * MARGIN,
            ARENA_H - 2 * MARGIN,
        )
        pygame.draw.rect(
            self.surface,
            (205, 221, 227),
            inner,
            width=1,
            border_radius=16,
        )

    def draw_spawn(self, player):
        rect = player.spawn_rect
        surface = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        surface.fill((*player.color, 34))
        self.surface.blit(surface, (rect[0], rect[1]))
        pygame.draw.rect(
            self.surface,
            (*player.color, 150),
            rect,
            width=2,
            border_radius=10,
        )
        label = self.font_tiny.render("出生点", True, INK_SOFT)
        self.surface.blit(
            label,
            (
                rect[0] + rect[2] // 2 - label.get_width() // 2,
                rect[1] + 7,
            ),
        )

    def draw_dot(self, position, color, radius=DOT_RADIUS):
        center = (int(position[0]), int(position[1]))
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 50), (15, 15), 14)
        pygame.draw.circle(glow, (*color, 95), (15, 15), 8)
        self.surface.blit(glow, (center[0] - 15, center[1] - 15))
        pygame.draw.circle(self.surface, color, center, radius + 2)
        pygame.draw.circle(
            self.surface, WHITE_SOFT, center, radius, 1
        )

    def draw_line_segment(self, a, b, color, width=3):
        pygame.draw.line(
            self.surface,
            color,
            (int(a[0]), int(a[1])),
            (int(b[0]), int(b[1])),
            width,
        )

    def draw_confirmed_lines(self, game):
        for segment in game.p1.line_segments:
            self.draw_line_segment(
                segment[0],
                segment[1],
                P1_COLOR,
                CONFIRMED_LINE_WIDTH,
            )

    def draw_trail(self, player, trail_color):
        if len(player.trail) < 2:
            return
        count = len(player.trail)
        for i in range(count - 1):
            progress = i / max(count - 1, 1)
            alpha = int(75 + 155 * progress)
            color = (*trail_color[:3], alpha)
            a, b = player.trail[i], player.trail[i + 1]
            width = max(1, int(1 + 3 * progress))
            pygame.draw.line(
                self.surface,
                color,
                (int(a[0]), int(a[1])),
                (int(b[0]), int(b[1])),
                width,
            )

    def draw_trail_glow(self, player, trail_color):
        if not player.trail:
            return
        head = player.trail[-1]
        glow = pygame.Surface((34, 34), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*trail_color, 55), (17, 17), 16)
        pygame.draw.circle(glow, (*trail_color, 125), (17, 17), 7)
        self.surface.blit(
            glow, (int(head[0]) - 17, int(head[1]) - 17)
        )

    # ------------------------------------------------------------------
    # HUD 与消息
    # ------------------------------------------------------------------
    def draw_player_card(self, game, player, rect, align_right=False):
        draw_panel(
            self.surface,
            rect,
            radius=16,
            fill=HUD_BG,
            border=PANEL_BORDER,
            shadow=True,
        )
        dot_color = (*player.color, 255)
        pygame.draw.circle(
            self.surface,
            player.color,
            (rect.x + 27, rect.centery),
            10,
        )
        pygame.draw.circle(
            self.surface,
            WHITE_SOFT,
            (rect.x + 27, rect.centery),
            10,
            2,
        )

        name = self.font_small.render(
            player.name, True, TEXT_COLOR
        )
        name_x = rect.x + 48
        if align_right:
            name_x = rect.right - 24 - name.get_width()
        self.surface.blit(name, (name_x, rect.y + 12))

        status = "出击待命" if player.is_launch else "已离开出生点"
        status_color = ACCENT_DEEP if player.is_launch else DIM_TEXT
        status_text = self.font_tiny.render(status, True, status_color)
        status_x = rect.x + 48
        if align_right:
            status_x = rect.right - 24 - status_text.get_width()
        self.surface.blit(status_text, (status_x, rect.y + 38))
        del dot_color

    def draw_hud(self, game):
        left_rect = pygame.Rect(40, 24, 278, 66)
        right_rect = pygame.Rect(962, 24, 278, 66)
        self.draw_player_card(game, game.p1, left_rect)
        self.draw_player_card(game, game.p2, right_rect, align_right=True)

        turn_rect = pygame.Rect(474, 24, 332, 66)
        draw_panel(
            self.surface,
            turn_rect,
            radius=18,
            fill=PANEL_BG,
            border=PANEL_BORDER,
            shadow=True,
        )
        player = game.current_player
        turn_text = f"回合 {game.turn_number}  ·  {player.name}"
        label = self.font_medium.render(turn_text, True, player.color)
        self.surface.blit(
            label,
            (
                turn_rect.centerx - label.get_width() // 2,
                turn_rect.centery - label.get_height() // 2,
            ),
        )

    def draw_message(self, game):
        if not game.message or game.message_timer <= 0:
            return

        total_frames = 90.0
        elapsed = total_frames - game.message_timer
        enter_ratio = clamp(elapsed / 12.0, 0.0, 1.0)
        exit_ratio = clamp((game.message_timer - 18) / 18.0, 0.0, 1.0)
        fade_ratio = min(enter_ratio, exit_ratio)
        eased = 1 - (1 - enter_ratio) ** 3

        width = min(760, max(330, len(game.message) * 24 + 90))
        height = 50
        y = int(-height + (100 + height) * eased)
        rect = pygame.Rect(
            SCREEN_W // 2 - width // 2,
            y,
            width,
            height,
        )

        warning = any(
            keyword in game.message
            for keyword in ("无效", "过慢", "不连续", "必须")
        )
        light = WARN_COLOR if warning else TOAST_LIGHT
        deep = (153, 104, 74) if warning else TOAST_DEEP
        background = lerp_color(light, deep, clamp(elapsed / 18.0, 0, 1))
        text_background = lerp_color(
            TOAST_TEXT_DARK,
            TOAST_TEXT_LIGHT,
            clamp(elapsed / 18.0, 0, 1),
        )

        layer = pygame.Surface((width, height + 14), pygame.SRCALPHA)
        shadow = pygame.Rect(0, 7, width, height)
        pygame.draw.rect(
            layer, (55, 75, 87, int(44 * fade_ratio)), shadow,
            border_radius=16,
        )
        fill = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(
            layer,
            (*background, int(246 * fade_ratio)),
            fill,
            border_radius=16,
        )
        pygame.draw.rect(
            layer,
            (*text_background, int(150 * fade_ratio)),
            fill,
            width=1,
            border_radius=16,
        )
        label = self.font_small.render(
            game.message, True, text_background
        )
        layer.blit(
            label,
            (
                width // 2 - label.get_width() // 2,
                height // 2 - label.get_height() // 2,
            ),
        )
        self.surface.blit(layer, (rect.x, rect.y - 7))

    # ------------------------------------------------------------------
    # 页面
    # ------------------------------------------------------------------
    def draw_title(self, game):
        self.surface.blit(self.background, (0, 0))
        veil = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        veil.fill((224, 235, 239, 66))
        self.surface.blit(veil, (0, 0))

        panel_rect = pygame.Rect(360, 116, 560, 520)
        draw_panel(
            self.surface,
            panel_rect,
            radius=28,
            fill=(244, 248, 247, 238),
            border=(144, 169, 179, 220),
            shadow=True,
        )

        shadow = self.font_logo.render(
            "点线大作战", True, (137, 166, 178)
        )
        self.surface.blit(
            shadow,
            (
                SCREEN_W // 2 - shadow.get_width() // 2 + 2,
                156 + 3,
            ),
        )
        title = self.font_logo.render(
            "点线大作战", True, TEXT_COLOR
        )
        self.surface.blit(
            title,
            (
                SCREEN_W // 2 - title.get_width() // 2,
                156,
            ),
        )
        subtitle = self.font_small.render(
            "DOTS  &  LINES  BATTLE", True, ACCENT_DEEP
        )
        self.surface.blit(
            subtitle,
            (
                SCREEN_W // 2 - subtitle.get_width() // 2,
                235,
            ),
        )

        rule_line = self.font_small.render(
            "画出一条线，穿过对方的点。", True, INK_SOFT
        )
        self.surface.blit(
            rule_line,
            (
                SCREEN_W // 2 - rule_line.get_width() // 2,
                287,
            ),
        )
        divider = pygame.Rect(430, 330, 420, 1)
        pygame.draw.rect(self.surface, (177, 198, 207), divider)

        self.slider.draw(self.surface, self.font_small)
        mouse_position = pygame.mouse.get_pos()
        for button in self.title_buttons:
            button.draw(self.surface, self.font_small, mouse_position)

        version = self.font_tiny.render(
            "LoFi UI V1  ·  v0.6.0", True, DIM_TEXT
        )
        self.surface.blit(
            version,
            (
                SCREEN_W // 2 - version.get_width() // 2,
                664,
            ),
        )

    def draw_rules(self, game):
        self.surface.blit(self.background, (0, 0))
        veil = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        veil.fill((77, 104, 119, 92))
        self.surface.blit(veil, (0, 0))

        panel_rect = pygame.Rect(148, 62, 984, 594)
        draw_panel(
            self.surface,
            panel_rect,
            radius=28,
            fill=(245, 248, 248, 244),
            border=(153, 177, 187, 230),
            shadow=True,
        )
        title = self.font_large.render(
            "游戏规则", True, TEXT_COLOR
        )
        self.surface.blit(title, (204, 84))

        mouse_position = pygame.mouse.get_pos()
        for index, rect in enumerate(self.rules_tab_rects):
            selected = game.rules_section == index
            hovered = rect.collidepoint(mouse_position)
            if selected:
                fill = ACCENT_DEEP
                text_color = WHITE_SOFT
            elif hovered:
                fill = (218, 231, 234)
                text_color = TEXT_COLOR
            else:
                fill = (230, 238, 240)
                text_color = INK_SOFT
            pygame.draw.rect(
                self.surface, fill, rect, border_radius=12
            )
            pygame.draw.rect(
                self.surface,
                ACCENT_DEEP if selected else (163, 184, 193),
                rect,
                width=1,
                border_radius=12,
            )
            label = self.font_small.render(
                RULE_SECTIONS[index][0], True, text_color
            )
            self.surface.blit(
                label,
                (
                    rect[0] + rect[2] // 2 - label.get_width() // 2,
                    rect.centery - label.get_height() // 2,
                ),
            )

        heading, paragraphs = RULE_SECTIONS[game.rules_section]
        section_title = self.font_medium.render(
            heading, True, ACCENT_DEEP
        )
        self.surface.blit(section_title, (216, 214))

        content_rect = pygame.Rect(216, 266, 848, 270)
        y = content_rect.y
        for number, paragraph in enumerate(paragraphs, start=1):
            marker = self.font_medium.render(
                f"{number:02d}", True, (169, 194, 202)
            )
            self.surface.blit(marker, (content_rect.x, y))
            text_rect = pygame.Rect(
                content_rect.x + 64, y, content_rect.width - 64, 76
            )
            y = (
                draw_wrapped_text(
                    self.surface,
                    paragraph,
                    self.font_small,
                    TEXT_COLOR,
                    text_rect,
                    line_gap=8,
                )
                + 14
            )

        mouse_position = pygame.mouse.get_pos()
        for button in self.rules_buttons:
            button.draw(self.surface, self.font_small, mouse_position)

        page_hint = self.font_tiny.render(
            "← / → 切换章节  ·  ESC 返回", True, DIM_TEXT
        )
        self.surface.blit(page_hint, (216, 610))

    def draw_game_over(self, game):
        if game.state != "GAME_OVER":
            return
        effect_active = bool(game.effects.shards) or game.effects.flash_frames > 0
        if effect_active:
            return

        overlay = pygame.Surface(
            self.surface.get_size(), pygame.SRCALPHA
        )
        overlay.fill((48, 67, 78, 155))
        self.surface.blit(overlay, (0, 0))

        panel_rect = pygame.Rect(356, 230, 568, 292)
        draw_panel(
            self.surface,
            panel_rect,
            radius=28,
            fill=(245, 248, 248, 246),
            border=(151, 176, 186, 235),
            shadow=True,
        )
        label = self.font_small.render(
            "对 局 结 束", True, ACCENT_DEEP
        )
        self.surface.blit(
            label,
            (
                panel_rect.centerx - label.get_width() // 2,
                270,
            ),
        )

        if game.winner:
            winner = self.font_large.render(
                f"{game.winner.name} 获胜",
                True,
                game.winner.color,
            )
            self.surface.blit(
                winner,
                (
                    panel_rect.centerx - winner.get_width() // 2,
                    320,
                ),
            )
        flourish = pygame.Rect(486, 386, 308, 2)
        pygame.draw.rect(
            self.surface, (184, 204, 211), flourish
        )

        mouse_position = pygame.mouse.get_pos()
        for button in self.game_over_buttons:
            button.draw(self.surface, self.font_small, mouse_position)

    def draw_playing(self, game):
        self.surface.blit(self.background, (0, 0))
        self.draw_arena()
        self.draw_spawn(game.p1)
        self.draw_spawn(game.p2)
        self.draw_confirmed_lines(game)

        if (
            game.state == "DRAW"
            and game.current_player == game.p1
            and game.mouse_held
        ):
            self.draw_trail(game.p1, TRAIL_COLOR_P1)
            self.draw_trail_glow(game.p1, TRAIL_COLOR_P1)
        elif game.state == "DRAW" and game.current_player == game.p2:
            self.draw_trail(game.p2, TRAIL_COLOR_P2)
            self.draw_trail_glow(game.p2, TRAIL_COLOR_P2)

        loser_hidden = (
            game.state == "GAME_OVER" and game.winner is not None
        )
        if game.p1.dot_pos and not (
            loser_hidden and game.p1 == game.other_player
        ):
            self.draw_dot(game.p1.dot_pos, P1_COLOR)
        if game.p2.dot_pos and not (
            loser_hidden and game.p2 == game.other_player
        ):
            self.draw_dot(game.p2.dot_pos, P2_COLOR)

        self.draw_hud(game)
        self.draw_message(game)
        self.draw_game_over(game)
        game.effects.draw(self.surface)

    def draw(self, game):
        shaking = game.effects.shake_frames > 0
        if shaking:
            canvas = pygame.Surface((SCREEN_W, SCREEN_H))
            canvas.fill(BG_COLOR)
            self.surface = canvas
            self._dispatch(game)
            self.screen.fill(BG_COLOR)
            self.screen.blit(canvas, game.effects.shake_offset)
        else:
            self.surface = self.screen
            self._dispatch(game)
        pygame.display.flip()

    def _dispatch(self, game):
        if game.state == "TITLE":
            self.draw_title(game)
        elif game.state == "RULES":
            self.draw_rules(game)
        else:
            self.draw_playing(game)
