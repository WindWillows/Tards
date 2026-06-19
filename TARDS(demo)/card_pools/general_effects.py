"""通用卡包效果函数库。

所有通用卡包的 special_fn / effect_fn 集中于此，供 general.py 注册表引用。
"""

import random
from typing import Any, List, Optional

from card_pools.effect_decorator import special
from card_pools.effect_utils import (
    add_deathrattle,
    buff_minion,
    convert_cost_to_t,
    deal_damage_to_minion,
    destroy_minion,
    on,
)


# =============================================================================
# 精灵系列 special
# =============================================================================

@special
def _huoling_special(minion, player, game, extras=None):
    """火灵：亡语：对伤害来源造成2点伤害。"""
    def _dr(m, p, b):
        source = getattr(m, "_last_damage_source", None)
        if source and source.is_alive():
            g = b.game_ref
            deal_damage_to_minion(source, 2, source=m, game=g)
        else:
            print(f"  {m.name} 亡语触发，但找不到有效的伤害来源")
    add_deathrattle(minion, _dr)


@special
def _shikongling_special(minion, player, game, extras=None):
    """时空灵：亡语：抽1张牌。"""
    def _dr(m, p, b):
        g = b.game_ref
        p.draw_card(1, game=g)
    add_deathrattle(minion, _dr)


@special
def _dianling_special(minion, player, game, extras=None):
    """电灵：亡语：随机眩晕一个敌方异象。"""
    def _dr(m, p, b):
        enemies = [e for e in b.minion_place.values() if e.owner != p and e.is_alive()]
        if enemies:
            target_minion = random.choice(enemies)
            target_minion.base_keywords["眩晕"] = 1
            target_minion.recalculate()
            print(f"  {target_minion.name} 被眩晕1回合")
        else:
            print(f"  {m.name} 亡语触发，但场上没有敌方异象")
    add_deathrattle(minion, _dr)


@special
def _xueling_special(minion, player, game, extras=None):
    """血灵：亡语：你获得+2HP。"""
    def _dr(m, p, b):
        p.health_change(2)
    add_deathrattle(minion, _dr)


@special
def _shuiling_special(minion, player, game, extras=None):
    """水灵：亡语：下一个出牌阶段开始时，获得1T。"""
    def _dr(m, p, b):
        g = b.game_ref
        if not g:
            return
        lid = [None]
        def _callback(event):
            if event.data.get("phase") == g.PHASE_ACTION:
                p.t_point_change(1)
                print(f"  {p.name} 水灵亡语触发，获得1T")
                if lid[0] is not None:
                    g.history.unlisten(lid[0])
        lid[0] = on("phase_start", _callback, g)
    add_deathrattle(minion, _dr)


@special
def _fengling_special(minion, player, game, extras=None):
    """风灵：亡语：使一个随机敌方异象获得-1攻击力。"""
    def _dr(m, p, b):
        enemies = [e for e in b.minion_place.values() if e.owner != p and e.is_alive()]
        if enemies:
            target_minion = random.choice(enemies)
            buff_minion(target_minion, atk_delta=-1)
            print(f"  {target_minion.name} 被风灵亡语减1攻击力")
        else:
            print(f"  {m.name} 亡语触发，但场上没有敌方异象")
    add_deathrattle(minion, _dr)


# =============================================================================
# 策略卡效果函数
# =============================================================================

def _xuanwo_effect(player, target, game, extras=None):
    """漩涡：抽2张牌。"""
    player.draw_card(2, game=game)
    print(f"  漩涡：{player.name} 抽2张牌")
    return True


def _genchu_effect(player, target, game, extras=None):
    """根除：消灭一个异象。"""
    if target and hasattr(target, "is_alive") and target.is_alive():
        destroy_minion(target, game)
        return True
    print("  根除：未选择有效目标")
    return False


def _lingdong_effect(player, target, game, extras=None):
    """灵动：1T 将双方抽牌堆中所有折算花费最小的牌移动到各自的抽牌堆顶。"""
    opponent = game.p2 if player == game.p1 else game.p1
    for p in (player, opponent):
        if not p.card_deck:
            print(f"  灵动：{p.name} 的牌库为空")
            continue
        indexed = [(convert_cost_to_t(c.cost), i, c) for i, c in enumerate(p.card_deck)]
        min_cost = min(t[0] for t in indexed)
        selected = [c for cost, i, c in indexed if cost == min_cost]
        remaining = [c for cost, i, c in indexed if cost != min_cost]
        p.card_deck = remaining + selected
        print(f"  灵动：{p.name} 将 {len(selected)} 张折算花费最小的牌移到牌库顶")
    return True


def _wumei_effect(player, target, game, extras=None):
    """污煤：1T 获得1个T槽，抽1张牌。你失去2个T槽自然上限。"""
    # 卡面顺序：获得T槽 -> 抽牌 -> 失去自然上限
    player.t_point_max_change(1)
    player.draw_card(1, game=game)
    player._natural_t_max_cap_modifier -= 2
    print(f"  污煤：{player.name} 获得1个T槽，抽1张牌，T槽自然上限-2")
    return True


def _bumei_effect(player, target, game, extras=None):
    """不寐：抉择：消灭一个沉浸度为3的异象，或对手随机弃一张沉浸度为3的手牌。"""
    from tards.core.targeting import TargetingRequest
    from tards.data.card_db import DEFAULT_REGISTRY

    opponent = game.p2 if player == game.p1 else game.p1

    def _immersion_level(card_or_minion) -> int:
        name = getattr(card_or_minion, "name", None)
        if not name:
            return 0
        defn = DEFAULT_REGISTRY.get(name)
        return getattr(defn, "immersion_level", 0) if defn else 0

    # 抉择选项始终向玩家展示，不因当前无合法目标而隐藏，避免泄露信息。
    options = ["消灭一个沉浸度为3的异象", "对手随机弃一张沉浸度为3的手牌"]
    choice = game.request_choice(player, options, title="不寐")
    if choice is None:
        return False

    if choice == "消灭一个沉浸度为3的异象":
        alive_targets = [
            m for m in game.board.minion_place.values()
            if m.is_alive() and _immersion_level(m) == 3
        ]
        if not alive_targets:
            print("  不寐：场上没有沉浸度为3的异象，该分支无法执行")
            return True

        def scope(p, board):
            return [m for m in alive_targets if m.is_alive()]

        req = TargetingRequest(
            source=player,
            scope_fn=scope,
            prompt="不寐：选择一个沉浸度为3的异象消灭",
            deciding_player=player,
        )
        chosen = game.targeting_system.request_target(req)
        if chosen is None or not getattr(chosen, "is_alive", lambda: False)():
            print("  不寐：未选择有效目标")
            return True
        destroy_minion(chosen, game)
        print(f"  不寐：消灭 {chosen.name}")
        return True
    else:
        valid_hand = [c for c in opponent.card_hand if _immersion_level(c) == 3]
        if not valid_hand:
            print("  不寐：对手手中没有沉浸度为3的牌，该分支无法执行")
            return True
        card = random.choice(valid_hand)
        opponent.discard_card(card, game=game, reason="effect")
        print(f"  不寐：对手弃置 {card.name}")
        return True


# =============================================================================
# 其他 special
# =============================================================================

@special
def _jingxiliwu_special(minion, player, game, extras=None):
    """惊喜礼物：亡语：你抽1张牌，对手抽2张牌。"""
    def _dr(m, p, b):
        g = b.game_ref
        opponent = g.p2 if p == g.p1 else g.p1
        p.draw_card(1, game=g)
        print(f"  惊喜礼物：{p.name} 抽1张牌")
        opponent.draw_card(2, game=g)
        print(f"  惊喜礼物：{opponent.name} 抽2张牌")
    add_deathrattle(minion, _dr)
