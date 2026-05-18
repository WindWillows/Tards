"""程序生成棋盘地形与 UI 装饰。

棋盘格子、关键词图标均由 pygame 实时绘制，不依赖外部美术资源。
"""

from __future__ import annotations

import math
import random
from typing import Dict, Tuple

import pygame

from pygame_client.fonts import get_font_manager


# ===== 地形配置 =====
_TERRAINS = {
    "高地": {"bg": (141, 110, 99),   "noise": (120, 90, 80),   "label": "高地"},
    "山脊": {"bg": (120, 144, 156),  "noise": (100, 120, 130), "label": "山脊"},
    "中路": {"bg": (102, 187, 106),  "noise": (80, 160, 90),   "label": "中路"},
    "河岸": {"bg": (215, 204, 200),  "noise": (190, 180, 170), "label": "河岸"},
    "水路": {"bg": (25, 118, 210),   "noise": (50, 140, 220),  "label": "水路"},
}

_TILE_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}
_ICON_CACHE: Dict[Tuple[str, int], pygame.Surface] = {}


def render_board_tile(terrain_name: str, size: int) -> pygame.Surface:
    """生成单个棋盘格子 Surface。带缓存。"""
    cache_key = (terrain_name, size)
    if cache_key in _TILE_CACHE:
        return _TILE_CACHE[cache_key]

    config = _TERRAINS.get(terrain_name, _TERRAINS["中路"])
    surf = pygame.Surface((size, size), pygame.SRCALPHA)

    # 基础色块
    surf.fill(config["bg"])

    # 噪点纹理（确定性随机）
    noise = config["noise"]
    rng = random.Random(hash(cache_key))
    for _ in range(size * 2):
        nx = rng.randint(2, size - 3)
        ny = rng.randint(2, size - 3)
        nr = rng.randint(1, 2)
        alpha = rng.randint(30, 80)
        col = (*noise, alpha)
        pygame.draw.circle(surf, col, (nx, ny), nr)

    # 细线边框
    pygame.draw.rect(surf, (0, 0, 0, 60), (0, 0, size, size), 1)

    # 地形名称水印（底部居中）
    fm = get_font_manager()
    bg = config["bg"]
    label = config["label"]
    ltxt = fm.render_text(label, max(8, size // 6), bg)
    surf.blit(ltxt, (size // 2 - ltxt.get_width() // 2, size - ltxt.get_height() - 4))

    _TILE_CACHE[cache_key] = surf
    return surf


def render_board_background(cell_size: int, cols: int = 5, rows: int = 5) -> pygame.Surface:
    """生成整张棋盘底图（默认 5×5）。"""
    terrain_order = ["高地", "山脊", "中路", "河岸", "水路"]
    total_w = cols * cell_size
    total_h = rows * cell_size
    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

    for r in range(rows):
        for c in range(cols):
            tile = render_board_tile(terrain_order[c], cell_size)
            surf.blit(tile, (c * cell_size, r * cell_size))

    return surf


def render_keyword_icon(keyword: str, size: int = 16) -> pygame.Surface:
    """生成关键词图标 Surface。带缓存。"""
    cache_key = (keyword, size)
    if cache_key in _ICON_CACHE:
        return _ICON_CACHE[cache_key]

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2

    # 颜色映射
    color_map = {
        "冰冻": (0, 188, 212),
        "亡语": (96, 125, 139),
        "恐惧": (156, 39, 176),
        "迅捷": (33, 150, 243),
        "潜水": (3, 169, 244),
        "潜行": (158, 158, 158),
        "成长": (76, 175, 80),
        "视野": (255, 235, 59),
        "高频": (244, 67, 54),
        "连击": (233, 30, 99),
        "多重打击": (233, 30, 99),
        "防空": (0, 150, 136),
        "尖刺": (139, 195, 74),
        "穿刺": (255, 87, 34),
        "串击": (255, 87, 34),
        "穿透": (255, 87, 34),
        "横扫": (255, 152, 0),
        "丰饶": (255, 152, 0),
        "献祭": (121, 85, 72),
        "协同": (33, 150, 243),
        "独行": (255, 152, 0),
        "回响": (255, 193, 7),
        "坚韧": (139, 195, 74),
        "漂浮物": (255, 193, 7),
        "藤蔓": (121, 85, 72),
    }
    color = color_map.get(keyword, (100, 100, 100))

    # 背景圆
    pygame.draw.circle(surf, color, (c, c), c - 1)
    pygame.draw.circle(surf, (255, 255, 255), (c, c), c - 1, 1)

    # 关键词简化符号
    _draw_keyword_symbol(surf, keyword, size)

    _ICON_CACHE[cache_key] = surf
    return surf


def _draw_keyword_symbol(surf: pygame.Surface, keyword: str, size: int):
    """在已绘制的背景圆上绘制关键词简化符号。"""
    c = size // 2
    white = (255, 255, 255)

    if keyword == "冰冻":
        for angle in range(0, 360, 60):
            rad = math.radians(angle)
            x1 = int(c + math.cos(rad) * (c - 3))
            y1 = int(c + math.sin(rad) * (c - 3))
            x2 = int(c + math.cos(rad) * 2)
            y2 = int(c + math.sin(rad) * 2)
            pygame.draw.line(surf, white, (x2, y2), (x1, y1), max(1, size // 12))

    elif keyword == "亡语":
        pygame.draw.circle(surf, white, (c - 2, c - 1), max(1, size // 10))
        pygame.draw.circle(surf, white, (c + 2, c - 1), max(1, size // 10))
        pygame.draw.arc(surf, white, (c - 3, c, 6, 4), 0, math.pi, max(1, size // 12))

    elif keyword == "恐惧":
        for i in range(3):
            pygame.draw.arc(surf, white, (c - 5 + i * 3, c - 3, 4, 6), 0, math.pi, max(1, size // 12))

    elif keyword in ("迅捷", "潜水"):
        pts = [(c, 2), (c - 3, c), (c + 1, c), (c - 2, size - 2), (c + 2, c), (c - 1, c)]
        pygame.draw.polygon(surf, white, pts)

    elif keyword == "成长":
        pts = [(c, 2), (c - 3, c + 2), (c - 1, c + 2), (c - 1, size - 2),
               (c + 1, size - 2), (c + 1, c + 2), (c + 3, c + 2)]
        pygame.draw.polygon(surf, white, pts)

    elif keyword == "视野":
        pygame.draw.ellipse(surf, white, (c - 4, c - 2, 8, 4), max(1, size // 12))
        pygame.draw.circle(surf, white, (c, c), max(1, size // 10))

    elif keyword in ("高频", "连击", "多重打击"):
        for i in range(3):
            pygame.draw.line(surf, white, (2, 4 + i * 3), (size - 2, 4 + i * 3), max(1, size // 12))

    elif keyword == "丰饶":
        pygame.draw.circle(surf, white, (c - 2, c - 1), max(1, size // 8))
        pygame.draw.circle(surf, white, (c + 2, c + 1), max(1, size // 8))

    elif keyword == "献祭":
        pygame.draw.line(surf, white, (c - 2, c + 2), (c + 2, c - 2), max(1, size // 10))
        pygame.draw.line(surf, white, (c - 2, c - 2), (c + 2, c + 2), max(1, size // 10))

    elif keyword == "坚韧":
        pygame.draw.rect(surf, white, (c - 3, c - 3, 6, 6), max(1, size // 10))

    else:
        # 默认：首字
        fm = get_font_manager()
        txt = fm.render_text(keyword[0], max(8, size - 4), white, bold=True)
        surf.blit(txt, (c - txt.get_width() // 2, c - txt.get_height() // 2))
