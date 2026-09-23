# -*- coding: utf-8 -*-
"""游戏状态机、回合结算与 AI 回合推进。"""

import math
import random
import sys

import pygame

from .ai import ai_plan_trail
from .collision import path_hits_point
from .config import (
    ARENA_H,
    ARENA_W,
    ARENA_X,
    ARENA_Y,
    DEFAULT_LERP_SPEED,
    FPS,
    MAX_LARGE_TURNS,
    MAX_LERP_SPEED,
    MIN_LERP_SPEED,
    MOUSE_TRACE_MAX_SCALE,
    MOUSE_TRACE_MIN_SCALE,
    P1_COLOR,
    P1_LIGHT,
    P2_COLOR,
    P2_LIGHT,
    SPEED_WINDOW_FRAMES,
)
from .audio import AudioManager
from .effects import Effects
from .input_handler import InputHandler
from .line import (
    adaptive_pause_seconds,
    check_trail_quality,
    motion_discontinuity_reason,
)
from .map import path_leaves_spawn, point_in_spawn, retract_to_boundary
from .player import Player
from .renderer import Renderer


class Game:
    def __init__(self):
        pygame.init()
        self.renderer = Renderer()
        self.input_handler = InputHandler()
        self.audio = AudioManager()
        self.effects = Effects()
        self.rules_section = 0

        spawn_width, spawn_height = 80, 60
        p1_spawn = (
            ARENA_X + 30,
            ARENA_Y + ARENA_H - spawn_height - 30,
            spawn_width,
            spawn_height,
        )
        p2_spawn = (
            ARENA_X + ARENA_W - spawn_width - 30,
            ARENA_Y + 30,
            spawn_width,
            spawn_height,
        )

        self.p1 = Player(p1_spawn, P1_COLOR, P1_LIGHT, "玩家1（红）")
        self.p2 = Player(
            p2_spawn, P2_COLOR, P2_LIGHT, "玩家2（蓝·AI）"
        )

        self.current_player = self.p1
        self.other_player = self.p2

        self.state = "TITLE"
        self.turn_number = 0
        self.message = ""
        self.message_timer = 0
        self.winner = None

        self.mouse_held = False
        self.last_mouse_target = None
        self.last_cursor_move_time = None
        self.pending_cursor_delta = (0, 0)
        self.lerp_speed = DEFAULT_LERP_SPEED
        self.turn_start_pos = None

        self.ai_trail_plan = []
        self.ai_trail_idx = 0
        self.ai_turn_point = None
        self.ai_draw_speed = 6

    def show_visual_rejection(self, text):
        self.show_message(text, 90)
        self.audio.play("invalid")
        self.effects.trigger_shake()

    def show_message(self, text, duration=90):
        self.message = text
        self.message_timer = duration

    def next_turn(self):
        # 当前玩家结算后才切换，避免提前结束另一名玩家的出击状态。
        self.current_player, self.other_player = (
            self.other_player,
            self.current_player,
        )
        self.turn_number += 1
        self.mouse_held = False
        self.pending_cursor_delta = (0, 0)
        self.ai_trail_plan = []
        self.ai_trail_idx = 0
        self.ai_turn_point = None
        self.current_player.begin_turn()
        self.turn_start_pos = self.current_player.dot_pos
        self.state = "DRAW"

    def start_game(self):
        self.p1.reset_for_new_game()
        self.p2.reset_for_new_game()
        self.current_player = self.p1
        self.other_player = self.p2
        self.turn_number = 1
        self.mouse_held = False
        self.pending_cursor_delta = (0, 0)
        self.current_player.begin_turn()
        self.turn_start_pos = self.current_player.dot_pos
        self.state = "DRAW"
        self.winner = None

    def resolve_turn(self, path_points):
        path_points = retract_to_boundary(path_points)
        if len(path_points) < 2:
            return False, None
        self.current_player.move_dot_to(path_points[-1])
        if self.current_player.is_launch:
            return False, None
        hit, target = path_hits_point(path_points, self.other_player.dot_pos)
        if hit:
            self.show_message("击中目标 · 对方点已碎裂", 90)
            self.effects.trigger_kill(target, self.other_player.color)
            self.audio.play("hit")
            self.audio.play("victory")
        return hit, target

    def invalidate_draw_attempt(self, reason="画线不连续"):
        """实时判定画线无效，回到本回合起点并允许重新画。"""
        pygame.event.set_grab(False)
        self.show_visual_rejection(reason)
        self.current_player.reset_draw_attempt(self.turn_start_pos)
        self.mouse_held = False
        self.last_cursor_move_time = None

    def end_draw_phase(self, forced_stop=False):
        """玩家画线结束；forced_stop 表示二次转向导致的强制停止。"""
        pygame.event.set_grab(False)
        player = self.current_player
        rules = player.get_draw_rules()

        if player.is_launch and not path_leaves_spawn(
            player, player.trail
        ):
            self.invalidate_draw_attempt("出击回合必须离开出生点")
            return

        if forced_stop:
            # 连续性和 1 秒上限优先于二次转向强制停止。
            motion_valid, motion_reason = check_trail_quality(
                player.trail,
                player.motion_distances,
                player.draw_frames,
                max_turns=MAX_LARGE_TURNS,
                min_average_speed=(
                    0.0
                    if rules.ignore_speed_check
                    else rules.min_average_speed
                ),
                max_draw_seconds=(
                    float("inf")
                    if rules.ignore_speed_check
                    else rules.max_draw_seconds
                ),
                check_turns=False,
            )
            if not motion_valid:
                self.show_visual_rejection(
                    f"画线无效（{motion_reason}），回退原点重试"
                )
                player.reset_draw_attempt(self.turn_start_pos)
                self.mouse_held = False
                return
        else:
            is_valid, reason = check_trail_quality(
                player.trail,
                player.motion_distances,
                player.draw_frames,
                max_turns=rules.max_turns,
                min_average_speed=(
                    0.0
                    if rules.ignore_speed_check
                    else rules.min_average_speed
                ),
                max_draw_seconds=(
                    float("inf")
                    if rules.ignore_speed_check
                    else rules.max_draw_seconds
                ),
            )
            if not is_valid:
                self.show_visual_rejection(
                    f"画线无效（{reason}），回退原点重试"
                )
                player.reset_draw_attempt(self.turn_start_pos)
                self.mouse_held = False
                return

        path_points = player.confirm_from_trail()
        hit, _ = self.resolve_turn(path_points)
        if hit:
            self.winner = self.current_player
            self.state = "GAME_OVER"
            return

        player.trail = []
        player.motion_distances = []
        player.line_segments = []
        player.end_turn()
        self.next_turn()

    def start_ai_turn(self):
        result = None
        for _ in range(20):
            candidate = ai_plan_trail(
                self.current_player, self.other_player.dot_pos
            )
            if path_leaves_spawn(self.current_player, candidate[0]):
                result = candidate
                break
            result = candidate

        trail, _, turn_point = result
        self.ai_trail_plan = trail
        self.ai_trail_idx = 0
        self.ai_turn_point = turn_point
        self.current_player.trail = []
        self.current_player.motion_distances = []

    def advance_ai_turn(self):
        if self.ai_trail_idx >= len(self.ai_trail_plan):
            self.current_player.trail = self.ai_trail_plan[:]
            if any(
                not point_in_spawn(point, self.current_player.spawn_rect)
                for point in self.current_player.trail
            ):
                self.current_player.has_left_spawn = True
            if self.ai_turn_point:
                self.current_player.has_turned = True
                self.current_player.turn_point = self.ai_turn_point

            path_points = self.current_player.confirm_from_trail()
            hit, _ = self.resolve_turn(path_points)

            self.current_player.trail = []
            self.current_player.motion_distances = []
            self.current_player.line_segments = []
            self.ai_trail_plan = []

            if hit:
                self.winner = self.current_player
                self.state = "GAME_OVER"
                return

            self.current_player.end_turn()
            self.next_turn()
            return

        progress = self.ai_trail_idx / max(
            len(self.ai_trail_plan) - 1, 1
        )
        wave = math.sin(math.pi * progress)
        speed_factor = 0.35 + 0.65 * (max(0.0, wave) ** 0.35)
        natural_variation = random.uniform(0.92, 1.08)
        current_speed = max(
            2,
            int(
                round(
                    2
                    + self.ai_draw_speed
                    * speed_factor
                    * natural_variation
                )
            ),
        )
        end_index = min(
            self.ai_trail_idx + current_speed,
            len(self.ai_trail_plan),
        )
        for i in range(self.ai_trail_idx, end_index):
            self.current_player.trail.append(self.ai_trail_plan[i])
        self.ai_trail_idx = end_index

        if self.current_player.trail:
            self.current_player.dot_pos = self.current_player.trail[-1]

    def update(self):
        if self.message_timer > 0:
            self.message_timer -= 1
        self.effects.update()

        if self.state == "DRAW" and self.current_player == self.p2:
            if not self.ai_trail_plan:
                self.start_ai_turn()
            self.advance_ai_turn()
            return

        if (
            self.state == "DRAW"
            and self.current_player == self.p1
            and self.mouse_held
        ):
            now = pygame.time.get_ticks()
            pause_limit = adaptive_pause_seconds(
                self.current_player.motion_distances
            )
            if (
                self.last_cursor_move_time is not None
                and now - self.last_cursor_move_time > pause_limit * 1000
            ):
                self.invalidate_draw_attempt("画线不连续")
                return

            if self.pending_cursor_delta != (0, 0):
                slider_ratio = (
                    (self.lerp_speed - MIN_LERP_SPEED)
                    / (MAX_LERP_SPEED - MIN_LERP_SPEED)
                )
                mapping_scale = (
                    MOUSE_TRACE_MIN_SCALE
                    + slider_ratio
                    * (MOUSE_TRACE_MAX_SCALE - MOUSE_TRACE_MIN_SCALE)
                )
                cursor_delta = self.pending_cursor_delta
                self.pending_cursor_delta = (0, 0)
                self.current_player.move_dot_by_cursor_delta(
                    cursor_delta, mapping_scale
                )

            if (
                self.current_player.draw_frames
                >= SPEED_WINDOW_FRAMES * 3
            ):
                discontinuity = motion_discontinuity_reason(
                    self.current_player.motion_distances
                )
                if discontinuity:
                    self.invalidate_draw_attempt("画线不连续")
                    return

            reversal = self.current_player.detect_reversal(
                self.current_player.get_draw_rules().max_turns
            )
            if reversal == "turn":
                self.current_player.confirm_turn()
                self.audio.play("turn")
            elif reversal == "second_turn":
                self.mouse_held = False
                self.end_draw_phase(forced_stop=True)

    def run(self):
        running = True
        while running:
            running = self.input_handler.handle_events(self)
            self.update()
            self.renderer.draw(self)
            self.renderer.clock.tick(FPS)
        pygame.quit()
        sys.exit()


def main():
    pygame.init()
    Game().run()
