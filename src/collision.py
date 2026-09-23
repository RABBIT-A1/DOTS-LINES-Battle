# -*- coding: utf-8 -*-
"""线段与路径碰撞检测。"""

from .config import COLLISION_RADIUS
from .geometry import vec_add, vec_dot, vec_len, vec_mul, vec_sub


def dist_point_to_segment(p, a, b):
    ab = vec_sub(b, a)
    ap = vec_sub(p, a)
    ab_len_sq = vec_dot(ab, ab)
    if ab_len_sq < 0.0001:
        return vec_len(ap), a
    t = max(0, min(1, vec_dot(ap, ab) / ab_len_sq))
    closest = vec_add(a, vec_mul(ab, t))
    return vec_len(vec_sub(p, closest)), closest


def path_hits_point(path_points, target_dot):
    """判断路径中的任一线段是否穿过目标点。"""
    for i in range(len(path_points) - 1):
        distance, _ = dist_point_to_segment(
            target_dot, path_points[i], path_points[i + 1]
        )
        if distance < COLLISION_RADIUS:
            return True, target_dot
    return False, None
