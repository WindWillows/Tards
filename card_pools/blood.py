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

def _jiaopian_choice(player, board):
    """胶片：抉择。"""
    return ["造成1点伤害", "移除卡组顶1张"]




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
    special_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
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

def _peiti_targets(player, board):
    """配体：选择友方纯净异象。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.owner == player and "纯净" in getattr(m, "tags", []) and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result


def _peiti_effect(player, target, game, extras=None):
    """配体：场上每有1个恐惧异象，使1个纯净异象+1/+1。"""
    from tards.cards import Minion

    # 统计场上恐惧异象数量
    fear_count = 0
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            fear_count += 1

    if fear_count == 0:
        print("  配体：场上没有恐惧异象")
        return True

    if not isinstance(target, Minion) or not target.is_alive():
        print("  配体：目标不合法")
        return False

    target.gain_attack(fear_count, permanent=True)
    target.gain_health_bonus(fear_count, permanent=True)
    print(f"  配体：{target.name} +{fear_count}/+{fear_count}（场上{fear_count}个恐惧异象）")
    return True


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
    special_fn=lambda p, t, g, extras=None: (t.health_change(-1) if hasattr(t, "health_change") else (t.take_damage(1) if hasattr(t, "take_damage") else False) or True),
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
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)

def _zhanzheng_heping_effect(player, target, game, extras=None):
    """战争即和平：对方抽2张牌，若其手牌≥5，你获得+6HP。"""
    opponent = game.p2 if player == game.p1 else game.p1
    opponent.draw_card(2, game=game)
    print(f"  战争即和平：{opponent.name} 抽2张牌")

    if len(opponent.card_hand) >= 5:
        player.health_change(6)
        print(f"  战争即和平：{opponent.name} 手牌≥5，{player.name} 获得+6HP")
    else:
        print(f"  战争即和平：{opponent.name} 手牌{len(opponent.card_hand)}，不足5张")
    return True


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

def _ziyou_effect(player, target, game, extras=None):
    """自由即奴役：对异象造成1点伤害，若本回合离开战场，回响加入手牌。"""
    from card_pools.effect_utils import deal_damage_to_minion, create_echo_card
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  自由即奴役：目标不合法")
        return False

    deal_damage_to_minion(target, 1, game=game)
    print(f"  自由即奴役：{target.name} 受到1点伤害")

    tracked = target
    sc = getattr(tracked, "source_card", None)

    def _check():
        if not tracked.is_alive() and sc:
            echo = create_echo_card(sc, getattr(sc, "echo_level", 1))
            echo.owner = player
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(echo)
                print(f"  自由即奴役：{tracked.name} 离开战场，回响加入手牌")
            else:
                player.card_dis.append(echo)
                print(f"  自由即奴役：手牌已满，回响被弃置")
        else:
            print(f"  自由即奴役：{tracked.name} 仍存活，无回响")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": _check,
    })
    return True


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

def _wuzhi_effect(player, target, game, extras=None):
    """无知即力量：将上一个被消灭的异象的复制洗入卡组。"""
    import random
    from tards.cards import MinionCard

    death_entries = [e for e in getattr(game, "_state_log", []) if e.get("event") == "minion_death"]
    if not death_entries:
        print("  无知即力量：本对局无异象被消灭")
        return True

    last = death_entries[-1]
    minion = last.get("minion")
    sc = getattr(minion, "source_card", None)
    if not sc:
        print("  无知即力量：无法找到源卡")
        return True

    copy_card = MinionCard(
        name=sc.name,
        owner=player,
        cost=sc.cost.copy(),
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if sc.keywords else {},
    )
    copy_card.pack = getattr(sc, "pack", None)

    player.card_deck.append(copy_card)
    random.shuffle(player.card_deck)
    print(f"  无知即力量：{copy_card.name} 的复制洗入卡组")
    return True


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

def _xianchu_xinzang_effect(player, target, game, extras=None):
    """献出心脏：对所有异象造成2点伤害，每消灭1个获得2S。"""
    from card_pools.effect_utils import deal_damage_to_minion

    all_minions = []
    seen = set()
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and id(m) not in seen:
            all_minions.append(m)
            seen.add(id(m))

    killed = 0
    for m in all_minions:
        before_alive = m.is_alive()
        deal_damage_to_minion(m, 2, game=game)
        if before_alive and not m.is_alive():
            killed += 1

    if killed > 0:
        player.s_point += killed * 2
        print(f"  献出心脏：消灭 {killed} 个异象，获得 {killed * 2}S")
    else:
        print(f"  献出心脏：未消灭异象")
    return True


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

def _jisuobuyu_effect(player, target, game, extras=None):
    """己所不欲：随机将对方1张手牌转换为己所不欲（+2T直到回合结束）。"""
    import random
    opponent = game.p2 if player == game.p1 else game.p1

    if not opponent.card_hand:
        print("  己所不欲：对方手牌为空")
        return True

    original = random.choice(opponent.card_hand)
    opponent.card_hand.remove(original)

    # 创建新卡
    card_def = DEFAULT_REGISTRY.get("己所不欲 己所不欲 勿施于人")
    if not card_def:
        print("  己所不欲：找不到卡牌定义")
        opponent.card_hand.append(original)
        return False

    new_card = card_def.to_game_card(opponent)

    # 临时费用修正 +2T
    def _temp_cost_mod(card, cost):
        cost.t += 2

    new_card._card_cost_modifiers.append(_temp_cost_mod)

    opponent.card_hand.append(new_card)
    print(f"  己所不欲：{opponent.name} 的 [{original.name}] 被转换为 [{new_card.name}]（+2T）")

    # 回合结束时移除修正
    def _cleanup():
        if _temp_cost_mod in getattr(new_card, "_card_cost_modifiers", []):
            new_card._card_cost_modifiers.remove(_temp_cost_mod)
            print(f"  己所不欲：{new_card.name} 的+2T修正已移除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": _cleanup,
    })
    return True


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

def _yongheng_targets(player, board):
    """永恒奴役：选择场上具有恐惧的异象。"""
    result = []
    seen = set()
    for m in list(board.minion_place.values()) + list(board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False) and id(m) not in seen:
            result.append(m)
            seen.add(id(m))
    return result


def _yongheng_effect(player, target, game, extras=None):
    """永恒奴役：将恐惧异象的复制加入手牌。"""
    from card_pools.effect_utils import copy_card_to_hand
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  永恒奴役：目标不合法")
        return False

    sc = getattr(target, "source_card", None)
    if not sc:
        print("  永恒奴役：找不到源卡")
        return False

    copy_card_to_hand(sc, player, game=game)
    print(f"  永恒奴役：{sc.name} 的复制加入手牌")
    return True


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

def _tansuanya_tie_effect(player, target, game, extras=None):
    """碳酸亚铁：获得等同于本出牌阶段失去HP的治疗。"""
    phase = getattr(game, "PHASE_ACTION", "action")
    total_lost = sum(
        entry.get("amount", 0)
        for entry in getattr(game, "_state_log", [])
        if entry.get("event") == "health_lost"
        and entry.get("player") == player
        and entry.get("turn") == game.current_turn
        and entry.get("phase") == phase
    )

    if total_lost > 0:
        player.health_change(total_lost)
        print(f"  碳酸亚铁：{player.name} 本出牌阶段失去 {total_lost} HP，恢复 {total_lost} HP")
    else:
        print(f"  碳酸亚铁：{player.name} 本出牌阶段未失去HP")
    return True


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

def _jiaojuan_effect(player, target, game, extras=None):
    """胶卷：将1张胶片加入对方手牌，自己抽1张。"""
    opponent = game.p2 if player == game.p1 else game.p1
    film_def = DEFAULT_REGISTRY.get("胶片")
    if film_def:
        film = film_def.to_game_card(opponent)
        if len(opponent.card_hand) < opponent.card_hand_max:
            opponent.card_hand.append(film)
            print(f"  胶卷：胶片加入 {opponent.name} 手牌")
        else:
            opponent.card_dis.append(film)
            print(f"  胶卷：{opponent.name} 手牌已满，胶片被弃置")
    else:
        print("  胶卷：找不到胶片定义")

    player.draw_card(1, game=game)
    print(f"  胶卷：{player.name} 抽1张牌")
    return True


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

def _fusi_effect(player, target, game, extras=None):
    """赴死之时：消灭所有攻击力最高的异象，自己拉闸。"""
    from card_pools.effect_utils import destroy_minion

    all_minions = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m not in all_minions:
            all_minions.append(m)

    if not all_minions:
        print("  赴死之时：场上无异象")
        player.braked = True
        print(f"  赴死之时：{player.name} 拉闸")
        return True

    max_atk = max(m.current_attack for m in all_minions)
    victims = [m for m in all_minions if m.current_attack == max_atk]

    for m in victims:
        destroy_minion(m, game)
        print(f"  赴死之时：消灭攻击力最高的 {m.name}({max_atk})")

    player.braked = True
    print(f"  赴死之时：{player.name} 拉闸")
    return True


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

def _kongju_zhi_effect(player, target, game, extras=None):
    """恐惧植入：使1个异象获得恐惧，抽1张牌。"""
    from tards.cards import Minion

    if not isinstance(target, Minion) or not target.is_alive():
        print("  恐惧植入：目标不合法")
        return False

    target.keywords["恐惧"] = True
    target.recalculate()
    print(f"  恐惧植入：{target.name} 获得恐惧")

    player.draw_card(1, game=game)
    print(f"  恐惧植入：{player.name} 抽1张牌")
    return True


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

def _zhongying_effect(player, target, game, extras=None):
    """重影：对方胶片数量翻倍，所有胶片+1T直到回合结束。"""
    opponent = game.p2 if player == game.p1 else game.p1
    film_def = DEFAULT_REGISTRY.get("胶片")

    # 统计现有胶片
    existing_films = [c for c in opponent.card_hand if getattr(c, "name", None) == "胶片"]
    count = len(existing_films)

    if count > 0 and film_def:
        added = 0
        for _ in range(count):
            if len(opponent.card_hand) < opponent.card_hand_max:
                film = film_def.to_game_card(opponent)
                opponent.card_hand.append(film)
                added += 1
            else:
                break
        print(f"  重影：{opponent.name} 的胶片数量翻倍（+{added}张）")
    else:
        print(f"  重影：{opponent.name} 手牌中无胶片")

    # 给所有胶片+1T
    def _temp_cost_mod(card, cost):
        cost.t += 1

    all_films = [c for c in opponent.card_hand if getattr(c, "name", None) == "胶片"]
    for film in all_films:
        film._card_cost_modifiers.append(_temp_cost_mod)
    print(f"  重影：{len(all_films)} 张胶片+1T")

    # 回合结束时移除修正
    def _cleanup():
        for film in all_films:
            if _temp_cost_mod in getattr(film, "_card_cost_modifiers", []):
                film._card_cost_modifiers.remove(_temp_cost_mod)
        print("  重影：胶片+1T修正已移除")

    game._delayed_effects.append({
        "trigger": "turn_end",
        "turn": game.current_turn,
        "fn": _cleanup,
    })
    return True


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

def _kongju_zhengshe_effect(player, target, game, extras=None):
    """恐惧震慑：冰冻所有恐惧异象，对其造成1点伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion

    victims = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            victims.append(m)

    if not victims:
        print("  恐惧震慑：场上无恐惧异象")
        return True

    for m in victims:
        m.keywords["冰冻"] = True
        m.recalculate()
        deal_damage_to_minion(m, 1, game=game)
        print(f"  恐惧震慑：{m.name} 被冰冻并受到1点伤害")

    return True


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

def _chahuo_shuji_effect(player, target, game, extras=None):
    """查获书籍：随机将1张对方手牌洗入卡组，自己抽1张。"""
    import random
    opponent = game.p2 if player == game.p1 else game.p1

    if opponent.card_hand:
        card = random.choice(opponent.card_hand)
        opponent.card_hand.remove(card)
        opponent.card_deck.append(card)
        random.shuffle(opponent.card_deck)
        print(f"  查获书籍：{opponent.name} 的 [{card.name}] 被洗入卡组")
    else:
        print(f"  查获书籍：{opponent.name} 手牌为空")

    player.draw_card(1, game=game)
    print(f"  查获书籍：{player.name} 抽1张牌")
    return True


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

def _wujiandi_yu_effect(player, target, game, extras=None):
    """无间地狱：对所有恐惧敌方异象造成等同于场上恐惧异象数的伤害。"""
    from card_pools.effect_utils import deal_damage_to_minion

    # 统计场上恐惧异象数
    fear_count = 0
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False):
            fear_count += 1

    if fear_count == 0:
        print("  无间地狱：场上无恐惧异象")
        return True

    opponent = game.p2 if player == game.p1 else game.p1
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive() and m.keywords.get("恐惧", False) and m.owner == opponent:
            deal_damage_to_minion(m, fear_count, game=game)
            print(f"  无间地狱：{m.name} 受到 {fear_count} 点伤害")

    return True


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

def _wangyi_targets(player, board):
    """王翼弃兵：选择手牌中的一张牌弃掉。"""
    return player.card_hand


def _wangyi_effect(player, target, game, extras=None):
    """王翼弃兵：弃1张牌，消灭1个折算花费不大于此牌的异象。"""
    from card_pools.effect_utils import convert_cost_to_t, destroy_minion
    from tards.cards import Minion

    if target not in player.card_hand:
        print("  王翼弃兵：目标不在手牌中")
        return False

    player.card_hand.remove(target)
    player.card_dis.append(target)
    max_cost = convert_cost_to_t(target.cost)
    print(f"  王翼弃兵：弃掉 [{target.name}]，折算费用 {max_cost}T")

    # 筛选符合条件的异象
    candidates = []
    for m in list(game.board.minion_place.values()) + list(game.board.cell_underlay.values()):
        if m.is_alive():
            sc = getattr(m, "source_card", None)
            if sc and convert_cost_to_t(sc.cost) <= max_cost:
                candidates.append(m)

    if not candidates:
        print("  王翼弃兵：无符合条件的异象")
        return True

    options = [f"{i+1}. {m.name}({convert_cost_to_t(m.source_card.cost)}T)" for i, m in enumerate(candidates)]
    chosen = game.request_choice(player, options, title="王翼弃兵：选择要消灭的异象")
    if not chosen:
        print("  王翼弃兵：未选择目标")
        return True

    idx = int(chosen.split('.')[0]) - 1
    victim = candidates[idx]
    destroy_minion(victim, game)
    print(f"  王翼弃兵：消灭 {victim.name}")
    return True


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

def _shenyuan_effect(player, target, game, extras=None, card=None):
    """深渊：抽2张牌。被弃掉时：抽2张牌。

    利用新引擎的 Card.on() 注册卡实例级监听器，仅响应该实例自身的弃置事件。
    正常打出进入弃牌堆不会触发 EVENT_DISCARDED，因此不会误触发。
    """
    from tards.constants import EVENT_DISCARDED

    player.draw_card(2, game=game)
    print(f"  深渊：{player.name} 抽2张牌")

    if card is None:
        return True

    def on_discarded(event_data):
        discarded = event_data.get("card")
        if discarded is not card:
            return
        owner = getattr(discarded, "owner", None)
        if owner:
            owner.draw_card(2, game=game)
            print(f"  深渊：被弃掉时，{owner.name} 抽2张牌")
        # 触发后注销，避免重复响应
        card.off_all()

    card.on(EVENT_DISCARDED, on_discarded)
    return True


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

def _yusiwangpo_effect(player, target, game, extras=None, card=None):
    """鱼死网破：选择并弃1张自己的手牌，对方随机弃2张牌。

    规则确认：
    - 打出时卡已进入临时结算区，不在手牌中。
    - "如可能"原则：没有牌可弃就不弃。
    - 先弃自己的，再弃对方的。
    """
    import random

    # 先弃置自己的1张手牌
    if player.card_hand:
        options = [f"{i+1}. {c.name}" for i, c in enumerate(player.card_hand)]
        chosen = game.request_choice(player, options, "鱼死网破：选择弃1张手牌")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = player.card_hand[idx]
            player.discard_card(chosen_card, game, reason="effect")

    # 再弃置对方随机2张手牌
    opponent = game.p2 if player == game.p1 else game.p1
    if opponent.card_hand:
        discard_count = min(2, len(opponent.card_hand))
        to_discard = random.sample(opponent.card_hand, discard_count)
        for c in to_discard:
            opponent.discard_card(c, game, reason="effect")

    return True


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

def _guobao_cost_modifier(card, cost):
    """过曝！：对方手中每有1张牌，费用-1S。"""
    owner = getattr(card, "owner", None)
    if not owner:
        return
    game = getattr(getattr(owner, "board_ref", None), "game_ref", None)
    if not game:
        return
    opponent = game.p2 if owner == game.p1 else game.p1
    discount = len(opponent.card_hand)
    cost.s = max(0, cost.s - discount)


def _guobao_effect(player, target, game, extras=None, card=None):
    """过曝！：将2张胶片加入对方手牌，对所有异象造成等同于对方手中胶片数目的伤害。"""
    from tards.card_db import DEFAULT_REGISTRY
    from tards.constants import EVENT_DRAW, EVENT_DISCARDED, EVENT_MILLED

    opponent = game.p2 if player == game.p1 else game.p1

    # 将2张胶片加入对方手牌
    jiaopian_def = DEFAULT_REGISTRY.get("胶片")
    if jiaopian_def:
        for _ in range(2):
            jp = jiaopian_def.to_game_card(opponent)
            if len(opponent.card_hand) < opponent.card_hand_max:
                opponent.card_hand.append(jp)
                jp.move_to("hand", game)
                game.emit_event(EVENT_DRAW, player=opponent, card=jp)
                print(f"  过曝！：{jp.name} 加入 {opponent.name} 手牌")
            else:
                opponent.card_dis.append(jp)
                jp.move_to("discard", game)
                game.emit_event(EVENT_DISCARDED, player=opponent, card=jp, reason="mill")
                game.emit_event(EVENT_MILLED, player=opponent, card=jp)
                print(f"  过曝！：{opponent.name} 手牌已满，胶片被弃置")

    # 对所有异象造成等同于对方手中胶片数目的伤害（包含刚加入的）
    jiaopian_count = sum(1 for c in opponent.card_hand if getattr(c, "name", None) == "胶片")
    if jiaopian_count > 0:
        all_minions = list(game.board.minion_place.values())
        for m in all_minions:
            if m.is_alive():
                m.take_damage(jiaopian_count, source_type="strategy")
        print(f"  过曝！：对方手中有 {jiaopian_count} 张胶片，对所有异象造成 {jiaopian_count} 点伤害")
    else:
        print(f"  过曝！：对方手中没有胶片，不造成伤害")

    return True


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

def _xuejian_bailian_effect(player, target, game, extras=None, card=None):
    """血溅白练：冰冻所有敌方异象。若本回合第3张策略，对所有敌方异象造成3点伤害。"""
    opponent = game.p2 if player == game.p1 else game.p1

    # 冰冻所有敌方异象
    enemy_minions = [m for m in game.board.minion_place.values()
                     if m.is_alive() and m.owner == opponent]
    for m in enemy_minions:
        m.gain_keyword("冰冻", 1, permanent=True)
        print(f"  血溅白练：{m.name} 被冰冻")

    # 若这是本回合双方使用的第3张策略，造成额外伤害
    if getattr(game, "_strategies_played_this_turn", 0) == 3:
        for m in enemy_minions:
            if m.is_alive():
                m.take_damage(3, source_type="strategy")
        print(f"  血溅白练：本回合第3张策略，对所有敌方异象造成3点伤害")

    return True


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

def _xiajian_effect(player, target, game, extras=None, card=None):
    """狭间：将1个异象返回其所有者手牌。冰冻相邻两列的敌方异象。

    手牌满则爆掉（直接销毁，不进弃牌堆）。返回手牌不触发亡语。
    """
    from tards.cards import MinionCard

    if target is None or not hasattr(target, 'is_alive'):
        return False

    minion = target
    if not minion.is_alive():
        return False

    owner = minion.owner
    position = minion.position
    col = position[1] if isinstance(position, (list, tuple)) and len(position) >= 2 else 0

    # 1. 将异象从战场移除（remove_minion 不触发亡语）
    game.board.remove_minion(position)

    # 创建原卡复制
    sc = minion.source_card
    new_card = MinionCard(
        name=sc.name,
        owner=owner,
        cost=sc.cost,
        targets=sc.targets,
        attack=sc.attack,
        health=sc.health,
        special=getattr(sc, "special", None),
        keywords=dict(sc.keywords) if hasattr(sc, "keywords") else {},
    )

    # 手牌有空间则加入手牌，否则爆掉（直接销毁，不进弃牌堆）
    if len(owner.card_hand) < owner.card_hand_max:
        owner.card_hand.append(new_card)
        new_card.move_to("hand", game)
        print(f"  狭间：{minion.name} 返回 {owner.name} 手牌")
    else:
        print(f"  狭间：{minion.name} 返回手牌失败（手牌满），爆掉")

    # 2. 冰冻相邻两列的敌方异象（不包含目标所在列）
    adjacent_cols = []
    if col - 1 >= 0:
        adjacent_cols.append(col - 1)
    if col + 1 < 5:  # BOARD_SIZE
        adjacent_cols.append(col + 1)

    for m in game.board.minion_place.values():
        if m.is_alive() and m.owner != player:
            m_col = m.position[1] if isinstance(m.position, (list, tuple)) and len(m.position) >= 2 else 0
            if m_col in adjacent_cols:
                m.gain_keyword("冰冻", 1, permanent=True)
                print(f"  狭间：{m.name}（列 {m_col}）被冰冻")

    return True


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

def _shenpan_qianxi_effect(player, target, game, extras=None, card=None):
    """审判前夕：选择手牌中的1张异象，使其花费-2T。你失去1个T槽。

    费用减免为永久，可叠加。下限为0T。
    """
    from tards.cards import MinionCard

    # 筛选手牌中的异象卡
    minion_cards = [c for c in player.card_hand if isinstance(c, MinionCard)]
    if minion_cards:
        options = [f"{i+1}. {c.name}({c.cost})" for i, c in enumerate(minion_cards)]
        chosen = game.request_choice(player, options, "审判前夕：选择手牌中的1张异象")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = minion_cards[idx]

            def discount_fn(card, cost):
                cost.t = max(0, cost.t - 2)

            chosen_card._card_cost_modifiers.append(discount_fn)
            print(f"  审判前夕：{chosen_card.name} 的费用-2T")
        else:
            print("  审判前夕：未选择目标")
    else:
        print("  审判前夕：手牌中没有异象卡")

    # 无论是否选到目标，都失去1个T槽
    player.t_point_max_change(-1)
    print(f"  审判前夕：{player.name} 失去1个T槽")
    return True


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

def _xuezhi_huaibiao_game_start(player, game, card):
    """对局开始时：将血渍怀表置入卡组顶。"""
    if card in player.card_deck:
        player.card_deck.remove(card)
        player.card_deck.insert(0, card)
        print(f"  血渍怀表：{player.name} 将其置入卡组顶")


def _xuezhi_huaibiao_effect(player, target, game, extras=None, card=None):
    """血渍怀表：对你造成3点伤害，对方随机弃1张牌。将1张钝锈指针洗入卡组。"""
    import random

    # 对自己造成3点伤害（普通伤害，非流失生命）
    player.health_change(-3)
    print(f"  血渍怀表：{player.name} 受到3点伤害")

    # 对方随机弃1张手牌
    opponent = game.p2 if player == game.p1 else game.p1
    if opponent.card_hand:
        to_discard = random.choice(opponent.card_hand)
        opponent.discard_card(to_discard, game, reason="effect")

    # 将1张钝锈指针洗入卡组
    from tards.card_db import DEFAULT_REGISTRY
    pointer_def = DEFAULT_REGISTRY.get("钝锈指针")
    if pointer_def:
        new_card = pointer_def.to_game_card(player)
        player.card_deck.append(new_card)
        new_card.move_to("deck", game)
        random.shuffle(player.card_deck)
        print(f"  血渍怀表：1张钝锈指针洗入卡组")
    else:
        print(f"  血渍怀表：钝锈指针定义未找到")

    return True


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

def _dunxiu_zhizhen_effect(player, target, game, extras=None, card=None):
    """钝锈指针：对你造成3点伤害，本轮跳过结算阶段。将1张含垢齿轮洗入卡组。"""
    import random

    # 对自己造成3点伤害
    player.health_change(-3)
    print(f"  钝锈指针：{player.name} 受到3点伤害")

    # 跳过本轮结算阶段
    game._skip_resolve_phase = True
    print(f"  钝锈指针：本轮结算阶段将被跳过")

    # 将1张含垢齿轮洗入卡组
    from tards.card_db import DEFAULT_REGISTRY
    gear_def = DEFAULT_REGISTRY.get("含垢齿轮")
    if gear_def:
        new_card = gear_def.to_game_card(player)
        player.card_deck.append(new_card)
        new_card.move_to("deck", game)
        random.shuffle(player.card_deck)
        print(f"  钝锈指针：1张含垢齿轮洗入卡组")
    else:
        print(f"  钝锈指针：含垢齿轮定义未找到")

    return True


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

def _hangou_chilun_effect(player, target, game, extras=None, card=None):
    """含垢齿轮：对你造成3点伤害，获得'获得血契时，改为获得双倍'。"""
    player.health_change(-3)
    print(f"  含垢齿轮：{player.name} 受到3点伤害")

    setattr(player, "_double_blood_gain", True)
    print(f"  含垢齿轮：{player.name} 获得双倍血契")
    return True


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

def _tianxiawushuang_effect(player, target, game, extras=None, card=None):
    """天下无"双"：随机对1个敌方异象造成1点伤害。若场上有敌方异象的HP为偶数，重复此操作。"""
    import random

    opponent = game.p2 if player == game.p1 else game.p1

    while True:
        # 获取敌方存活异象
        enemy_minions = [m for m in game.board.minion_place.values()
                         if m.is_alive() and m.owner == opponent]
        if not enemy_minions:
            break

        # 随机选1个造成1点伤害
        victim = random.choice(enemy_minions)
        victim.take_damage(1, source_type="strategy")
        print(f"天下无双：{victim.name} 受到1点伤害")

        # 检查是否仍有敌方异象HP为偶数
        has_even_hp = any(
            m.is_alive() and m.health % 2 == 0
            for m in game.board.minion_place.values()
            if m.owner == opponent
        )
        if not has_even_hp:
            break

    return True


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

def target_highland_minion(player, board):
    """返回所有位于高地列（col=0）的异象。"""
    return [m for m in board.minion_place.values()
            if m.is_alive() and isinstance(m.position, (list, tuple)) and len(m.position) >= 2 and m.position[1] == 0]


def _weiwei_yuzhui_effect(player, target, game, extras=None, card=None):
    """巍巍欲坠：对1个高地异象造成6点伤害。若被消灭，将其回响加入手牌。"""
    from card_pools.effect_utils import create_echo_card
    from tards.cards import Minion

    if target is None or not isinstance(target, Minion) or not target.is_alive():
        return False

    # 验证目标在高地列
    if isinstance(target.position, (list, tuple)) and len(target.position) >= 2:
        if target.position[1] != 0:
            print("  巍巍欲坠：目标不在高地列")
            return False

    # 造成6点伤害
    target.take_damage(6, source_type="strategy")
    print(f"  巍巍欲坠：{target.name} 受到6点伤害")

    # 若被消灭，将其回响加入手牌
    if not target.is_alive():
        source_card = getattr(target, "source_card", None)
        if source_card:
            echo = create_echo_card(source_card, echo_level=1)
            echo.owner = player
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(echo)
                echo.move_to("hand", game)
                print(f"  巍巍欲坠：{echo.name} 的回响加入手牌")
            else:
                player.card_dis.append(echo)
                echo.move_to("discard", game)
                print(f"  巍巍欲坠：手牌已满，回响被弃置")

    return True


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

def _zhanweifu1_draw_trigger(player, game, card):
    """抽取：若可能，消耗1S，对对手造成2点伤害。"""
    if player.s_point >= 1:
        player.s_point -= 1
        opponent = game.p2 if player == game.p1 else game.p2
        opponent.health_change(-2)
        print(f"  {card.name} 抽取：{player.name} 消耗1S，{opponent.name} 受到2点伤害")
    else:
        print(f"  {card.name} 抽取：{player.name} S不足，无法造成伤害")


def _zhanweifu1_effect(player, target, game, extras=None, card=None):
    """占位符1：消灭场上攻击力唯一最高的敌方异象。"""
    opponent = game.p2 if player == game.p1 else game.p1
    enemy_minions = [m for m in game.board.minion_place.values()
                     if m.is_alive() and m.owner == opponent]

    if not enemy_minions:
        print("  占位符1：场上没有敌方异象")
        return True

    # 找出最高攻击力
    max_attack = max(m.attack for m in enemy_minions)
    highest = [m for m in enemy_minions if m.attack == max_attack]

    if len(highest) != 1:
        print(f"  占位符1：最高攻击力({max_attack})的敌方异象有{len(highest)}个，不唯一，无法消灭")
        return True

    victim = highest[0]
    victim.current_health = 0
    victim.minion_death()
    print(f"  占位符1：消灭 {victim.name}")
    return True


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

def _zhanweifu2_draw_trigger(player, game, card):
    """抽取：对所有具有恐惧的异象造成2点伤害。"""
    for m in game.board.minion_place.values():
        if m.is_alive() and m.keywords.get("恐惧", False):
            m.take_damage(2, source_type="strategy")
            print(f"  {card.name} 抽取：{m.name} 受到2点伤害")


def _zhanweifu2_effect(player, target, game, extras=None, card=None):
    """占位符2：使1个异象及其相邻异象获得恐惧。"""
    from tards.cards import Minion

    if target is None or not isinstance(target, Minion) or not target.is_alive():
        return False

    # 目标自身获得恐惧
    target.apply_fear()

    # 上下左右相邻的异象也获得恐惧
    r, c = target.position[0], target.position[1]
    adjacent_positions = []
    if r - 1 >= 0:
        adjacent_positions.append((r - 1, c))
    if r + 1 < 5:
        adjacent_positions.append((r + 1, c))
    if c - 1 >= 0:
        adjacent_positions.append((r, c - 1))
    if c + 1 < 5:
        adjacent_positions.append((r, c + 1))

    for pos in adjacent_positions:
        m = game.board.get_minion_at(pos)
        if m and m.is_alive():
            m.apply_fear()
            print(f"  占位符2：{m.name}（相邻）获得恐惧")

    return True


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

def _zhanweifu3_effect(player, target, game, extras=None, card=None):
    """占位符3：抽2张牌。选择1张手牌，将其置入卡组顶。"""
    player.draw_card(2, game=game)

    if player.card_hand:
        options = [f"{i+1}. {c.name}" for i, c in enumerate(player.card_hand)]
        chosen = game.request_choice(player, options, "占位符3：选择1张手牌置入卡组顶")
        if chosen:
            idx = int(chosen.split('.')[0]) - 1
            chosen_card = player.card_hand[idx]
            player.card_hand.remove(chosen_card)
            player.card_deck.insert(0, chosen_card)
            chosen_card.move_to("deck", game)
            print(f"  占位符3：{chosen_card.name} 被置入卡组顶")

    return True


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

def _zhanweifu4_draw_trigger(player, game, card):
    """抽取：抽1张具有抽取效果的牌。

    正确实现：将候选卡放到卡组顶，然后通过 draw_card 真正抽进手牌，
    由 draw_card 内部统一触发抽取效果。
    """
    import random
    candidates = [c for c in player.card_deck if getattr(c, "hidden_keywords", {}).get("抽取")]
    if candidates:
        chosen = random.choice(candidates)
        # 将选中的卡放到卡组顶，然后通过 draw_card 真正抽进手牌
        player.card_deck.remove(chosen)
        player.card_deck.insert(0, chosen)
        chosen.move_to("deck", game)
        print(f"  {card.name} 抽取：将 {chosen.name} 置入卡组顶")
        player.draw_card(1, game=game)
    else:
        print(f"  {card.name} 抽取：卡组中没有具有抽取效果的牌")


def _zhanweifu4_effect(player, target, game, extras=None, card=None):
    """占位符4：将所有手牌洗入卡组，抽取等量的牌。"""
    import random
    count = len(player.card_hand)
    # 将所有手牌洗入卡组
    while player.card_hand:
        c = player.card_hand.pop()
        player.card_deck.append(c)
        c.move_to("deck", game)
    random.shuffle(player.card_deck)
    print(f"  占位符4：{count}张手牌洗入卡组")

    # 抽取等量的牌
    player.draw_card(count, game=game)
    return True


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

def _qinchen_effect(player, target, game, extras=None, card=None):
    """侵晨：对1个异象造成3点伤害。抽1张牌。"""
    from tards.cards import Minion
    if target and isinstance(target, Minion) and target.is_alive():
        target.take_damage(3, source_type="strategy")
        print(f"  侵晨：{target.name} 受到3点伤害")
    player.draw_card(1, game=game)
    return True


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

def _yuzhong_effect(player, target, game, extras=None, card=None):
    """隅中：你获得+4HP。抽1张牌。"""
    player.health_change(4)
    print(f"  隅中：{player.name} 获得4点HP")
    player.draw_card(1, game=game)
    return True


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

def _tingwu_effect(player, target, game, extras=None, card=None):
    """亭午：抽2张牌。"""
    player.draw_card(2, game=game)
    return True


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
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
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
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
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
    effect_fn=lambda p, t, g, extras=None: (p.draw_card(1, game=g) or True),
)
