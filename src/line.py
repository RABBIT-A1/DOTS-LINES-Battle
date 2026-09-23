# -*- coding: utf-8 -*-
"""画线轨迹的方向检测、简化和质量判定。"""

import math

from .config import (
    CURSOR_PAUSE_SECONDS,
    CURSOR_REFERENCE_STEP,
    DIR_SAMPLE_DIST,
    MAX_DRAW_SECONDS,
    MAX_IDLE_FRAMES,
    MAX_IDLE_RATIO,
    MAX_LARGE_TURNS,
    MAX_ADAPTIVE_PAUSE_SECONDS,
    MIN_ACTIVE_RATIO,
    MIN_ADAPTIVE_PAUSE_SECONDS,
    MIN_AVERAGE_DRAW_SPEED,
    MIN_FRAME_STEP,
    MIN_SLOWDOWN_FRAMES,
    SLOWDOWN_RATIO,
    SPEED_WINDOW_FRAMES,
    TRAIL_SIMPLIFY_DISTANCE,
)
from .geometry import clamp, vec_len, vec_normalize, vec_sub


def simplify_trail(trail, min_dist=3.0):
    if len(trail) < 2:
        return trail
    result = [trail[0]]
    for point in trail[1:]:
        if vec_len(vec_sub(point, result[-1])) >= min_dist:
            result.append(point)
    if result[-1] != trail[-1]:
        result.append(trail[-1])
    return result


def _signed_angle_delta(a, b):
    """返回两个航向角之间的最小绝对夹角（0~180°）。"""
    delta = (b - a + math.pi) % (2 * math.pi) - math.pi
    return abs(math.degrees(delta))


def adaptive_pause_seconds(motion_distances):
    """根据最近鼠标速度调整停顿阈值，快速时略放宽，慢速时略收紧。"""
    active = [distance for distance in (motion_distances or [])
              if distance >= MIN_FRAME_STEP]
    if not active:
        return CURSOR_PAUSE_SECONDS
    recent = active[-8:]
    ordered = sorted(recent)
    median_step = ordered[len(ordered) // 2]
    speed_ratio = clamp(
        median_step / CURSOR_REFERENCE_STEP, 0.5, 2.0
    )
    threshold = CURSOR_PAUSE_SECONDS * (0.85 + 0.15 * speed_ratio)
    return clamp(
        threshold,
        MIN_ADAPTIVE_PAUSE_SECONDS,
        MAX_ADAPTIVE_PAUSE_SECONDS,
    )


def motion_discontinuity_reason(motion_distances):
    """返回实时运动是否断续；停顿和明显减速统一返回“画线不连续”。"""
    if not motion_distances:
        return None

    idle_count = sum(
        distance < MIN_FRAME_STEP for distance in motion_distances
    )
    idle_ratio = idle_count / len(motion_distances)
    max_idle_run = 0
    idle_run = 0
    for distance in motion_distances:
        if distance < MIN_FRAME_STEP:
            idle_run += 1
            max_idle_run = max(max_idle_run, idle_run)
        else:
            idle_run = 0
    if idle_ratio > MAX_IDLE_RATIO or max_idle_run > MAX_IDLE_FRAMES:
        return "画线不连续"

    speeds = list(motion_distances)
    active_speeds = [
        speed for speed in speeds if speed >= MIN_FRAME_STEP
    ]
    if len(active_speeds) >= SPEED_WINDOW_FRAMES * 2:
        ordered = sorted(active_speeds)
        median_speed = ordered[len(ordered) // 2]
        slowdown_limit = max(
            MIN_FRAME_STEP * 2, median_speed * SLOWDOWN_RATIO
        )
        slow_run = 0
        for index in range(SPEED_WINDOW_FRAMES, len(speeds)):
            window = speeds[index - SPEED_WINDOW_FRAMES:index]
            window_average = sum(window) / SPEED_WINDOW_FRAMES
            if (index > SPEED_WINDOW_FRAMES * 2
                    and window_average < slowdown_limit):
                slow_run += 1
                if slow_run >= MIN_SLOWDOWN_FRAMES:
                    return "画线不连续"
            else:
                slow_run = 0
    return None


def check_trail_quality(
    trail,
    motion_distances=None,
    draw_frames=None,
    max_turns=MAX_LARGE_TURNS,
    min_average_speed=MIN_AVERAGE_DRAW_SPEED,
    max_draw_seconds=MAX_DRAW_SECONDS,
    check_turns=True,
):
    """检查玩家是否快速、连续地画出一条至多一次掉头的轨迹。

    先按距离抽样，消除 Pygame 每帧采样造成的微小抖动；再检查停顿比例和
    航向变化。掉头本身允许一次，但掉头之外的额外折返不能累计过多。
    """
    del max_turns, check_turns  # 保留扩展参数；实时方向检测负责转向停止。

    if len(trail) < 2:
        return False, "未开始移动"

    simplified = simplify_trail(
        trail, min_dist=TRAIL_SIMPLIFY_DISTANCE
    )
    if len(simplified) < 2:
        return False, "没有有效移动"

    distances = [
        vec_len(vec_sub(b, a)) for a, b in zip(trail, trail[1:])
    ]
    total_distance = sum(
        vec_len(vec_sub(b, a))
        for a, b in zip(simplified, simplified[1:])
    )

    if motion_distances is None:
        motion_distances = distances
    discontinuity = motion_discontinuity_reason(motion_distances)
    if discontinuity:
        return False, discontinuity

    headings = []
    for a, b in zip(simplified, simplified[1:]):
        delta = vec_sub(b, a)
        if vec_len(delta) >= 0.1:
            headings.append(math.atan2(delta[1], delta[0]))
    if len(headings) < 2:
        return True, "连续移动"

    turn_degrees = [
        _signed_angle_delta(a, b)
        for a, b in zip(headings, headings[1:])
    ]

    active_ratio = 1.0 - (
        sum(
            distance < MIN_FRAME_STEP
            for distance in (motion_distances or distances)
        ) / max(len(motion_distances or distances), 1)
    )
    if active_ratio < MIN_ACTIVE_RATIO:
        return False, "画线不连续"

    if draw_frames and draw_frames > 0:
        from .config import FPS

        duration = draw_frames / FPS
        average_speed = total_distance / duration
        if duration > max_draw_seconds:
            return False, f"画线时间过长（>{max_draw_seconds:.0f}秒）"
        if average_speed < min_average_speed:
            return False, "画线不连续"

    large_turns = sum(1 for turn in turn_degrees if turn >= 125.0)
    minor_turn = sum(turn for turn in turn_degrees if turn < 125.0)
    del minor_turn

    return True, f"连续移动，明显掉头{large_turns}次"


def get_direction_at_end(trail, sample_dist=DIR_SAMPLE_DIST):
    """取轨迹末端的方向向量（从 sample_dist 距离处指向末端）。"""
    if len(trail) < 2:
        return None
    end = trail[-1]
    for i in range(len(trail) - 2, -1, -1):
        distance = vec_len(vec_sub(end, trail[i]))
        if distance >= sample_dist:
            return vec_normalize(vec_sub(end, trail[i]))
    return vec_normalize(vec_sub(end, trail[0]))


def is_reversal(reference_direction, trail):
    """判断轨迹末端方向是否与参考方向形成明显掉头。"""
    if reference_direction is None or len(trail) < 10:
        return False
    current_direction = get_direction_at_end(trail)
    if current_direction is None:
        return False
    from .geometry import vec_dot

    return vec_dot(reference_direction, current_direction) < REVERSAL_COS

