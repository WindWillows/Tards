# 自动生成的卡包定义文件
# 由 translate_packs.py 翻译生成

from tards import register_card, CardType, Pack, Rarity, DEFAULT_REGISTRY
from tards.targets import target_friendly_positions, target_none, target_any_minion, target_enemy_minions, target_enemy_player, target_self, target_friendly_minions
from tards.auto_effects import move_enemy_to_friendly, swap_units, return_to_hand
from .underworld_effects import *

# Pack: UNDERWORLD

register_card(
    name="松鼠球",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=9,
    keywords={"协同": True, "献祭": 2, "亡语": True},
    evolve_to="松鼠",
    # 效果描述：受到伤害后，向相邻陆地移动一格，在原地留下一只“松鼠”。 亡语：在原地留下一只“松鼠”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松鼠",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=2,
    tags=['生物', '陆生'],
    is_token=True,
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松鼠罐",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True, "丰饶": 2},
    # 效果描述：回合结束：消灭友方场上的“松鼠”。每消灭一只，献祭等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猫",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    # 效果描述：不会因献祭而被消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="黑山羊",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=4,
    keywords={"协同": True, "绝缘": True, "丰饶": 3, "亡语": True},
    # 效果描述：亡语：若献祭点数溢出，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="13号孩子",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=1,
    keywords={"绝缘": True, "献祭": 13},
    evolve_to="13号",
    # 效果描述：无法被异象选中。献祭后，变为“13号”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="13号",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"空袭": True, "亡语": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：献祭后，转换为“13号孩子”。亡语：消灭伤害来源。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="烛烟",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_zhuyan_special,
)

register_card(
    name="大团烛烟",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "丰饶": 2, "迅捷": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：抽2张牌。
    targets_fn=target_friendly_positions,
    special_fn=_datuanzhuyan_special,
)

register_card(
    name="白鼬",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=6,
    keywords={"协同": True, "迅捷": True},
    # 效果描述：受到战斗伤害后，将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="臭虫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    keywords={"协同": True, "尖刺": 1},
    # 效果描述：与其同列的敌方异象具有-1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=_chouchong_special,
)

register_card(
    name="弱狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "亡语": True},
    # 效果描述：亡语：造成3点伤害，随机分配至敌方主角与伤害来源。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="林鼠",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"丰饶": 2},
    # 效果描述：部署：抽一张指令，或将1只0T的松鼠加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_linshu_special,
)

register_card(
    name="狼",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    # 效果描述：无法选中HP不大于2的异象。回合开始：对一个本列异象造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="灰熊",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：对方部署异象时，失去1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="棕熊",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=4,
    health=5,
    keywords={"先攻": 1},
    # 效果描述：兴奋 对攻击力≤3的异象伤害+2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="陆龟",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=8,
    keywords={"协同": True, "坚韧": 2},
    # 效果描述：处于协同时，受到的战斗伤害翻倍。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="翠鸟",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=1,
    keywords={"两栖": True, "先攻": 1},
    tags=['两栖'],
    # 效果描述：部署：若在水路，获得潜水和空袭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雕",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=5,
    health=4,
    keywords={"两栖": True, "迅捷": True, "先攻": 3},
    tags=['两栖'],
    # 效果描述：首次攻击后，失去先攻Ⅲ，获得-3攻击力和空袭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹰",
    cost_str="2T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"视野": 2, "高频": 3},
    # 效果描述：受到其伤害的目标此前每被本异象指向一次，受到的伤害+1.
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雀",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=1,
    health=2,
    keywords={"协同": True, "两栖": True},
    tags=['两栖'],
    # 效果描述：部署时：将其复制加入战场。回合结束：将其复制加入战场。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹞",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=5,
    health=3,
    keywords={"两栖": True, "迅捷": True},
    tags=['两栖'],
    # 效果描述：受到伤害时，改为失去1点HP。无法获得HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸥",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=4,
    keywords={"水生": True, "潜水": True, "高频": 2, "亡语": True},
    tags=['水生'],
    # 效果描述：免疫非战斗伤害。亡语：抽1张异象，使其具有两栖。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雄鹿",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=3,
    keywords={"丰饶": 2},
    # 效果描述：无法攻击对手。回合结束：若本回合未受到伤害，获得+1/1并对对手造成等同 于其攻击力的伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雌鹿",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"协同": True, "丰饶": 2},
    # 效果描述：攻击力最高的敌方异象无法攻击。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="豪猪",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    keywords={"协同": True, "坚韧": 1},
    # 效果描述：受到伤害后，对伤害来源造成等量伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牛蛙",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=2,
    keywords={"协同": True, "水生": True, "防空": True},
    tags=['水生'],
    # 效果描述：部署：将其复制加入同一列，使其具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="林蛙",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"两栖": True, "防空": True},
    tags=['两栖'],
    # 效果描述：部署：消灭场上攻击力最低的异象，获得被消灭异象的攻击力与防御力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="河狸",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"两栖": True, "潜水": True},
    tags=['两栖'],
    evolve_to="河坝",
    # 效果描述：回合开始：将一张“河坝”加入对方手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="河坝",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"水生": True},
    tags=['水生', '两栖', '生物'],
    is_token=True,
    # 效果描述：回合开始：将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="地鼠",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"协同": True, "尖刺": 1, "坚韧": 1},
    # 效果描述：如可能，移动以承担指向友方目标的伤害。回合结束：将HP改为6。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蛇",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"高频": 2, "亡语": True},
    # 效果描述：对HP不小于本异象的目标，伤害+1。亡语：对全体敌方目标造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="兀鹫",
    cost_str="0T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"空袭": True, "高地": True},
    # 效果描述：友方异象攻击后，若攻击目标 HP不小于2，令攻击目标失去1点HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="箭毒蛙",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=1,
    keywords={"迅捷": True, "两栖": True, "亡语": True},
    tags=['两栖'],
    # 效果描述：对对手造成的伤害翻倍。亡语：对方所有手牌花费+1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松毛虫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    # 效果描述：对对手造成的伤害翻倍。亡语：对方所有手牌获得：打出时，受到1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="“猹”",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"潜水": True, "两栖": True, "亡语": True},
    tags=['两栖'],
    evolve_to="西瓜",
    # 效果描述：回合结束：场上异象更少的一方抽一张牌。亡语：将一张“西瓜”加入原位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="西瓜",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：亡语：双方各抽2张牌。
    targets_fn=target_friendly_positions,
    special_fn=_xigua_special,
)

register_card(
    name="螳螂",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    keywords={"协同": True},
    # 效果描述：受伤时，友方陆地异象具有+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="象群",
    cost_str="6T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=8,
    keywords={"坚韧": 1, "先攻": -1},
    # 效果描述：部署：对所有异象造成1点伤害。回合开始时，随机眩晕一个敌方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="信鸽",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"两栖": True, "迅捷": True},
    tags=['两栖'],
    # 效果描述：回合结束：返回手牌，抽一张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="隼",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=3,
    health=1,
    keywords={"先攻": 3, "迅捷": True},
    # 效果描述：攻击后，返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸠",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=2,
    keywords={"协同": True, "两栖": True, "穿透": True},
    tags=['两栖'],
    # 效果描述：友方异象被消灭后，加入其位置并攻击。友方异象部署时，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="节肢座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True, "亡语": True},
    tags=['生物', '陆生', '昆虫'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="arthropod",
    on_statue_activate=_arthropod_top_effect,
    # 效果描述：（雕像激活后将在回合结束时移除 保留增益） 激活时：所有友方昆虫异象具有亡语；对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="多足底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['生物', '陆生', '昆虫'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="arthropod",
    on_statue_fuse=_arthropod_bottom_effect,
    # 效果描述：（只有“上下匹配”的雕像可以在一回合内拼装 否则需要两回合） 融合：激活座首，所有友方昆虫异象进入战场时+1/1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水肺座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '水生', '两栖'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="aquatic",
    on_statue_activate=_aquatic_top_effect,
    # 效果描述：激活时：所有友方两栖/水生异象部署花费-1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鳍尾底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"两栖": True},
    tags=['两栖', '生物', '水生'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="aquatic",
    on_statue_fuse=_aquatic_bottom_effect,
    # 效果描述：融合：激活座首，所有友方两栖/水生异象具有先攻1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="尖牙座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '肉食动物'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="predator",
    on_statue_activate=_predator_top_effect,
    # 效果描述：激活时：所有友方的陆生肉食动物进入战场时+2/1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="利爪底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"高地": True},
    tags=['生物', '陆生', '肉食动物'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="predator",
    on_statue_fuse=_predator_bottom_effect,
    # 效果描述：融合：激活座首，所有友方陆生肉食动物部署花费-1B。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="丰饶座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="sacrifice",
    on_statue_activate=_sacrifice_top_effect,
    # 效果描述：激活时：每回合首个友方B=0异象入场时献祭等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牢牲底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['生物', '陆生'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="sacrifice",
    on_statue_fuse=_sacrifice_bottom_effect,
    # 效果描述：中路 融合：激活座首，所有B=0异象丰饶等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="长翅座首",
    cost_str="2T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"脆弱": True},
    tags=['生物', '陆生', '飞禽'],
    statue_top=True,
    statue_bottom=False,
    statue_pair="avian",
    on_statue_activate=_avian_top_effect,
    # 效果描述：激活时：所有友方飞禽类异象具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="破风底座",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"高地": True},
    tags=['生物', '陆生', '飞禽'],
    statue_top=False,
    statue_bottom=True,
    statue_pair="avian",
    on_statue_fuse=_avian_bottom_effect,
    # 效果描述：融合：激活座首，所有友方飞禽类异象首次攻击力+2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="幼狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"成长": 1},
    evolve_to="成狼",
    # 效果描述：组队 成长时，若不是组队状态，重置计时。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="成狼",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True, "高频": 2, "成长": 2},
    tags=['友好', '生物', '肉食动物', '陆生'],
    is_token=True,
    evolve_to="狼王",
    # 效果描述：成长前，若未消灭过异象，失去成长2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="狼王",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"协同": True, "高频": 2},
    tags=['友好', '生物', '肉食动物', '陆生'],
    is_token=True,
    # 效果描述：所有友方异象具有坚韧1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="幼鸟",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=1,
    keywords={"成长": 2},
    evolve_to="成鸟",
    # 效果描述：部署：指向一个友方飞禽异象，使其获得+3防御力和“友方幼鸟无法选中”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="成鸟",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：若指向异象存活，将本异象转换为指向异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="奇怪的蛹",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=4,
    keywords={"协同": True},
    evolve_to="巨蛾",
    # 效果描述：出牌阶段结束：弃掉此牌，将一张“巨蛾”洗入卡组。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="巨蛾",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"迅捷": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：友方迅捷异象具有+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="群猿",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    # 效果描述：组队 每有一个其它异象被献祭，+1/1，丰饶等级+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="狐",
    cost_str="0T4B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=0,
    health=4,
    keywords={"迅捷": True, "三重打击": True},
    # 效果描述：攻击后，获得+1攻击力。免疫偶数伤害。
    targets_fn=target_friendly_positions,
    special_fn=_hu_special,
)

register_card(
    name="鹤",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    keywords={"两栖": True},
    tags=['两栖'],
    # 效果描述：组队 回合开始：重置一个异象的攻击力与防御力，你获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="夜枭",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    # 效果描述：敌方异象部署、加入和被消灭时，对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鮟鱇",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    keywords={"重甲": 1, "水生": True},
    tags=['水生'],
    # 效果描述：回合结束：指向一个异象。回合开始：消灭指向异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹏",
    cost_str="5T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=6,
    keywords={"横扫": 1, "迅捷": True},
    # 效果描述：所有花费≤5的非飞禽异象部署时具有休眠I。 部署：使敌方花费不大于4的异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: return_to_hand(t, g, p),
)

register_card(
    name="鲲",
    cost_str="5T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=2,
    health=6,
    keywords={"水生": True, "坚韧": 1, "横扫": 1},
    tags=['水生'],
    # 效果描述：平地均算作是水路。 部署：使全体友方非两栖异象获得“水生”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="食蚁兽",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"迅捷": True},
    # 效果描述：被弃掉或被从卡组中移除时：改为加入战场。部署：双方随机弃一张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="头鹿",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=4,
    keywords={"协同": True, "坚韧": 1, "成长": 2},
    evolve_to="老鹿",
    # 效果描述：你的手牌花费-1T。成长时，若场上有B=0异象，改为重置计时。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="老鹿",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：你的手牌花费+1T。无法选中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="信天翁",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"迅捷": True, "空袭": True},
    # 效果描述：部署：使异象更多一方的一个异象返回其所有者手中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鼯鼱",
    cost_str="1T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=1,
    keywords={"迅捷": True},
    # 效果描述：必须是本轮部署的第一个异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="豺",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=4,
    health=4,
    keywords={"亡语": True},
    # 效果描述：部署：失去1个T槽。亡语：所有手牌花费-1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="负鼠",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"坚韧": 1},
    # 效果描述：场上有不少于3个友方异象时，花费-2B。部署：开发一张卡组中的牌。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: g.develop_card(p, p.original_deck_defs),
)

register_card(
    name="追猎者",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=1,
    keywords={"亡语": True},
    # 效果描述：部署：指向一个不处于本列的异象。亡语：将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="嘲鸫",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"两栖": True, "潜水": True},
    tags=['两栖'],
    # 效果描述：友方异象在受到致命伤害前，先获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="木鹊",
    cost_str="5T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=3,
    # 效果描述：你的手牌花费-1B。 回合结束：若本回合对手受到的伤害累计不小于3，你获得1B。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="牛虻",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"协同": True},
    # 效果描述：敌方目标被指向后，也算作是被本异象指向。 回合开始：使所有被本异象指向的目标失去1点HP。 部署：指向一个目标。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="野牛",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：攻击目标的HP不大于3时，具有穿透。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="跳蛛",
    cost_str="1T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"防空": True},
    # 效果描述：若这是你本回合部署的最后一个异象，获得迅捷。 你部署献祭点数大于0的异象时，对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鹳",
    cost_str="4T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"视野": 2, "两栖": True},
    tags=['两栖'],
    # 效果描述：将其消灭的异象的回响加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="燕",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=3,
    health=3,
    keywords={"迅捷": True, "穿刺": True, "两栖": True},
    tags=['两栖'],
    # 效果描述：部署：失去一个T槽。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="天牛",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True, "穿透": True},
    # 效果描述：回合结束：使同列敌方前排异象移动至后排，后排异象返回对方手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="射水鱼",
    cost_str="4T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"水生": True, "防空": True, "视野": 2},
    tags=['水生'],
    # 效果描述：对空袭与昆虫异象伤害翻倍。受到本异象伤害的异象本回合改为在回合结束时 攻击。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸮",
    cost_str="4T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=5,
    keywords={"视野": 1, "先攻": 1},
    # 效果描述：攻击时，改为与目标对战。消灭一个异象后，获得等同于其攻击力的HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鬣狗",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=2,
    health=1,
    keywords={"迅捷": True, "先攻": 1, "协同": True},
    # 效果描述：将其消灭的异象的回响加入手牌。你打出或弃掉回响时，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="寄居蟹",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"坚韧": 1, "两栖": True, "协同": True},
    tags=['两栖'],
    # 效果描述：回合结束：向相邻方向移动一格。 将受到其伤害的异象的回响加入手牌，回合开始时弃掉。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猞猁",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=5,
    keywords={"协同": True, "坚韧": 1},
    # 效果描述：相邻异象受到伤害时，改为由本异象承受。 回合结束：若本异象本回合未受到伤害，对对手造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蟒",
    cost_str="3T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=3,
    keywords={"迅捷": True, "亡语": True},
    # 效果描述：必须是本回合双方部署的第2个异象。 亡语：若消灭过异象，随机消灭一个敌方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="避役",
    cost_str="3T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=2,
    # 效果描述：受到不小于4的单次伤害时，改为失去1点HP。 部署：开发1张冥刻阴谋。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.card_type == CardType.CONSPIRACY]),
)

register_card(
    name="雪豹",
    cost_str="3T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=5,
    keywords={"先攻": 1, "高地": True},
    # 效果描述：部署：将1个花费不大于2T的异象移动至友方区域。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水螅岩",
    cost_str="5T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=5,
    health=3,
    keywords={"水生": True, "成长": True, "亡语": True},
    tags=['水生'],
    evolve_to="水螅群",
    # 效果描述：亡语：若是由于异象效果被消灭，改为在回合结束时成长。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="水螅群",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"水生": True},
    tags=['水生', '两栖', '生物'],
    is_token=True,
    # 效果描述：抽牌阶段：对方失去3T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚜虫",
    cost_str="4T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"亡语": True},
    # 效果描述：亡语：T槽更少的一方失去1个T槽。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚊",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True},
    # 效果描述：对方所有异象花费+2T。对方异象部署前，本异象返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鸬鹚",
    cost_str="3T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True},
    # 效果描述：友方异象更少时，使所有敌方异象具有-1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="虎",
    cost_str="4T3B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    attack=6,
    health=6,
    keywords={"坚韧": 2, "绝缘": True},
    # 效果描述：对方无法使用策略指向友方异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="环形虫",
    cost_str="2T2B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"亡语": True},
    # 效果描述：部署：指向一个异象。亡语：使伤害来源与一个随机敌方异象对战。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="石钱子",
    cost_str="2T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=1,
    health=4,
    keywords={"协同": True, "迅捷": True, "亡语": True},
    evolve_to="断尾",
    # 效果描述：亡语：将一张“断尾”加入原位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="断尾",
    cost_str="0T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：回合结束：转换为“石钱子”。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蚁穴",
    cost_str="5T1B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    attack=0,
    health=6,
    keywords={"坚韧": 1},
    # 效果描述：场上有昆虫类异象时，HP无法降至1以下。 回合开始：将1张“兵蚁”加入战场。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="兵蚁",
    cost_str="1T0B",
    card_type=CardType.MINION,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True, "迅捷": True},
    tags=['生物', '陆生'],
    # 效果描述：场上每有一个友方昆虫异象，+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="松鼠瓶",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将2张“松鼠”加入手牌，此前你每使用过一次“松鼠瓶”，额外加入一只“松鼠”。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="树洞",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将一只“松鼠”加入战场，本回合所有B=0友方异象无法选中。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="血瓶",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张异象，获得3B。若非松鼠，抽一张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="金牙齿",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对一个目标造成1点伤害。若将其消灭，获得1T，抽一张牌。
    targets_fn=target_any_minion_or_enemy_player,
    effect_fn=_jin_yachi_strategy,
)

register_card(
    name="钳子",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对你造成2点伤害，然后对一个异象造成4点伤害。抽一张牌。
    targets_fn=target_any_minion,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="林鼠匕首",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：对你造成4点伤害，然后造成8点伤害，随机分配至所有敌方目标。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="骨王",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：选择并弃一张异象，若其献祭等级与丰饶等级之积不小于2，将一张“骨王之 赏”加入手牌；否则将一张“骨王之惠”加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="骨王之惠",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_token=True,
    # 效果描述：抽一张牌，使其-2T1B。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="骨王之赏",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_token=True,
    # 效果描述：抽2张牌，免除其献祭点数。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(2, game=g) or True),
)

register_card(
    name="蜡烛",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：你获得+6HP，抽2张牌。此前你每使用过一次“烛烟”，花费-2T。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(2, game=g) or True),
)

register_card(
    name="植物学家",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张异象，使你手牌中另一张同名异象攻防翻倍且花费+1T。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="皮毛商",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：随机将一张手牌洗入卡组。抉择：抽2张异象或获得4T。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="猎人",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：选择并弃一张牌，将其2张复制进入牌库。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="鱼钩",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将一个花费不大于3T的异象移动至友方同一列。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="扇子",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象具有空袭直到回合结束。抽1张牌。
    targets_fn=target_any_minion,
    effect_fn=_shanzi_strategy,
)

register_card(
    name="剥皮刀",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：眩晕一个异象。若是迅捷异象，改为消灭。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="岩瓶",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一列陆地也算作是高地。抽一张高地异象。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="蓝月",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：下个出牌阶段，你的所有异象献祭等级+1。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="炸弹夫人的遥控器",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一个异象获得亡语：随机对一个友方异象造成2点伤害，使其获得此亡语。
    targets_fn=target_friendly_minions,
    effect_fn=lambda p, t, g, extras=None: (setattr(t, "base_keywords", dict(getattr(t, "base_keywords", {}))) or t.base_keywords.update({"亡语": True}) or t.recalculate() or True) if hasattr(t, "recalculate") else False,
)

register_card(
    name="相机",
    cost_str="7T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将场上的一个异象移动至你的手牌中。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="沙漏",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：手牌数不大于3时，花费-2T。随机将对方一张手牌放置至其卡组顶，你抽1 张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="血月",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：你的所有异象具有+1攻击力和坚韧1，直到回合结束。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="胶水",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象获得：在受到致命伤害前，+0/1。若因此存活，+1/1。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="时钟",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：弃掉一个花费不大于7T的异象，在3回合后的抽牌阶段将其加入战场。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="营火",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使手牌中一个异象获得 +2/3 和亡语：对方抽一张牌。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="冰块",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个友方异象获得 +0/4 并冰冻2回合，期间其拥有坚韧I。
    targets_fn=target_friendly_minions,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="木雕师",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：开发一张座首和一张底座。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="木漆",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：使一个木雕组件获得+6HP和绝缘。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="玛珂",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：使一个目标免疫下次伤害。若指向异象，抽1张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="稿纸",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：本回合你每部署1个异象，花费-1T。你获得1个T槽，对方失去1个T槽。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="金羊皮",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：开发一张冥刻金卡异象。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.UNDERWORLD and c.rarity == Rarity.GOLD and c.card_type == CardType.MINION]),
)

register_card(
    name="繁盛",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=2,
    # 效果描述：弃掉所有手牌，你获得：“抽牌阶段：你多抽1张牌。”
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="旱季",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对所有陆地异象造成3点伤害，然后使所有陆地异象+1/2。你失去1个T槽。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="山洪",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：回合结束时，使一列陆地算作水路直到下回合结束。你失去1个T槽。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="水疫",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：若水路有敌方异象，对所有敌方异象造成1点伤害，若有异象被消灭，重复此 流程。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="沙尘",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：眩晕一个敌方异象。若本回合对方先手，结束双方出牌阶段。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="狂风",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：对方无法部署异象，直到下一个出牌阶段结束。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="骤雨",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将1个异象返回其所有者手牌。对手下回合无法抽牌。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="屠刀",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：将2张“松鼠”加入手牌。本回合，你每献祭一个异象，抽一张牌。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="砧板",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃一张牌，抽一张花费更高的牌。若弃掉的牌献祭等级与丰饶等级之积 不小于2，你获得2B。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="还尘",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭一个受伤异象。若是友方异象，抽三张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="继代",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象获得亡语：将其-1/1的复制加入你的手牌。
    targets_fn=target_any_minion,
    effect_fn=lambda p, t, g, extras=None: (setattr(t, "base_keywords", dict(getattr(t, "base_keywords", {}))) or t.base_keywords.update({"亡语": True}) or t.recalculate() or True) if hasattr(t, "recalculate") else False,
)

register_card(
    name="野火",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，将一个异象返回其所有者牌堆顶。眩晕周围异象。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="轮回",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，抽1张牌。若弃掉回响，对一个目标造成4点伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="更替",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使手牌中的1个回响异象回响等级+1。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="破晓",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=2,
    # 效果描述：抽2张牌。然后若你剩余T点不大于1，获得两倍于你本对局失去过T槽数目的T点。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="柳林风声",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张异象，将其花费为5T的复制加入对方手牌。对方部署其它异象时，将此异象加入友方区域。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="贺胜",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=3,
    # 效果描述：展示卡组顶的4张牌，抽取其中花费最高的一张，使其花费为0T。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="善潜",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使一个异象立刻成长，然后使其获得+1/1。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="粗粝",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使1个异象获得：成长时，+2/2。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="肉蛋糕",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.GOLD,
    immersion_level=3,
    # 效果描述：移除卡组顶的6张牌。将你的HP设为20。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="新月",
    cost_str="7T",
    card_type=CardType.STRATEGY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="剪刀",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方部署异象后，失去4T。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="墨水",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方使用花费不大于4T的策略时，改为将其洗入对方卡组。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="劲风",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方额外抽1张牌后，将其弃掉，随机使对方1张手牌花费+1T。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="离群",
    cost_str="3T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭接下来首列进入协同状态的异象。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="入河",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方部署异象前，将其移除，在下回合开始后将其加入原位。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="怪石",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方拉闸时，若其剩余T点等于0，对方失去一个T槽。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="海市蜃楼",
    cost_str="3T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：1个异象被指向前，改为其随机敌方异象成为指向目标。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="掩星",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：场上敌方异象数量成为唯一最多时，抽2张牌。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(2, game=g) or True),
)

register_card(
    name="反戈",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方打出下一张牌时，若是异象，对对手造成等同于其花费的伤害。
    targets_fn=target_enemy_player,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="夜袭",
    cost_str="2T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：敌方异象对你造成伤害前，使其先获得-2攻击力。若具有迅捷，将其消灭。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="蓄锐",
    cost_str="1T",
    card_type=CardType.CONSPIRACY,
    pack=Pack.UNDERWORLD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方下次拍铃时，若此轮次未出牌，你获得4T。
    targets_fn=target_none,
    condition_fn=None,  # TODO: 实现触发条件
    effect_fn=None,  # TODO: 实现效果
)
