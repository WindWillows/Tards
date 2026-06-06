# 通用卡包定义文件

from tards import register_card, CardType, Pack, Rarity
from tards.targets import target
from card_pools.effect_decorator import special
from card_pools.effect_utils import add_deathrattle, deal_damage_to_minion, buff_minion, on
import random


# =============================================================================
# 精灵系列
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
# 注册卡牌
# =============================================================================

register_card(
    name="火灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：对伤害来源造成2点伤害。",
    targets_fn=target("position", friendly=True),
    special_fn=_huoling_special,
)

register_card(
    name="时空灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：抽1张牌。",
    targets_fn=target("position", friendly=True),
    special_fn=_shikongling_special,
)

register_card(
    name="电灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：随机眩晕一个敌方异象。",
    targets_fn=target("position", friendly=True),
    special_fn=_dianling_special,
)

register_card(
    name="血灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：你获得+2HP。",
    targets_fn=target("position", friendly=True),
    special_fn=_xueling_special,
)

register_card(
    name="水灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：下一个出牌阶段开始时，获得1T。",
    targets_fn=target("position", friendly=True),
    special_fn=_shuiling_special,
)

register_card(
    name="风灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=["精灵"],
    hidden_keywords={},
    description="亡语：使一个随机敌方异象获得-1攻击力。",
    targets_fn=target("position", friendly=True),
    special_fn=_fengling_special,
)
