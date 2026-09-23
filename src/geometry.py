# -*- coding: utf-8 -*-
"""纯几何向量运算。"""

import math


def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def vec_add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def vec_mul(v, s):
    return (v[0] * s, v[1] * s)


def vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def vec_len(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def vec_normalize(v):
    length = vec_len(v)
    if length < 0.0001:
        return (0, 0)
    return (v[0] / length, v[1] / length)


def lerp_pos(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def clamp(value, low, high):
    return max(low, min(high, value))
