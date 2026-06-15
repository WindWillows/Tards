"""纯 UI 渲染工具函数。

原位于 Gamestart.py::BattleFrame 与 gui/battle/input_controller.py::InputController，
提取为模块级函数以减少重复。
"""

from typing import Any, Optional

import tkinter as tk

try:
    from PIL import Image, ImageDraw, ImageTk
    _PIL_AVAILABLE = True
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageTk = None  # type: ignore
    _PIL_AVAILABLE = False

from gui.theme import UI_THEME


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def interpolate_color(c1: str, c2: str, t: float) -> str:
    """在两种十六进制颜色之间线性插值，t ∈ [0, 1]。"""
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return rgb_to_hex((
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    ))


def rounded_rect(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int,
                 radius: int, **kwargs: Any) -> int:
    """在 Canvas 上绘制圆角多边形（smooth=True 实现圆角）。"""
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)


def calc_tab_width(cost_str: str, base: int = 28, char_px: int = 6, padding: int = 10) -> int:
    """根据费用字符串长度计算左上角标签宽度。"""
    return max(base, len(cost_str) * char_px + padding)


def get_minion_attack_color(m) -> str:
    """返回 1 号攻击三角区域背景色。"""
    if m.current_attack > m.base_attack:
        return UI_THEME["minion_atk_boost"]
    if m.current_attack < m.base_attack:
        return UI_THEME["minion_atk_low"]
    return UI_THEME["minion_atk_eq"]


def get_minion_hp_color(m) -> str:
    """返回 2 号 HP 三角区域背景色。"""
    if m.current_health < m.current_max_health:
        return UI_THEME["minion_hp_injured"]
    if m.current_max_health > m.base_max_health:
        return UI_THEME["minion_hp_boost"]
    return UI_THEME["minion_hp_eq"]


def create_gradient_photo(width: int, height: int, color1: str, color2: str, radius: int = 6):
    """生成圆角斜向渐变 PIL Image，返回 tk.PhotoImage。"""
    if not _PIL_AVAILABLE or width <= 0 or height <= 0:
        return None

    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)

    grad = Image.new("RGB", (width, height))
    pixels = grad.load()
    max_sum = width + height - 2
    for y in range(height):
        for x in range(width):
            t = (x + y) / max_sum if max_sum > 0 else 0
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            pixels[x, y] = (r, g, b)

    mask = Image.new("L", (width, height), 255)
    r_band, g_band, b_band = grad.split()
    img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
    return ImageTk.PhotoImage(img)


def create_tab_gradient_photo(width: int, height: int, color1: str, color2: str,
                              tab_w: int = 28, tab_h: int = 16, slant: int = 5, radius: int = 2):
    """生成带左上角标签的圆角斜向渐变 PIL Image，返回 tk.PhotoImage。"""
    if not _PIL_AVAILABLE or width <= 0 or height <= 0:
        return None

    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)

    grad = Image.new("RGB", (width, height))
    pixels = grad.load()
    max_sum = width + height - 2
    for y in range(height):
        for x in range(width):
            t = (x + y) / max_sum if max_sum > 0 else 0
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            pixels[x, y] = (r, g, b)

    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    x1, y1 = 0, 0
    x2, y2 = width - 1, height - 1
    body_y1 = y1 + tab_h
    r = radius

    body_points = [
        (x1 + tab_w + slant, body_y1),
        (x2 - r, body_y1),
        (x2, body_y1 + r),
        (x2, y2 - r),
        (x2 - r, y2),
        (x1 + r, y2),
        (x1, y2 - r),
        (x1, body_y1),
    ]
    draw.polygon(body_points, fill=255)

    draw.polygon([
        (x1, y1),
        (x1 + tab_w, y1),
        (x1 + tab_w + slant, body_y1),
        (x1, body_y1),
    ], fill=255)

    r_band, g_band, b_band = grad.split()
    img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
    return ImageTk.PhotoImage(img)


def create_minion_portrait_photo(size: int, color1: str, color2: str,
                                 is_enemy: bool = False, corner_leg: int = 10):
    """生成异象 3 号区域渐变图。敌方在友方视角下左下角裁掉一个小三角。"""
    if not _PIL_AVAILABLE or size <= 0:
        return None

    c1 = hex_to_rgb(color1)
    c2 = hex_to_rgb(color2)

    grad = Image.new("RGB", (size, size))
    pixels = grad.load()
    max_sum = size + size - 2
    for y in range(size):
        for x in range(size):
            t = (x + y) / max_sum if max_sum > 0 else 0
            r = int(c1[0] + (c2[0] - c1[0]) * t)
            g = int(c1[1] + (c2[1] - c1[1]) * t)
            b = int(c1[2] + (c2[2] - c1[2]) * t)
            pixels[x, y] = (r, g, b)

    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    if is_enemy:
        points = [
            (0, 0),
            (size - 1, 0),
            (size - 1, size - 1),
            (corner_leg, size - 1),
            (0, size - 1 - corner_leg),
        ]
    else:
        points = [
            (0, 0),
            (size - 1, 0),
            (size - 1, size - 1),
            (0, size - 1),
        ]
    draw.polygon(points, fill=255)

    r_band, g_band, b_band = grad.split()
    img = Image.merge("RGBA", (r_band, g_band, b_band, mask))
    return ImageTk.PhotoImage(img)
