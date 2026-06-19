# 奇迹卡包注册表

from tards import register_card, CardType, Pack, Rarity
from tards.core.targets import target, target_none

from .miracle_effects import (
    _gongwu_draw_trigger,
    _gongwu_special,
)


# =============================================================================
# 银卡：汞雾
# =============================================================================

register_card(
    name="汞雾",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.MIRACLE,
    rarity=Rarity.SILVER,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"协同": True},
    hidden_keywords={"抽取": _gongwu_draw_trigger},
    description="抽取：你和对手各失去2点HP。\n部署：随机将一个距离最近的异象的回响加入手牌。",
    targets_fn=target("position", friendly=True),
    special_fn=_gongwu_special,
)
