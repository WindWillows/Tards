"""程序生成卡牌视觉系统。

所有卡牌面、缩略图均由 pygame 实时绘制，不依赖外部美术资源。
支持 CardDefinition 和游戏内 Card 对象（MinionCard / Strategy 等）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pygame

from tards.data.card_db import CardDefinition, CardType, Pack, Rarity
from tards.core.cost import Cost
from pygame_client.fonts import get_font_manager


# ===== 颜色常量 =====

_PACK_BG_COLORS = {
    Pack.GENERAL:    (69, 90, 100),
    Pack.PLANT:      (46, 125, 50),
    Pack.MIRACLE:    (245, 176, 0),
    Pack.DISCRETE:   (25, 118, 210),
    Pack.UNDERWORLD: (123, 31, 162),
    Pack.BLOOD:      (211, 47, 47),
}

_PACK_DARK_COLORS = {
    Pack.GENERAL:    (45, 60, 67),
    Pack.PLANT:      (27, 75, 27),
    Pack.MIRACLE:    (150, 110, 0),
    Pack.DISCRETE:   (15, 70, 130),
    Pack.UNDERWORLD: (75, 20, 95),
    Pack.BLOOD:      (130, 30, 30),
}

_RARITY_BORDER = {
    Rarity.IRON:   (176, 190, 197),
    Rarity.BRONZE: (205, 140, 100),
    Rarity.SILVER: (220, 220, 220),
    Rarity.GOLD:   (255, 215, 0),
}

_COST_BALL_COLORS = {
    "T":  (255, 235, 59),
    "C":  (66, 165, 245),
    "B":  (239, 83, 80),
    "S":  (171, 71, 188),
    "I":  (189, 189, 189),
    "G":  (255, 202, 40),
    "D":  (77, 208, 225),
    "M":  (121, 85, 72),
    "CT": (156, 204, 101),
}

_TYPE_LABELS = {
    CardType.MINION:     "异象",
    CardType.STRATEGY:   "策略",
    CardType.CONSPIRACY: "阴谋",
    CardType.MINERAL:    "矿物",
}


# ===== 缓存 =====
_card_cache: Dict[Tuple[str, int, int, str], pygame.Surface] = {}
_thumb_cache: Dict[Tuple[str, int, str], pygame.Surface] = {}


def _extract_pack(card_or_def: Any) -> Pack:
    p = getattr(card_or_def, "pack", None)
    if p is None and hasattr(card_or_def, "source_card"):
        p = getattr(card_or_def.source_card, "pack", None)
    return p if p is not None else Pack.GENERAL


def _extract_rarity(card_or_def: Any) -> Rarity:
    r = getattr(card_or_def, "rarity", None)
    if r is None and hasattr(card_or_def, "source_card"):
        r = getattr(card_or_def.source_card, "rarity", None)
    return r if r is not None else Rarity.IRON


def _extract_type(card_or_def: Any) -> CardType:
    t = getattr(card_or_def, "card_type", None)
    if t is None:
        from tards.cards import MinionCard, Strategy, Conspiracy, MineralCard
        if isinstance(card_or_def, MinionCard):
            t = CardType.MINION
        elif isinstance(card_or_def, Strategy):
            t = CardType.STRATEGY
        elif isinstance(card_or_def, Conspiracy):
            t = CardType.CONSPIRACY
        elif isinstance(card_or_def, MineralCard):
            t = CardType.MINERAL
    return t if t is not None else CardType.MINION


def _extract_cost_items(cost: Cost) -> list:
    items = []
    if cost.t > 0:
        items.append(("T", cost.t))
    if cost.c > 0:
        items.append(("C", cost.c))
    if cost.b > 0:
        items.append(("B", cost.b))
    if cost.s > 0:
        items.append(("S", cost.s))
    for mtype, count in sorted(cost.minerals.items()):
        items.append((mtype, count))
    if cost.ct > 0:
        items.append(("CT", cost.ct))
    return items


def render_card_surface(card_or_def: Any, width: int = 200, height: int = 280) -> pygame.Surface:
    """程序生成标准卡牌 Surface（默认 200×280）。带缓存。"""
    name = getattr(card_or_def, "name", "?")
    cost_str = str(getattr(card_or_def, "cost", "0"))
    cache_key = (name, width, height, cost_str)
    if cache_key in _card_cache:
        return _card_cache[cache_key]

    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    fm = get_font_manager()
    pack = _extract_pack(card_or_def)
    rarity = _extract_rarity(card_or_def)
    card_type = _extract_type(card_or_def)

    # 1. 外边框（稀有度色）
    border_color = _RARITY_BORDER.get(rarity, _RARITY_BORDER[Rarity.IRON])
    _draw_rounded_rect(surf, 0, 0, width, height, 10, border_color)

    # 2. 内背景（卡包色）
    bg = _PACK_BG_COLORS.get(pack, _PACK_BG_COLORS[Pack.GENERAL])
    _draw_rounded_rect(surf, 2, 2, width - 4, height - 4, 8, bg)

    # 3. 顶部深色装饰条
    top_bar = _PACK_DARK_COLORS.get(pack, (0, 0, 0))
    pygame.draw.rect(surf, top_bar, (4, 4, width - 8, 28), border_radius=4)

    # 4. 费用球
    cost = getattr(card_or_def, "cost", None)
    if cost:
        items = _extract_cost_items(cost)
        ball_r = min(10, int((width - 16) / max(len(items), 1) / 2) - 2)
        x_off = 6
        for sym, val in items:
            cx = x_off + ball_r
            cy = 18
            color = _COST_BALL_COLORS.get(sym, (200, 200, 200))
            pygame.draw.circle(surf, color, (cx, cy), ball_r)
            pygame.draw.circle(surf, (255, 255, 255), (cx, cy), ball_r, 1)
            vtxt = fm.render_text(str(val), max(8, ball_r), (0, 0, 0), bold=True)
            surf.blit(vtxt, (cx - vtxt.get_width() // 2, cy - vtxt.get_height() // 2))
            x_off += ball_r * 2 + 4

    # 5. 卡名（中央）
    display_name = name[:4] + "…" if len(name) > 4 else name
    name_size = max(16, int(width * 0.13))
    ntxt = fm.render_text(display_name, name_size, (255, 255, 255), bold=True)
    shadow = fm.render_text(display_name, name_size, (0, 0, 0), bold=True)
    nx = width // 2 - ntxt.get_width() // 2
    ny = height // 2 - 25
    surf.blit(shadow, (nx + 1, ny + 1))
    surf.blit(ntxt, (nx, ny))

    # 6. 类型标签
    tlabel = _TYPE_LABELS.get(card_type, "卡")
    tsize = max(12, int(width * 0.09))
    ttxt = fm.render_text(tlabel, tsize, (255, 255, 255))
    surf.blit(ttxt, (width // 2 - ttxt.get_width() // 2, height // 2 + 2))

    # 7. 底部信息
    if card_type == CardType.MINION:
        atk = getattr(card_or_def, "attack", None)
        hp = getattr(card_or_def, "health", None)
        if atk is not None and hp is not None:
            # 攻击（左下，红色盾）
            _draw_shield(surf, 8, height - 32, 34, 22, (211, 47, 47))
            atxt = fm.render_text(str(atk), max(14, int(width * 0.11)), (255, 255, 255), bold=True)
            surf.blit(atxt, (25 - atxt.get_width() // 2, height - 29))

            # 生命（右下，绿色盾）
            _draw_shield(surf, width - 42, height - 32, 34, 22, (46, 125, 50))
            htxt = fm.render_text(str(hp), max(14, int(width * 0.11)), (255, 255, 255), bold=True)
            surf.blit(htxt, (width - 25 - htxt.get_width() // 2, height - 29))
    else:
        big = f"【{tlabel}】"
        btxt = fm.render_text(big, max(14, int(width * 0.12)), (255, 255, 255, 180))
        surf.blit(btxt, (width // 2 - btxt.get_width() // 2, height - 32))

    _card_cache[cache_key] = surf
    return surf


def render_thumbnail(card_or_def: Any, size: int = 64) -> pygame.Surface:
    """生成缩略图（简化版卡牌，正方形）。带缓存。"""
    name = getattr(card_or_def, "name", "?")
    cost_str = str(getattr(card_or_def, "cost", "0"))
    cache_key = (name, size, cost_str)
    if cache_key in _thumb_cache:
        return _thumb_cache[cache_key]

    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pack = _extract_pack(card_or_def)
    bg = _PACK_BG_COLORS.get(pack, _PACK_BG_COLORS[Pack.GENERAL])
    _draw_rounded_rect(surf, 0, 0, size, size, 4, bg)

    fm = get_font_manager()
    first = name[0] if name else "?"
    txt = fm.render_text(first, max(14, size // 2), (255, 255, 255), bold=True)
    surf.blit(txt, (size // 2 - txt.get_width() // 2, size // 2 - txt.get_height() // 2))

    _thumb_cache[cache_key] = surf
    return surf


def _draw_rounded_rect(surf: pygame.Surface, x: int, y: int, w: int, h: int,
                       radius: int, color):
    """绘制填充圆角矩形（pygame 2.0+）。"""
    pygame.draw.rect(surf, color, (x, y, w, h), border_radius=radius)


def _draw_shield(surf: pygame.Surface, x: int, y: int, w: int, h: int, color):
    """绘制简化盾牌（圆角矩形 + 白边）。"""
    pygame.draw.rect(surf, color, (x, y, w, h), border_radius=h // 2)
    pygame.draw.rect(surf, (255, 255, 255), (x, y, w, h), 1, border_radius=h // 2)
