# -*- coding: utf-8 -*-
"""玩家实体：点、路径、回合状态与技能组。"""

from .config import REVERSAL_COS
from .geometry import vec_add, vec_dot, vec_len, vec_mul, vec_normalize, vec_sub
from .line import (
    get_direction_at_end,
    is_reversal,
    simplify_trail,
)
from .map import clamp_point_to_arena, point_in_spawn
from .skill_system import SkillSet


class Player:
    def __init__(self, spawn_rect, color, color_light, name):
        self.spawn_rect = spawn_rect
        self.color = color
        self.color_light = color_light
        self.name = name
        self._init_state()

    def _init_state(self):
        self.dot_pos = None
        self.line_segments = []
        self.all_path_points = []
        self.has_turned = False
        self.turn_point = None
        self.is_launch = True
        self.alive = True
        self.turn_count = 0
        self.skill_set = SkillSet()
        self.trail = []
        self.motion_distances = []
        self.draw_frames = 0
        self.initial_dir = None
        self.post_turn_dir = None
        self.has_left_spawn = False

    def reset_for_new_game(self):
        cx = self.spawn_rect[0] + self.spawn_rect[2] // 2
        cy = self.spawn_rect[1] + self.spawn_rect[3] // 2
        self._init_state()
        self.dot_pos = (cx, cy)
        self.alive = True
        self.is_launch = True

    def begin_turn(self):
        self.has_turned = False
        self.turn_point = None
        self.line_segments = []
        self.trail = []
        self.motion_distances = []
        self.draw_frames = 0
        self.initial_dir = None
        self.post_turn_dir = None
        self.turn_count += 1
        self.skill_set.on_turn_start(self)

    def get_draw_rules(self):
        return self.skill_set.draw_rules(self)

    def move_dot_by_cursor_delta(self, cursor_delta, mapping_scale):
        """按鼠标轨迹增量映射点的位置，不追赶鼠标绝对坐标。"""
        mapped_delta = vec_mul(cursor_delta, mapping_scale)
        start_pos = self.dot_pos
        self.dot_pos = vec_add(self.dot_pos, mapped_delta)
        self.dot_pos = clamp_point_to_arena(
            self.dot_pos[0], self.dot_pos[1]
        )
        if not point_in_spawn(self.dot_pos, self.spawn_rect):
            self.has_left_spawn = True
        if not self.trail:
            self.trail.append(start_pos)
        self.trail.append(self.dot_pos)

        # 连续性检测使用原始鼠标位移，不使用边界 clamp 后的点位移。
        self.motion_distances.append(vec_len(cursor_delta))
        self.draw_frames += 1

        if self.initial_dir is None and len(self.trail) >= 2:
            direction = vec_sub(self.trail[-1], self.trail[0])
            if vec_len(direction) > 5:
                self.initial_dir = vec_normalize(direction)

    def detect_reversal(self, max_turns=1):
        """检测当前轨迹末端方向是否反转。

        返回：'none' / 'turn' / 'second_turn'
        """
        del max_turns
        if self.initial_dir is None or len(self.trail) < 10:
            return "none"

        current_direction = get_direction_at_end(self.trail)
        if current_direction is None:
            return "none"

        if not self.has_turned:
            if vec_dot(self.initial_dir, current_direction) < REVERSAL_COS:
                return "turn"
        else:
            if self.post_turn_dir is not None:
                if vec_dot(self.post_turn_dir, current_direction) < REVERSAL_COS:
                    return "second_turn"
        return "none"

    def confirm_turn(self):
        """确认一次方向反转为转向。"""
        self.has_turned = True
        self.turn_point = self.dot_pos
        self.post_turn_dir = get_direction_at_end(self.trail)

    def confirm_from_trail(self):
        points = simplify_trail(self.trail, min_dist=5.0)
        if len(points) < 2:
            points = (
                [self.trail[0], self.trail[-1]]
                if len(self.trail) >= 2
                else self.trail
            )

        if self.has_turned and self.turn_point:
            turn_index = 0
            min_distance = float("inf")
            for i, point in enumerate(points):
                distance = vec_len(vec_sub(point, self.turn_point))
                if distance < min_distance:
                    min_distance = distance
                    turn_index = i
            segments = [
                points[:turn_index + 1],
                points[turn_index:],
            ]
            self.line_segments = []
            for segment_points in segments:
                if len(segment_points) >= 2:
                    for i in range(len(segment_points) - 1):
                        self.line_segments.append(
                            (segment_points[i], segment_points[i + 1])
                        )
        else:
            self.line_segments = []
            for i in range(len(points) - 1):
                self.line_segments.append((points[i], points[i + 1]))

        self.all_path_points.extend(points)
        return points

    def move_dot_to(self, new_pos):
        self.dot_pos = new_pos

    def reset_draw_attempt(self, start_pos):
        """无效画线回到本回合原点，保留回合本身供玩家重试。"""
        self.dot_pos = start_pos
        self.trail = []
        self.motion_distances = []
        self.draw_frames = 0
        self.line_segments = []
        self.has_turned = False
        self.turn_point = None
        self.initial_dir = None
        self.post_turn_dir = None
        self.has_left_spawn = (
            False if self.is_launch else self.has_left_spawn
        )

    def end_turn(self):
        self.is_launch = False

