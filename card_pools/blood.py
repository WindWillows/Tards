# 自动生成的卡包定义文件
# 由 translate_packs.py 翻译生成

from tards import register_card, CardType, Pack, Rarity, DEFAULT_REGISTRY
from tards.targets import target_friendly_positions, target_none, target_any_minion, target_enemy_minions, target_enemy_player, target_self, target_friendly_minions
from tards.auto_effects import move_enemy_to_friendly, swap_units, return_to_hand
from .blood_effects import *

# Pack: BLOOD

register_card(
    name="保卫者",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    keywords={"协同": True},
    tags=['生物', '陆生'],
    # 效果描述：你受到伤害时，本异象获得+1/1。
    targets_fn=target_friendly_positions,
    special_fn=_baoweizhe_special,
)

register_card(
    name="流明",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    tags=['生物', '陆生'],
    # 效果描述：部署：至多消耗6S，每消耗2S，随机将1张精灵异象加入战场。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="“礼堂“",
    cost_str="3T2S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=8,
    tags=['生物', '陆生'],
    # 效果描述：双方打出手牌时，对所有目标造成1点伤害。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="独脚大盗",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    tags=['生物', '陆生'],
    # 效果描述：部署：抽取对方卡组顶的1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="显影室",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=6,
    tags=['生物', '陆生'],
    # 效果描述：回合开始：将1个“溴化银”加入本异象前方。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="溴化银",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：攻击后，消灭本异象。 亡语：将1张“胶片”加入对方手牌。
    targets_fn=target_friendly_positions,
    special_fn=_xiuhuayin_special,
)

register_card(
    name="胶片",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：抉择：对你造成1点伤害 或 移除卡组顶的1张牌。
    targets_fn=target_none,
    extra_targeting_stages=[(_jiaopian_choice, 1, False)],
    effect_fn=_jiaopian_effect,
)

register_card(
    name="Bishop",
    cost_str="3T3S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    tags=['生物', '陆生'],
    # 效果描述：回合结束：场上每有1个具有恐惧的异象，你获得1点HP。
    targets_fn=target_friendly_positions,
    special_fn=_bishop_special,
)

register_card(
    name="死灵法师",
    cost_str="5T3S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=6,
    tags=['生物', '陆生'],
    # 效果描述：敌方异象被消灭时，将1个“亡灵“加入其原位。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="亡灵",
    cost_str="1T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=2,
    keywords={"恐惧": True, "协同": True},
    tags=['生物', '陆生'],
    # 效果描述：无法被异象选中。
    targets_fn=target_friendly_positions,
    special_fn=_wangling_special,
)

register_card(
    name="天籁人偶",
    cost_str="3T1S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    keywords={"两栖": True},
    tags=['两栖', '生物'],
    # 效果描述：受到伤害时，你获得等量HP。
    targets_fn=target_friendly_positions,
    special_fn=_tianlairenou_special,
)

register_card(
    name="巫毒娃娃",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    keywords={"坚韧": 1},
    tags=['生物', '陆生'],
    # 效果描述：你每受到1点伤害，获得1S。
    targets_fn=target_friendly_positions,
    special_fn=_wuduwawa_special,
)

register_card(
    name="云君",
    cost_str="6T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"迅捷": True},
    tags=['生物', '陆生'],
    # 效果描述：攻击时，改为对攻击力最高的敌方异象造成等量伤害。 部署：攻击1次。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="无穷小量",
    cost_str="6T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    keywords={"坚韧": 1},
    tags=['生物', '陆生'],
    # 效果描述：部署：消灭1个受伤异象。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="雷金纳德",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    keywords={"协同": True, "尖刺": 1},
    tags=['生物', '陆生'],
    # 效果描述：HP不小于4时，具有“你受到伤害时，改为由本异象承受。” 部署：每有1个敌方异象，获得1次+1HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="翼龙",
    cost_str="9T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=5,
    health=3,
    keywords={"迅捷": True, "先攻": 1},
    tags=['生物', '陆生'],
    # 效果描述：你每受到1次伤害，获得-1T花费。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="指尖方寸",
    cost_str="5T2S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=4,
    tags=['生物', '陆生'],
    # 效果描述：部署：将1个异象返回其所有者手牌，其所有者抽1张牌。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=_zhijianfangcun_special,
)

register_card(
    name="环丁二烯",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=2,
    keywords={"迅捷": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：使敌方部署的下一个异象获得恐惧。
    targets_fn=target_friendly_positions,
    special_fn=_huanderxixi_special,
)

register_card(
    name="铁心",
    cost_str="3T2S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"迅捷": True},
    tags=['生物', '陆生'],
    # 效果描述：部署：将1张“环丁二烯”和1张“配体”加入手牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="配体",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    tags=['生物', '陆生'],
    is_token=True,
    # 效果描述：场上每有1个具有恐惧的异象 使1个纯净异象获得+1/1。
    targets_fn=_peiti_targets,
    effect_fn=_peiti_effect,
)

register_card(
    name="阿波罗之卫",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['生物', '陆生'],
    # 效果描述：你的随机效果改为指向，如可能。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="炸弹人",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['生物', '陆生'],
    # 效果描述：被弃掉时：对方随机弃1张牌。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="食梦貘",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=0,
    health=3,
    tags=['生物', '陆生'],
    # 效果描述：攻击力不大于4时，具有迅捷。 部署：选择并弃1张牌，获得等同于其花费的攻击力。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="不动点",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=6,
    keywords={"亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：部署：所有友方异象攻击1次本异象。 亡语：所有对其造成过伤害的异象获得+1/1。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="锯片",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=4,
    tags=['生物', '陆生'],
    # 效果描述：部署：对1个异象和你造成3点伤害。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="竹心",
    cost_str="4T3S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=3,
    keywords={"协同": True, "亡语": True},
    tags=['生物', '陆生'],
    # 效果描述：亡语：随机消灭1个处于协同的敌方异象。
    targets_fn=target_friendly_positions,
    special_fn=_zhuxin_special,
)

register_card(
    name="宣辰",
    cost_str="4T2S",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=4,
    keywords={"迅捷": True, "协同": True},
    tags=['生物', '陆生'],
    # 效果描述：部署：展示卡组顶的3张牌，将其中1张置入手牌。若其折算花费不大于5，你获 得等量血契。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="硫氰化钾",
    cost_str="3T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=2,
    health=3,
    tags=['生物', '陆生'],
    # 效果描述：部署：使1个异象获得恐惧。若其已具有恐惧，将其HP设为1点。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=_liuqinghuajia_special,
)

register_card(
    name="三氟化氯",
    cost_str="4T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=3,
    health=3,
    tags=['生物', '陆生'],
    # 效果描述：场上有异象具有恐惧时，无法被异象指向。 回合开始：随机使1个敌方异象具有恐惧。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="二硫化碳",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=1,
    tags=['生物', '陆生'],
    # 效果描述：部署：对1个异象造成1点伤害，将其冰冻。
    targets_fn=target_friendly_positions,
    extra_targeting_stages=[(target_any_minion, 1, False)],
    special_fn=_erliuhuatan_special,
)

register_card(
    name="乙烯",
    cost_str="2T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=1,
    health=2,
    tags=['生物', '陆生'],
    # 效果描述：部署：还原一个异象的HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="占位符5",
    cost_str="8T",
    card_type=CardType.MINION,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    attack=4,
    health=7,
    keywords={"两栖": True},
    tags=['两栖', '生物'],
    # 效果描述：手牌不因被使用而被移出手牌区时，本异象获得-2T花费。 抽取：选择1张手牌，将其洗入卡组。你获得等同于此牌花费的HP。
    targets_fn=target_friendly_positions,
    special_fn=None,  # TODO: 实现部署/回合效果
)

register_card(
    name="双生匕首",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：抽1张牌，获得1S，对1个异象和你造成1点伤害。
    targets_fn=target_any_minion,
    effect_fn=_shuangsheng_bishou_effect,
)

register_card(
    name="战争即和平",
    cost_str="3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对方抽2张牌，然后若对方手牌数不小于5，你获得+6HP。
    targets_fn=target_none,
    effect_fn=_zhanzheng_heping_effect,
)

register_card(
    name="自由即奴役",
    cost_str="2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对1个异象造成1点伤害。若其在本回合离开战场，将其回响加入手牌。
    targets_fn=target_any_minion,
    effect_fn=_ziyou_effect,
)

register_card(
    name="无知即力量",
    cost_str="1S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将上一个被消灭的异象的复制洗入卡组。
    targets_fn=target_none,
    effect_fn=_wuzhi_effect,
)

register_card(
    name="献出心脏",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对所有异象造成2点伤害。每消灭1个异象，获得2S。
    targets_fn=target_none,
    effect_fn=_xianchu_xinzang_effect,
)

register_card(
    name="己所不欲 己所不欲 勿施于人",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：随机将1张对方手牌转换为“己所不欲，勿施于人“，使其具有+2T花费，直到回合 结束。
    targets_fn=target_none,
    effect_fn=_jisuobuyu_effect,
)

register_card(
    name="永恒奴役",
    cost_str="2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将场上1个具有恐惧的异象的复制加入手牌。
    targets_fn=_yongheng_targets,
    effect_fn=_yongheng_effect,
)

register_card(
    name="碳酸亚铁",
    cost_str="2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：获得等同于你在本出牌阶段失去的HP。
    targets_fn=target_none,
    effect_fn=_tansuanya_tie_effect,
)

register_card(
    name="胶卷",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将1张“胶片”加入对方手牌。抽1张牌。
    targets_fn=target_none,
    effect_fn=_jiaojuan_effect,
)

register_card(
    name="赴死之时",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭所有攻击力最高的异象。你拉闸。
    targets_fn=target_none,
    effect_fn=_fusi_effect,
)

register_card(
    name="恐惧植入",
    cost_str="2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使1个异象获得恐惧。抽1张牌。
    targets_fn=target_any_minion,
    effect_fn=_kongju_zhi_effect,
)

register_card(
    name="重影",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使对方手牌中的“胶片”数量翻倍。所有“胶片”具有+1T花费，直到回合结束。
    targets_fn=target_none,
    effect_fn=_zhongying_effect,
)

register_card(
    name="恐惧震慑",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：冰冻所有具有恐惧的异象，对其造成1点伤害。
    targets_fn=target_none,
    effect_fn=_kongju_zhengshe_effect,
)

register_card(
    name="查获书籍",
    cost_str="2T2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：随机将1张对方手牌洗入卡组。抽1张牌。
    targets_fn=target_none,
    effect_fn=_chahuo_shuji_effect,
)

register_card(
    name="无间地狱",
    cost_str="4T2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对所有具有恐惧的敌方异象造成等同于场上具有恐惧的异象数的伤害。
    targets_fn=target_none,
    effect_fn=_wujiandi_yu_effect,
)

register_card(
    name="王翼弃兵",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，消灭1个折算花费不大于此牌的异象。
    targets_fn=_wangyi_targets,
    effect_fn=_wangyi_effect,
)

register_card(
    name="深渊",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：抽2张牌。被弃掉时：抽2张牌。
    targets_fn=target_none,
    effect_fn=_shenyuan_effect,
)

register_card(
    name="鱼死网破",
    cost_str="5S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择并弃1张牌，对方随机弃2张牌。
    targets_fn=target_none,
    effect_fn=_yusiwangpo_effect,
)

register_card(
    name="过曝！",
    cost_str="10S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将2张"胶片"加入对方手牌，对所有异象造成等同于对方手中"胶片"数目的伤害。 对方手中每有1张牌，具有-1S花费。
    targets_fn=target_none,
    effect_fn=_guobao_effect,
    cost_modifier=_guobao_cost_modifier,
)

register_card(
    name="血溅白练",
    cost_str="3T6S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：冰冻所有敌方异象。若这是本回合双方使用的第3张策略，对所有敌方异象造成3 点伤害。
    targets_fn=target_none,
    effect_fn=_xuejian_bailian_effect,
)

register_card(
    name="狭间",
    cost_str="3T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将1个异象返回其所有者手牌。冰冻相邻两列的敌方异象。
    targets_fn=target_any_minion,
    effect_fn=_xiajian_effect,
)

register_card(
    name="审判前夕",
    cost_str="1T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：选择手牌中的1张异象，使其花费-2T。你失去1个T槽。
    targets_fn=target_none,
    effect_fn=_shenpan_qianxi_effect,
)

register_card(
    name="管窥",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：开发1张纯净异象。若场上有友方纯净异象，再开发1张“时刻”。
    targets_fn=target_none,
    effect_fn=None,  # TODO: 实现效果
)

register_card(
    name="血渍怀表",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对局开始时，将其置入卡组顶。 对你造成3点伤害，对方随机弃1张牌。将1张"钝锈指针"洗入卡组。
    targets_fn=target_none,
    effect_fn=_xuezhi_huaibiao_effect,
    on_game_start=_xuezhi_huaibiao_game_start,
)

register_card(
    name="钝锈指针",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对你造成3点伤害，本轮跳过结算阶段。将1张"含垢齿轮"洗入卡组。
    targets_fn=target_none,
    effect_fn=_dunxiu_zhizhen_effect,
)

register_card(
    name="含垢齿轮",
    cost_str="6T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对你造成3点伤害，你获得"获得血契时，改为获得双倍"。
    targets_fn=target_none,
    effect_fn=_hangou_chilun_effect,
)

register_card(
    name="天下无双",
    cost_str="1T2S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：随机对1个敌方异象造成1点伤害。若场上有敌方异象的HP为偶数，重复此操作。
    targets_fn=target_enemy_minions,
    effect_fn=_tianxiawushuang_effect,
)

register_card(
    name="巍巍欲坠",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：对1个高地异象造成6点伤害。若被消灭，将其回响加入手牌。
    targets_fn=target_highland_minion,
    effect_fn=_weiwei_yuzhui_effect,
)

register_card(
    name="占位符1",
    cost_str="4T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：消灭场上攻击力唯一最高的敌方异象。 抽取：若可能，消耗1S，对对手造成2点伤害。
    targets_fn=target_none,
    effect_fn=_zhanweifu1_effect,
    hidden_keywords={"抽取": _zhanweifu1_draw_trigger},
)

register_card(
    name="占位符2",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：使1个异象及其相邻异象获得恐惧。 抽取：对所有具有恐惧的异象造成2点伤害。
    targets_fn=target_any_minion,
    effect_fn=_zhanweifu2_effect,
    hidden_keywords={"抽取": _zhanweifu2_draw_trigger},
)

register_card(
    name="占位符3",
    cost_str="2T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：抽2张牌。选择1张手牌，将其置入卡组顶。
    targets_fn=target_none,
    effect_fn=_zhanweifu3_effect,
)

register_card(
    name="占位符4",
    cost_str="3T",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    # 效果描述：将所有手牌洗入卡组，抽取等量的牌。 抽取：抽1张具有抽取效果的牌。
    targets_fn=target_none,
    effect_fn=_zhanweifu4_effect,
    hidden_keywords={"抽取": _zhanweifu4_draw_trigger},
)

register_card(
    name="侵晨",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：对1个异象造成3点伤害。抽1张牌。
    targets_fn=target_any_minion,
    effect_fn=_qinchen_effect,
)

register_card(
    name="隅中",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：你获得+4HP。抽1张牌。
    targets_fn=target_none,
    effect_fn=_yuzhong_effect,
)

register_card(
    name="亭午",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：抽2张牌。
    targets_fn=target_none,
    effect_fn=_tingwu_effect,
)

register_card(
    name="薄暮",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：抽1张牌。下个抽牌阶段，对方无法抽牌。
    targets_fn=target_none,
    effect_fn=_bomu_effect,
)

register_card(
    name="人定",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：冰冻1个异象及其相邻的1个异象。抽1张牌。
    targets_fn=target_none,
    effect_fn=_rending_effect,
)

register_card(
    name="昧旦",
    cost_str="1T3S",
    card_type=CardType.STRATEGY,
    pack=Pack.BLOOD,
    rarity=Rarity.IRON,
    immersion_level=1,
    is_moment=True,
    # 效果描述：将场上攻击力最高的1个异象返回其所有者手牌。抽1张牌。
    targets_fn=target_none,
    effect_fn=_meidan_effect,
)
