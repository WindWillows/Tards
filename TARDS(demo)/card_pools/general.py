# 通用卡包注册表

from tards import register_card, CardType, Pack, Rarity
from tards.core.targets import target, target_none

from card_pools.general_effects import (
    _huoling_special,
    _shikongling_special,
    _dianling_special,
    _xueling_special,
    _shuiling_special,
    _fengling_special,
    _jingxiliwu_special,
    _xuanwo_effect,
    _genchu_effect,
    _lingdong_effect,
    _wumei_effect,
    _bumei_effect,
)


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

register_card(
    name="漩涡",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.GENERAL,
    rarity=Rarity.IRON,
    immersion_level=0,
    description="抽2张牌。",
    targets_fn=target_none,
    effect_fn=_xuanwo_effect,
)

register_card(
    name="根除",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.GENERAL,
    rarity=Rarity.SILVER,
    immersion_level=0,
    description="消灭一个异象。",
    targets_fn=target("minion"),
    effect_fn=_genchu_effect,
)

register_card(
    name="灵动",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.GENERAL,
    rarity=Rarity.SILVER,
    immersion_level=0,
    description="将双方抽牌堆中所有折算花费最小的牌移动到各自的抽牌堆顶。",
    targets_fn=target_none,
    effect_fn=_lingdong_effect,
)

register_card(
    name="污煤",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.GENERAL,
    rarity=Rarity.GOLD,
    immersion_level=0,
    description="获得1个T槽，抽1张牌。你失去2个T槽自然上限。",
    targets_fn=target_none,
    effect_fn=_wumei_effect,
)

register_card(
    name="不寐",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.GENERAL,
    rarity=Rarity.SILVER,
    immersion_level=0,
    description="抉择：消灭一个沉浸度为3的异象；或对手随机弃一张沉浸度为3的手牌。",
    targets_fn=target_none,
    effect_fn=_bumei_effect,
)

register_card(
    name="惊喜礼物",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.GENERAL,
    rarity=Rarity.BRONZE,
    attack=4,
    health=4,
    keywords={"亡语": True},
    tags=[],
    hidden_keywords={},
    description="亡语：你抽1张牌，对手抽2张牌。",
    targets_fn=target("position", friendly=True),
    special_fn=_jingxiliwu_special,
)
