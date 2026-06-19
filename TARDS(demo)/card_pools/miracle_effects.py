"""奇迹卡包效果函数库。

所有奇迹卡包的 special_fn / effect_fn 集中于此，供 miracle.py 注册表引用。
"""

import random
from typing import Any, List, Optional, Tuple

from card_pools.effect_decorator import special
from card_pools.effect_utils import (
    add_deathrattle,
    buff_minion,
    create_echo_card,
    deal_damage_to_minion,
    destroy_minion,
)


# =============================================================================
# 汞雾
# =============================================================================

def _gongwu_draw_trigger(player, game, card):
    """汞雾抽取：抽牌玩家与其对手各失去2点HP，抽牌玩家先结算。"""
    opponent = game.p2 if player == game.p1 else game.p1
    player.health_change(-2)
    print(f"  汞雾抽取：{player.name} 失去2点HP")
    opponent.health_change(-2)
    print(f"  汞雾抽取：{opponent.name} 失去2点HP")


@special
def _gongwu_special(minion, player, game, extras=None):
    """汞雾部署：随机将一个距离本异象最近的异象的回响加入手牌。"""
    if not minion.is_alive():
        return
    if minion.position is None:
        print("  汞雾部署：本异象没有位置信息，无法计算距离")
        return

    others = [
        m for m in game.board.minion_place.values()
        if m is not minion and m.is_alive()
    ]
    if not others:
        print("  汞雾部署：场上没有其他异象")
        return

    r, c = minion.position
    min_dist = min(abs(m.position[0] - r) + abs(m.position[1] - c) for m in others)
    nearest = [m for m in others if abs(m.position[0] - r) + abs(m.position[1] - c) == min_dist]
    target_minion = random.choice(nearest)

    source_card = getattr(target_minion, "source_card", None)
    if source_card is None:
        print(f"  汞雾部署：{target_minion.name} 没有源卡，无法生成回响")
        return

    echo = create_echo_card(source_card, echo_level=1)
    echo.owner = player
    player.add_card_to_hand(echo, game=game, emit_events=False)
    print(f"  汞雾部署：将 {target_minion.name} 的回响加入 {player.name} 手牌")
