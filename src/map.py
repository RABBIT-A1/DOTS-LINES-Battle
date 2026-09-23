# -*- coding: utf-8 -*-
"""竞技场边界、出生区域与路径回退规则。"""

from .config import ARENA_H, ARENA_W, ARENA_X, ARENA_Y, MARGIN


def arena_bounds():
    min_x = ARENA_X + MARGIN
    max_x = ARENA_X + ARENA_W - MARGIN
    min_y = ARENA_Y + MARGIN
    max_y = ARENA_Y + ARENA_H - MARGIN
    return min_x, max_x, min_y, max_y


def clamp_point_to_arena(px, py):
    min_x, max_x, min_y, max_y = arena_bounds()
    return (
        max(min_x, min(max_x, px)),
        max(min_y, min(max_y, py)),
    )


def is_in_arena(px, py):
    min_x, max_x, min_y, max_y = arena_bounds()
    return min_x <= px <= max_x and min_y <= py <= max_y


def point_in_spawn(point, spawn_rect):
    """判断点是否位于出生框内。"""
    x, y = point
    sx, sy, sw, sh = spawn_rect
    return sx <= x <= sx + sw and sy <= y <= sy + sh


def path_leaves_spawn(player, path_points):
    """检查出击轨迹是否离开出生点；出生点允许之后重新进入。"""
    if not path_points:
        return False
    has_left = player.has_left_spawn
    for point in path_points:
        if not point_in_spawn(point, player.spawn_rect):
            has_left = True
    return has_left


def retract_to_boundary(path_points):
    if len(path_points) < 2:
        return path_points
    end = path_points[-1]
    if is_in_arena(end[0], end[1]):
        return path_points
    for i in range(len(path_points) - 1, 0, -1):
        a = path_points[i - 1]
        b = path_points[i]
        if is_in_arena(a[0], a[1]):
            low, high = 0.0, 1.0
            for _ in range(32):
                middle = (low + high) / 2
                mx = a[0] + (b[0] - a[0]) * middle
                my = a[1] + (b[1] - a[1]) * middle
                if is_in_arena(mx, my):
                    low = middle
                else:
                    high = middle
            safe_point = clamp_point_to_arena(
                a[0] + (b[0] - a[0]) * low,
                a[1] + (b[1] - a[1]) * low,
            )
            return list(path_points[:i]) + [safe_point]
    return [path_points[0]]

