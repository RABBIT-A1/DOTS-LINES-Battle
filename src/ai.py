# -*- coding: utf-8 -*-
"""AI 画线规划。"""

import math
import random

from .map import clamp_point_to_arena


def ai_plan_trail(ai_player, target_pos):
    """AI 规划轨迹：瞄准红点附近的随机位置，再完成一次掉头。

    出击回合完全随机；后续回合在目标附近加入随机偏差，并重新采样
    弧线控制点，避免路线模板化。
    """
    start = ai_player.dot_pos
    dx = target_pos[0] - start[0]
    dy = target_pos[1] - start[1]
    distance = math.sqrt(dx * dx + dy * dy)
    if distance < 1:
        return [start, start], False, None

    if ai_player.is_launch:
        angle_to_target = random.uniform(0.0, math.tau)
        random_distance = random.uniform(180.0, 500.0)
        aim_point = clamp_point_to_arena(
            start[0] + math.cos(angle_to_target) * random_distance,
            start[1] + math.sin(angle_to_target) * random_distance,
        )
    else:
        if random.random() < 0.25:
            aim_point = target_pos
        else:
            deviation_angle = random.uniform(0.0, math.tau)
            deviation_distance = random.uniform(10.0, 32.0)
            aim_point = clamp_point_to_arena(
                target_pos[0]
                + math.cos(deviation_angle) * deviation_distance,
                target_pos[1]
                + math.sin(deviation_angle) * deviation_distance,
            )

    aim_dx = aim_point[0] - start[0]
    aim_dy = aim_point[1] - start[1]
    aim_distance = math.sqrt(aim_dx * aim_dx + aim_dy * aim_dy)
    angle_to_target = math.atan2(aim_dy, aim_dx)

    lateral = random.uniform(-0.35, 0.35) * aim_distance
    control_distance = aim_distance * random.uniform(0.30, 0.75)
    control_angle = angle_to_target + random.uniform(-0.35, 0.35)
    control = (
        start[0]
        + math.cos(control_angle) * control_distance
        - math.sin(angle_to_target) * lateral,
        start[1]
        + math.sin(control_angle) * control_distance
        + math.cos(angle_to_target) * lateral,
    )

    trail = [start]
    step = 1.5
    approach_count = max(16, int(aim_distance / step))
    for i in range(1, approach_count + 1):
        t = i / approach_count
        one_minus_t = 1.0 - t
        point = (
            one_minus_t * one_minus_t * start[0]
            + 2 * one_minus_t * t * control[0]
            + t * t * aim_point[0],
            one_minus_t * one_minus_t * start[1]
            + 2 * one_minus_t * t * control[1]
            + t * t * aim_point[1],
        )
        trail.append(clamp_point_to_arena(*point))

    away_angle = (
        angle_to_target + math.pi + random.uniform(-0.45, 0.45)
    )
    post_distance = max(
        300.0,
        min(550.0, aim_distance * random.uniform(0.45, 0.70)),
    )
    post_count = max(24, int(post_distance / step))
    for i in range(1, post_count + 1):
        progress = i / post_count
        point = (
            aim_point[0]
            + math.cos(away_angle) * post_distance * progress,
            aim_point[1]
            + math.sin(away_angle) * post_distance * progress,
        )
        trail.append(clamp_point_to_arena(*point))

    return trail, True, aim_point
