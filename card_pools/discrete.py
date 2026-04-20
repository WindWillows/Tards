# 自动生成的卡包定义文件
# 由 translate_packs.py 翻译生成

from tards import register_card, CardType, Pack, Rarity, DEFAULT_REGISTRY
from tards.targets import target_friendly_positions, target_none, target_any_minion, target_enemy_minions, target_enemy_player, target_self, target_friendly_minions, target_hand_minions
from tards.auto_effects import move_enemy_to_friendly, swap_units, return_to_hand
from .discrete_effects import *

# Pack: DISCRETE

register_card(
    name="火把",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：每回合你首次获得额外的T槽时，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_huoba_special,
)

register_card(
    name="萤石",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：你受到的伤害-1。回合结束：你获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=_yingshi_special,
)

register_card(
    name="信标",
    cost_str="1D1G1I1T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=8,
    keywords={"绝缘": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：你获得1个C槽或T槽时，开发1张卡组中的牌。若手牌已满，将其洗入卡组。
    targets_fn=target_friendly_positions,
    special_fn=_xinbiao_special,
)

register_card(
    name="书架",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    keywords={"协同": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：受到伤害时，将1张“书”加入手牌。（“书”的介绍见策略区）
    targets_fn=target_friendly_positions,
    special_fn=_shujia_special,
)

register_card(
    name="钓鱼竿",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"协同": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：河岸 回合结束：将1张“书”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="末影螨",
    cost_str="1I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True},
    tags=['昆虫', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：对1个单位造成1点伤害。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=lambda p, t, g, extras=None: (t.health_change(-1) if hasattr(t, "health_change") else (t.take_damage(1) if hasattr(t, "take_damage") else False) or True),
)

register_card(
    name="末影人",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=1,
    keywords={"协同": True, "迅捷": True},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到伤害前，与1个友方单位交换位置。
    targets_fn=target_friendly_positions,
    special_fn=_moyiren_special,
)

register_card(
    name="烈焰人",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=2,
    keywords={"迅捷": True, "亡语": True},
    tags=['地狱', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：溢出伤害转移至对手。亡语：将1张“烈焰粉”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_lieyanren_special,
)

register_card(
    name="烈焰粉",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['地狱', '非生命'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：对一个单位及其相邻单位造成1点伤害。
    targets_fn=target_any_minion,
    effect_fn=_lieyanfen_strategy,
)

register_card(
    name="恶魂",
    cost_str="1G1T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"亡语": True},
    tags=['地狱', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：本单位造成的伤害无视坚韧效果。 亡语：将1张“恶魂之泪“加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_ehan_special,
)

register_card(
    name="恶魂之泪",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['地狱', '敌对', '非生命'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：对1个目标造成2点伤害 对方随机弃1张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="凋零骷髅",
    cost_str="2I1T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"亡语": True},
    tags=['地狱', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到其伤害的目标在回合结束时获得-1/1。若是对手，移除其卡组顶的1张牌。 亡语：将1张“凋零骷髅头”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_diaolingkulou_special,
)

register_card(
    name="凋零骷髅头",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['地狱', '敌对', '非生命'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：移除对方卡组顶的1张牌。
    targets_fn=target_none,
    effect_fn=_diaolingkuloutou_strategy,
)

register_card(
    name="狗",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True, "迅捷": True, "亡语": True},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：处于协同时，具有+1攻击力。亡语：同列友方单位立刻攻击1次。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="羊",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：回合结束：若其为本回合唯一部署的友方单位，抽1张牌，将其花费改为0T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猪",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：指向1个单位，为其承担伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="马",
    cost_str="1G1T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=6,
    keywords={"协同": True},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：与其同列的友方单位具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=_ma_special,
)

register_card(
    name="驴",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：回合结束：若处于协同，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_lv_special,
)

register_card(
    name="羊驼",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"坚韧": 1, "先攻": 1},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到其伤害的单位获得-1攻击力。然后若其攻击力为0，将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="铁傀儡",
    cost_str="4I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=6,
    health=6,
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到等于其HP的单次伤害时，将其免除。 你打出“铁锭”时，本单位获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=_tiekuilei_special,
)

register_card(
    name="雪傀儡",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"亡语": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    evolve_to="雪块",
    # 效果描述：部署：在三路平地各加入1个“雪块”。亡语：将1张“雪球”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_xuewulou_special,
)

register_card(
    name="雪块",
    cost_str="0T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=1,
    keywords={"协同": True, "尖刺": 1},
    tags=['非生命'],
    hidden_keywords={},
    is_token=True,
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雪球",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['非生命'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：对一个单位造成1点伤害。然后若其HP不大于2 将其冰冻。
    targets_fn=target_any_minion,
    effect_fn=_xueqiu_strategy,
)

register_card(
    name="狐狸",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=2,
    tags=['友好', '生物', '肉食动物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到大于其HP的单次伤害时，将其免除。
    targets_fn=target_friendly_positions,
    special_fn=_huli_special,
)

register_card(
    name="豹猫",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"迅捷": True},
    tags=['友好', '生物', '肉食动物', '陆生'],
    hidden_keywords={},
    # 效果描述：本单位攻击时，对其指向的单位造成等量伤害。部署：指向一个单位。
    targets_fn=target_friendly_positions,
    special_fn=_baomao_special,
)

register_card(
    name="海龟",
    cost_str="1G1T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=5,
    keywords={"协同": True, "两栖": True, "坚韧": 1},
    tags=['两栖', '友好', '生物'],
    hidden_keywords={},
    # 效果描述：受到伤害后，将攻击力最高的敌方单位的攻击力设为1，直到下回合结束。
    targets_fn=target_friendly_positions,
    special_fn=_haigui_special,
)

register_card(
    name="鹦鹉",
    cost_str="5T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['友好', '生物', '陆生', '飞禽'],
    hidden_keywords={},
    # 效果描述：回合开始：将出牌阶段对方使用的首张策略的复制加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="鲑鱼",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"协同": True, "水生": True, "亡语": True},
    tags=['水生', '两栖', '友好', '生物'],
    hidden_keywords={},
    # 效果描述：亡语：抽1张牌，如可能，使其获得-1T花费。否则，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_guiyu_special,
)

register_card(
    name="河豚",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=6,
    keywords={"水生": True, "亡语": True},
    tags=['水生', '两栖', '友好', '生物'],
    hidden_keywords={},
    # 效果描述：亡语：造成等同于其受到过伤害总和的伤害，随机分配至所有敌方单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="村民",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：每回合每种矿物被首次兑换时，获得1T。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="流浪商人",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"协同": True},
    tags=['友好', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：抽牌阶段，取消抽牌，开发一张卡组中的牌。 场上有友方友好单位时，无法选中。
    targets_fn=target_friendly_positions,
    special_fn=_liulangshangren_special,
)

register_card(
    name="北极熊",
    cost_str="6T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"两栖": True, "坚韧": 1, "穿刺": True},
    tags=['两栖', '友好', '生物', '肉食动物'],
    hidden_keywords={},
    # 效果描述：回合结束：若HP不大于2，获得-1/+2。
    targets_fn=target_friendly_positions,
    special_fn=_beijixiong_special,
)

register_card(
    name="炽足兽",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：与其同列的友方单位具有先攻1和+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=_chizushou_special,
)

register_card(
    name="疣猪",
    cost_str="3G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"坚韧": 2, "串击": True},
    tags=['友好', '地狱', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：双方无法部署花费不大于4T的单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猪灵",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    tags=['友好', '地狱', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：每回合首次使用金锭时，随机将1张掉落物加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猪灵蛮兵",
    cost_str="3G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"坚韧": 2, "高频": 2},
    tags=['友好', '地狱', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：友方友好单位无法被选中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="猪灵弓兵",
    cost_str="3G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"迅捷": True, "高频": 3, "破甲": 3},
    tags=['友好', '地狱', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：一回合内，此前每攻击过目标1次，对其攻击力-1。 每消灭1个单位，将1张“光灵箭”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="光灵箭",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['非生命'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个单位获得-1坚韧等级。
    targets_fn=target_any_minion,
    effect_fn=_guanglingjian_strategy,
)

register_card(
    name="幻翼",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=3,
    keywords={"迅捷": True, "视野": 1},
    tags=['敌对', '生物', '陆生', '飞禽'],
    hidden_keywords={},
    # 效果描述：消灭单位前，改为移除对方卡组顶的2张牌。
    targets_fn=target_friendly_positions,
    special_fn=_huanyi_special,
)

register_card(
    name="刌民",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    keywords={"串击": True},
    tags=['生物', '精灵', '陆生'],
    hidden_keywords={},
    # 效果描述：友方每有1个敌对单位和中立单位，具有+1攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="卫道士",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：所有敌方单位获得-1坚韧等级。
    targets_fn=target_friendly_positions,
    special_fn=_weidaoshi_special,
)

register_card(
    name="潜影贝",
    cost_str="1G3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=5,
    keywords={"坚韧": 1, "先攻": -1, "视野": 2},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：敌方单位受到1点伤害后，在回合结束时返回手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="唤魔者",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"绝缘": True},
    tags=['敌对', '生物', '精灵', '陆生'],
    hidden_keywords={},
    # 效果描述：回合开始：将1张精灵单位加入战场，使其具有迅捷。 场上有精灵单位时，无法选中。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="劫掠兽",
    cost_str="1D1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=6,
    keywords={"高频": 2},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：眩晕其它所有单位。 单位进入战场时，获得-1HP和-1坚韧等级。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="僵尸",
    cost_str="1G2T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：造成伤害时，你获得等量HP。
    targets_fn=target_friendly_positions,
    special_fn=_jiangshi_special,
)

register_card(
    name="尸壳",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"高地": True},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：回合开始：对所有敌方单位造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=_shike_special,
)

register_card(
    name="溺尸",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=6,
    keywords={"水生": True},
    tags=['水生', '两栖', '敌对', '生物'],
    hidden_keywords={},
    # 效果描述：部署：失去1T。 对单位造成伤害时，弃掉对方花费最低的1张手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蜘蛛",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=2,
    keywords={"亡语": True},
    tags=['敌对', '昆虫', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：使1个单位失去迅捷，高频和空袭。 亡语：将1张“蜘蛛眼“加入手牌。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=_zhizhu_special,
)

register_card(
    name="蜘蛛眼",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['敌对', '昆虫', '生物', '陆生'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个单位获得-2攻击力。
    targets_fn=target_any_minion,
    effect_fn=_zhizhuyan_strategy,
)

register_card(
    name="洞穴蜘蛛",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"亡语": True},
    tags=['敌对', '昆虫', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：将1个单位的攻击力设为1。 亡语：将1张“蜘蛛眼“加入手牌。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="骷髅",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=3,
    keywords={"迅捷": True},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：攻击前，改为对HP最低的敌方单位造成等量伤害。
    targets_fn=target_friendly_positions,
    special_fn=_kulou_special,
)

register_card(
    name="蠹虫",
    cost_str="1I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=1,
    keywords={"协同": True},
    tags=['敌对', '昆虫', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：抽1张“蠹虫“。
    targets_fn=target_friendly_positions,
    special_fn=_shuaichong_special,
)

register_card(
    name="流髑",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=5,
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：回合开始：随机冰冻1个敌方单位。若其已被冰冻，将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=_liudu_special,
)

register_card(
    name="海豚",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    keywords={"迅捷": True, "水生": True},
    tags=['水生', '两栖', '友好', '生物'],
    hidden_keywords={},
    # 效果描述：部署：展示卡组顶的3张牌，选择1张加入手牌，另2张置入卡组底。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蝾螈",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"协同": True, "两栖": True},
    tags=['两栖', '生物'],
    hidden_keywords={},
    # 效果描述：受到伤害后，返回手牌。 返回手牌：使所有友方目标获得+1HP。
    targets_fn=target_friendly_positions,
    special_fn=_rongyuan_special,
)

register_card(
    name="劫掠队长",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    keywords={"绝缘": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：回合结束：若本回合对手受到的伤害不小于3，使对手失去2点HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="僵尸村民",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    tags=['友好', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：将1张“金苹果”置入卡组顶。 被“金苹果“指向时，抽1张牌，使你的所有手牌获得-1T花费。
    targets_fn=target_friendly_positions,
    special_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

register_card(
    name="末影箱",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=5,
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：你每在手牌已满时抽1张牌，对一个随机敌方目标造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="潜行者",
    cost_str="5T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：消灭1个与本单位距离最近的单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="矿车",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：亡语：获得1个T槽。
    targets_fn=target_friendly_positions,
    special_fn=_kuangche_special,
)

register_card(
    name="恼鬼",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=2,
    keywords={"迅捷": True},
    tags=['敌对', '生物', '精灵', '陆生'],
    hidden_keywords={},
    # 效果描述：回合结束时，将其消灭。
    targets_fn=target_friendly_positions,
    special_fn=_naogui_special,
)

register_card(
    name="滴水石锥",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=5,
    keywords={"尖刺": 2, "协同": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：受到伤害时，对对手造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=_dishuizhuichui_special,
)

register_card(
    name="僵尸鸡骑士",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['友好', '敌对', '生物', '陆生', '飞禽'],
    hidden_keywords={},
    # 效果描述：部署：移除卡组顶的1张友好单位。若如此做，获得迅捷和先攻1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="骷髅马骑士",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"迅捷": True, "视野": 1},
    tags=['友好', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：你的手牌具有+1T花费，直到下回合结束。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="蜘蛛骑士",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['敌对', '昆虫', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：友方策略造成的伤害+1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="地狱传送门",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=4,
    keywords={"坚韧": 1},
    tags=['地狱', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：友方单位被消灭时，改为将其洗入卡组。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="船",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"协同": True, "两栖": True, "漂浮物": True},
    tags=['两栖', '非生命'],
    hidden_keywords={},
    # 效果描述：其上单位被消灭时，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="TNT炮",
    cost_str="3I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"迅捷": True, "破甲": 3},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：攻击单位前，先造成等同于目标部署花费的伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="善魂",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：指向1个单位。 亡语：使其+2/2。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="甘蔗",
    cost_str="5T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"两栖": True, "迅捷": True, "亡语": True},
    tags=['两栖', '生物'],
    hidden_keywords={},
    # 效果描述：亡语：将1张“书”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=_ganzhe_special,
)

register_card(
    name="绊线钩",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=3,
    keywords={"协同": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：受到伤害前，每有1个友方“绊线钩“与之同行或同列，对1个随机敌方目标造成1 次1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="橡树苗",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    keywords={"协同": True, "成长": 2},
    tags=['生物', '陆生'],
    hidden_keywords={},
    evolve_to="橡树",
    # 效果描述：若你拥有不小于11个T槽，立刻成长。
    targets_fn=target_friendly_positions,
    special_fn=_xiangshu_special,
)

register_card(
    name="橡树",
    cost_str="0T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    is_token=True,
    # 效果描述：成长时，获得1个C槽，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="发射器",
    cost_str="2I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    keywords={"横扫": 1},
    tags=['非生命'],
    hidden_keywords={},
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="侦测器",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：敌方单位部署时，对其造成1点伤害，使其失去迅捷。
    targets_fn=target_friendly_positions,
    special_fn=_zhenceqi_special,
)

register_card(
    name="音乐盒",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：对方每回合打出的第一张手牌花费翻倍。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="钟",
    cost_str="3I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=4,
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：友方单位造成1点战斗伤害时，改为造成3点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="活塞飞艇",
    cost_str="5T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=6,
    health=1,
    keywords={"空袭": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：同列没有敌方单位时，具有迅捷。
    targets_fn=target_friendly_positions,
    special_fn=_huosai_feiting_special,
)

register_card(
    name="潮涌核心",
    cost_str="8T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=8,
    keywords={"视野": 2, "高频": 2, "两栖": True},
    tags=['两栖', '非生命'],
    hidden_keywords={},
    # 效果描述：其它友方单位具有+2攻击力。
    targets_fn=target_friendly_positions,
    special_fn=_chaoonghexin_special,
)

register_card(
    name="凋灵炮塔",
    cost_str="6T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"视野": 1, "坚韧": 1},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：溢出伤害转移至对手。 回合结束：若你的手牌数不小于6，随机攻击1个敌方单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="活塞城槌",
    cost_str="5T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=3,
    keywords={"迅捷": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：无法选中攻击力不大于本单位的单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="禁人塔",
    cost_str="2D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=6,
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：眩晕1行单位。 被眩晕单位多眩晕1回合。
    targets_fn=target_friendly_positions,
    special_fn=_jinrenta_special,
)

register_card(
    name="盾构机",
    cost_str="4I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=7,
    health=10,
    keywords={"坚韧": -1},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：无法攻击对手。每消灭1个单位，抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="岩浆艇",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=2,
    keywords={"迅捷": True, "串击": True},
    tags=['地狱', '非生命'],
    hidden_keywords={},
    # 效果描述：友方单位部署时，消灭本单位。
    targets_fn=target_friendly_positions,
    special_fn=_yanjiangting_special,
)

register_card(
    name="水幕墙",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=8,
    keywords={"协同": True, "坚韧": 2},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：使所有友方单位获得防空。 受到非生命单位或策略造成的伤害时，将其设为0点。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="末地船",
    cost_str="1D1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=6,
    keywords={"绝缘": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：非迅捷友方单位部署时，获得-1HP和迅捷。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="盔甲架",
    cost_str="1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：被弃掉时，将2张花费为1I的复制加入手牌。 亡语：抽1张牌。
    targets_fn=target_friendly_positions,
    special_fn=_kuijiujia_special,
)

register_card(
    name="末地水晶",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=5,
    keywords={"亡语": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：友方目标受到对方策略效果时，改为由本单位承受。 亡语：若是被策略效果消灭，对所有敌方目标造成2点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="漏斗矿车",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=2,
    keywords={"亡语": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：部署：抽1张花费不大于4T的单位。 亡语：将其加入本单位所在的位置。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="僵尸猪人",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"坚韧": 1},
    tags=['友好', '地狱', '敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：与1个敌方单位对战。若将其消灭，获得-1攻击力。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_enemy_minions, 1, False)],
    special_fn=_jiangshizhuren_special,
)

register_card(
    name="女巫",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"绝缘": True},
    tags=['敌对', '生物', '陆生'],
    hidden_keywords={},
    # 效果描述：部署：使1个目标获得-2HP。若将其消灭，获得：“本列结算时，使1个目标获得 -2HP。若将其消灭，具有“无法被消灭“直到回合结束。”
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="重生锚",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=6,
    keywords={"协同": True, "亡语": True},
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：友方其它非回响单位具有“亡语：将本单位的回响加入手牌。“ 友方回响单位的花费设为1G。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="哭泣的黑曜石",
    cost_str="2G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：友方回响单位具有“部署：获得+2/2。“
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="杀手兔",
    cost_str="1D",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=6,
    health=2,
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：结算阶段不攻击。出牌阶段，敌方单位首次部署时，本单位攻击1次。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="守卫者",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=2,
    keywords={"两栖": True, "串击": True, "迅捷": True},
    tags=['两栖', '敌对', '生物'],
    hidden_keywords={},
    # 效果描述：对对手造成伤害后，消灭本单位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="Toast_",
    cost_str="1D1G",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=5,
    keywords={"迅捷": True, "破甲": 1},
    tags=['生物', '陆生'],
    hidden_keywords={},
    # 效果描述：攻击单位后，若目标未被消灭，获得-1HP并攻击1次。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="高炉",
    cost_str="4I",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=5,
    tags=['非生命'],
    hidden_keywords={},
    # 效果描述：抽取：随机将“铁锭”，“金锭”，“钻石”中的1张加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="铁锭",
    cost_str="2CT",
    card_type=CardType.MINERAL,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    hidden_keywords={},
    mineral_type="I",
    stack_limit=1,
    is_token=True,
    # 效果描述：堆叠上限为4。打出：获得1T。
    targets_fn=target_none,
    effect_fn=_tieding_mineral,
)

register_card(
    name="金锭",
    cost_str="3CT",
    card_type=CardType.MINERAL,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    hidden_keywords={},
    mineral_type="G",
    stack_limit=1,
    is_token=True,
    # 效果描述：堆叠上限为2。打出：获得2T。
    targets_fn=target_none,
    effect_fn=_jinding_mineral,
)

register_card(
    name="钻石",
    cost_str="5CT",
    card_type=CardType.MINERAL,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    hidden_keywords={},
    mineral_type="D",
    stack_limit=1,
    is_token=True,
    # 效果描述：堆叠上限为1。打出：获得4T。
    targets_fn=target_none,
    effect_fn=_zuanshi_mineral,
)

register_card(
    name="青金石",
    cost_str="2CT",
    card_type=CardType.MINERAL,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    hidden_keywords={},
    mineral_type="M",
    stack_limit=1,
    is_token=True,
    # 效果描述：堆叠上限为2。打出：无事发生。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现打出效果
)

register_card(
    name="木镐",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：获得1个额外的C槽。
    targets_fn=target_none,
    effect_fn=_mubiao_strategy,
)

register_card(
    name="石镐",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：获得1个额外的T槽。然后若剩余T点不少于2，抽一张牌。
    targets_fn=target_none,
    effect_fn=_shibiao_strategy,
)

register_card(
    name="铁镐",
    cost_str="2I1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：获得2个额外的C槽。回合结束：抽一张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="金镐",
    cost_str="2G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：获得1个额外的C槽和T槽。然后若你的HP低于对手，你获得+4HP。
    targets_fn=target_none,
    effect_fn=_jinbiao_strategy,
)

register_card(
    name="钻石镐",
    cost_str="1D3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：获得1个额外的C槽和2个额外的T槽。然后若对方单位数更多，随机消灭一个 花费不大于4T的敌方单位。
    targets_fn=target_none,
    effect_fn=_zuanshibiao_strategy,
)

register_card(
    name="书",
    cost_str="1M",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：堆叠上限为2。开发1张“附魔书”。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.name == "附魔书"]),
)

register_card(
    name="多重射击",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：对所有敌方目标造成2点伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="冰霜行者",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：冰冻1个单位及其相邻单位。抽1张牌。
    targets_fn=target_hand_minions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    effect_fn=_mingmingpai_strategy,
)

register_card(
    name="火矢",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个陆地单位获得+4攻击力。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="横扫之刃",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：对1行单位造成3点伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="饵钓",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：将2张“书”加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="锋利",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：对一个单位造成6点伤害。
    targets_fn=target_any_minion,
    effect_fn=lambda p, t, g, extras=None: (t.health_change(-6) if hasattr(t, "health_change") else (t.take_damage(6) if hasattr(t, "take_damage") else False) or True),
)

register_card(
    name="忠诚",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个友方单位获得亡语：将本单位的复制加入手牌。
    targets_fn=target_friendly_minions,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="击退",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：将1个单位返回其所有者手牌。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="时运",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抽2张牌。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(2, game=g) or True),
)

register_card(
    name="深海探索者",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个水路单位获得+2/2 或 对其造成6点伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="耐久",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抽1张牌 你获得+4HP。
    targets_fn=target_hand_minions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    effect_fn=_mingmingpai_strategy,
)

register_card(
    name="保护",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：使1个单位获得+0/3 和坚韧1。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="精准采集",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：开发1张卡组中的牌。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: g.develop_card(p, p.original_deck_defs),
)

register_card(
    name="效率",
    cost_str="0T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：获得1个额外的C槽。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="经验修补",
    cost_str="10T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：将手牌抽至6张 获得1个额外的C槽和T槽 使所有友方单位获得+4HP。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="附魔台",
    cost_str="1D2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使你获得：每个出牌阶段首次开发时，再开发1张“附魔书”。
    targets_fn=target_none,
    effect_fn=_fumota_strategy,
)

register_card(
    name="幸运方块",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张离散金卡单位。
    targets_fn=target_none,
    effect_fn=lambda p, t, g, extras=None: g.develop_card(p, [c for c in DEFAULT_REGISTRY.all_cards() if c.pack == Pack.DISCRETE and c.rarity == Rarity.GOLD and c.card_type == CardType.MINION]),
)

register_card(
    name="砍伐！",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张花费不大于3的非敌对生物单位。将1张“掘进！“加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="掘进！",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张花费不小于4的非友好生物单位 使其具有迅捷。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="探索",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：将1张“丛林神殿“或”沙漠神殿“加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="丛林神殿",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抽2张策略 使其获得-1T花费。
    targets_fn=target_none,
    effect_fn=_conglin_shendian_strategy,
)

register_card(
    name="沙漠神殿",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抽2张单位 使其获得+1/2。
    targets_fn=target_none,
    effect_fn=_shamo_shendian_strategy,
)

register_card(
    name="金苹果",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：使1个单位获得+1/2，或使你获得+4HP。若指向僵尸村民，两项都触发。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="战利品",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：触发1个单位的亡语。若是敌方单位，再抹除其亡语。
    targets_fn=target_none,
    effect_fn=_zhanlipin_strategy,
)

register_card(
    name="铁砧",
    cost_str="3I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：选择并弃掉1张附魔书，将2张复制加入手牌。然后若你有铁锭，抽1张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="冶炼",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：移除所有矿物，将3个花费之和等于移除矿物的打出总和的非生命单位加入战场。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="脆弱同盟",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：消灭1个友方单位，将2张具有迅捷的“恶魂“加入战场，回合结束时，将其移除。
    targets_fn=target_friendly_minions,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="一日八秋",
    cost_str="4G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抽3张牌，然后若场上有不少于4个友方地狱生物单位，跳过对方的下一个抽牌 阶段。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="整装上阵",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：使所有离散单位获得+1/1，或所有离散单位获得+1HP和+1坚韧等级。 若你本回合此前未部署单位，两项都触发。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="耕殖",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张友好单位，抽1张牌。此前你每使用过1张“耕殖”，获得-1T花费。
    targets_fn=target_none,
    effect_fn=_gengzhi_strategy,
)

register_card(
    name="挖三填一",
    cost_str="1I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：移除1个单位。下个抽牌阶段，将其返回战场。其所有者抽1张牌。
    targets_fn=target_hand_minions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    effect_fn=_mingmingpai_strategy,
)

register_card(
    name="垂直竖井",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：抽1张牌，将一张“垂直竖井”加入对方手牌，使其花费和抽牌数+1 或 受到5点伤 害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="盘曲矿道",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抽2张牌，将其中1张复制洗入卡组。
    targets_fn=target_none,
    effect_fn=_panqukuandao_strategy,
)

register_card(
    name="鱼骨挖掘",
    cost_str="1D2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张攻击力不大于4的非友好单位，将其复制加入战场。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="迷失",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：移除1个单位，将其2张复制置入其所有者卡组顶。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="蛀蚀",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对方抽1张牌，失去与此牌花费相同的T点。若场上有蠹虫，再弃掉此牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="遗弃",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：将1个单位的HP设为1。
    targets_fn=target_any_minion,
    effect_fn=_yiqi_strategy,
)

register_card(
    name="复兴",
    cost_str="2D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使你获得：你不因抽牌而获得手牌时，将其复制加入手牌，使其花费+1。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="高山",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对方随机弃1张牌，将1张“铁锭“置入对方卡组顶。
    targets_fn=target_none,
    effect_fn=_gaoshan_strategy,
)

register_card(
    name="恶地",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对所有花费不大于3的单位造成3点伤害。
    targets_fn=target_none,
    effect_fn=_erdi_strategy,
)

register_card(
    name="雨林",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个单位获得亡语：随机消灭1个距离不大于3的敌方单位。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="雪原",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对1行单位造成等同于此行单位数的伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="火药",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：将1张“TNT”或1张“复制技术”加入手牌。
    targets_fn=target_none,
    effect_fn=_huoyao_strategy,
)

register_card(
    name="TNT",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对一个目标造成2点伤害。抽1张牌。
    targets_fn=target_none,
    effect_fn=_tnt_strategy,
)

register_card(
    name="复制技术",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抉择：将1张“轰击”或1张“制导技术”加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="轰击",
    cost_str="0T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：消灭1个受伤单位 将1张“TNT炮“加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="制导技术",
    cost_str="8T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：抉择：将1张“矢量炮“或1张”珍珠塔“加入手牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="珍珠塔",
    cost_str="0T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    is_token=True,
    # 效果描述：开发4张卡组中的牌 将其花费设为4T。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="矢量炮",
    cost_str="12T",
    card_type=CardType.MINION,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=12,
    health=12,
    keywords={"绝缘": True, "串击": True, "穿刺": True, "坚韧": 2},
    hidden_keywords={},
    is_token=True,
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="实体挤压",
    cost_str="2I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：指向1个单位，使其下一个出牌阶段开始时受到4点伤害并获得眩晕。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="C418",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对方手牌具有+2花费，直到下一个出牌阶段结束。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="红石粉",
    cost_str="1I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个非生命单位具有协同。抽1张牌。
    targets_fn=target_none,
    effect_fn=_hongshifen_strategy,
)

register_card(
    name="禁人书",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个单位及其相邻单位获得眩晕。
    targets_fn=target_any_minion,
    effect_fn=_jinrenshu_strategy,
)

register_card(
    name="焰火之星",
    cost_str="1D1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对1个单位造成6点伤害，溢出伤害随机分配至所有敌方目标。
    targets_fn=target_any_minion,
    effect_fn=lambda p, t, g, extras=None: (t.health_change(-6) if hasattr(t, "health_change") else (t.take_damage(6) if hasattr(t, "take_damage") else False) or True),
)

register_card(
    name="金西瓜片",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个单位获得：回合开始：获得+1/1。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="烟花鞘翅",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：将卡组顶的1张迅捷单位加入战场。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="紫颂果",
    cost_str="1I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抽2张牌。回合结束时，将其弃掉。
    targets_fn=target_none,
    effect_fn=_zisongguo_strategy,
)

register_card(
    name="雷暴",
    cost_str="7T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：随机消灭2个敌方单位。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="阴雨",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对1个非高地单位造成2点伤害，将其攻击力设为0直到回合结束。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="暗夜",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张离散迅捷单位。然后若你拥有不小于4个T点，对所有敌方目标造成1点 伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="破袭",
    cost_str="5T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个友方单位与1个攻击力最低的敌方单位对战。若将其消灭，获得+1HP并重 复此流程。
    targets_fn=target_friendly_minions,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="火灾",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：你和对手轮流抽牌至手牌数量为7张，下回合开始时弃掉本次抽到的牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="遗迹机关",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：将2张“绊线钩”加入战场。然后若场上有不多于3个“绊线钩“，对所有目标造成1 点伤害。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="临界点",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：开发1张非生命单位，使其具有“受到伤害前，每有1个友方“绊线钩“与之同行或 同列，对1个随机敌方目标造成1次1点伤害。“
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="药水箭",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个单位获得+1/2，抽1张牌。若指向非生命单位，再使所有友方非生命单位 获得+2HP。
    targets_fn=target_any_minion,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="熔岩",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抉择：对所有后排单位造成4点伤害 或 对对手造成6点伤害。
    targets_fn=target_enemy_player,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="充能铁轨",
    cost_str="1G",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    keywords={"回响": 2},
    hidden_keywords={},
    # 效果描述：移动1个陆地单位。若是友方单位，抽1张牌。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="门船穿梭",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个友方单位返回手牌，将其花费设为1I直到回合结束。然后若其上回合在场 上，使其部署时具有迅捷。
    targets_fn=target_friendly_minions,
    effect_fn=lambda p, t, g, extras=None: return_to_hand(t, g, p),
)

register_card(
    name="怪物猎人",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：使1个友方生物单位+1/3，然后与1个敌方单位对战。
    targets_fn=target_friendly_minions,
    extra_targeting_stages=[(target_enemy_minions, 1, False)],
    effect_fn=_guaiwulieren_strategy,
)

register_card(
    name="劫掠",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：消灭1个花费不大于3T的单位。若其处于协同，从对方卡组顶抽1张牌。
    targets_fn=target_none,
    effect_fn=_jielue_strategy,
)

register_card(
    name="命名牌",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：选择1张手牌中的单位，使场上的1个单位获得“也算作是本单位”。抽1张牌。
    targets_fn=target_hand_minions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    effect_fn=_mingmingpai_strategy,
)

register_card(
    name="调试棒",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：抽1张策略，将其展示并获得-1T花费和“抽1张策略，将其展示并获得-1T花费”
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="保卫要塞",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：将6张“蠹虫”洗入卡组。
    targets_fn=target_none,
    effect_fn=_baoweiyaosai_strategy,
)

register_card(
    name="村庄英雄",
    cost_str="1D",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：对1个单位及其相邻单位造成2点伤害。若有单位被消灭，将1张“村庄英雄”洗入 卡组。
    targets_fn=target_any_minion,
    effect_fn=_cunzhuangyingxiong_strategy,
)

register_card(
    name="虫蚀石头",
    cost_str="2I",
    card_type=CardType.STRATEGY,
    pack=Pack.DISCRETE,
    rarity=Rarity.IRON,
    immersion_level=1,
    hidden_keywords={},
    # 效果描述：移除对方卡组顶的2张牌，将2张“蠹虫”置入对方卡组顶。
    targets_fn=target_none,
    effect_fn=_chongshishitou_strategy,
)
