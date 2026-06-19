"""回归测试套件 — 已发现/已修复的 bug 固化于此。"""

from __future__ import annotations

from tards.cards import Strategy
from tards.constants import EVENT_CARD_ADDED_TO_HAND, EVENT_CARD_PLAYED, EVENT_PHASE_START
from tards.core.cost import Cost
from tests.assertions import (
    assert_board_empty,
    assert_event_count,
    assert_hand_contains,
    assert_hand_missing,
    assert_minion_exists,
    assert_minion_hp,
    assert_minion_keyword,
)
from tests.event_spy import EventSpy
from tests.harness import GameHarness


# =============================================================================
# 1. 显影室召唤溴化银
# =============================================================================

def test_xianyingshi_summons_xiuhuayin():
    """显影室：回合开始时在前方正确位置召唤溴化银。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("显影室", p1, (4, 2))
    assert_minion_exists(h.game, (4, 2), "显影室")

    h.resolve_phase(p1, p2)
    assert_minion_exists(h.game, (3, 2), "溴化银")
    assert_minion_keyword(h.game, (3, 2), "休眠", 1)


# =============================================================================
# 2. 血溅白练条件判定
# =============================================================================



# =============================================================================
# 3. 巫毒娃娃延迟触发
# =============================================================================



# =============================================================================
# 4. 天籁人偶伤害分摊
# =============================================================================



# =============================================================================
# 5. 溴化银亡语给对手手牌
# =============================================================================



# =============================================================================
# 6. 亡灵部署与攻击
# =============================================================================

def test_wangling_deploy_and_attack():
    """亡灵：作为 token 正确部署并能参与攻击结算。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("亡灵", p1, (4, 2))
    assert_minion_exists(h.game, (4, 2), "亡灵")

    # 推进到结算阶段，检查不报错（亡灵有亡语关键词，不应崩溃）
    h.resolve_phase(p1, p2)


# =============================================================================
# 7. 流明随机召唤
# =============================================================================

def test_liuming_random_summon():
    """流明：消耗 S 点正确召唤精灵异象到战场。"""
    h = GameHarness()
    p1, p2 = h.players

    p1.s_point = 6
    h.give_hand(p1, "流明")
    h.play_minion(p1, "流明", (4, 0))
    # 消耗 6S 应召唤 3 个精灵 token（随机位置）
    elves = [m for m in h.game.board.minion_place.values()
             if "精灵" in getattr(m, "tags", [])]
    assert len(elves) == 3, f"期望 3 个精灵，实际 {len(elves)}"


# =============================================================================
# 8. 独脚大盗抽取
# =============================================================================

def test_dujiaodadao_draws_opponent_top():
    """独脚大盗：部署时抽取对方卡组顶的 1 张牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p2 牌库塞一张可识别的牌
    from card_pools.effect_utils import create_card_by_name
    card = create_card_by_name("书架", p2)
    p2.card_deck.append(card)

    h.give_hand(p1, "独脚大盗")
    h.play_minion(p1, "独脚大盗", (4, 0))

    # p1 手牌应有独脚大盗部署后得到的牌
    assert len(p1.card_hand) == 1
    assert p1.card_hand[0].name == "书架"
    assert len(p2.card_deck) == 0


# =============================================================================
# 9. 死灵法师复活
# =============================================================================



# =============================================================================
# 10. Bishop 恐惧回血
# =============================================================================



# =============================================================================
# 11. 钝锈指针跳过结算阶段
# =============================================================================

def test_dunxiu_zhizhen_skips_resolve():
    """钝锈指针：打出后本回合跳过结算阶段。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "钝锈指针")
    h.play_strategy(p1, "钝锈指针")
    assert h.game._skip_resolve_phase is True


# =============================================================================
# 12. 含垢齿轮双倍血契
# =============================================================================

def test_hangou_chilun_double_blood():
    """含垢齿轮：打出后本回合献祭产血翻倍。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "含垢齿轮")
    h.play_strategy(p1, "含垢齿轮")
    assert p1._double_blood_gain is True


# =============================================================================
# 13. 钝锈指针衍生卡到手牌
# =============================================================================



# =============================================================================
# 14. 血契 1 级沉浸度流失生命
# =============================================================================



# =============================================================================
# 15. 钝锈指针跳过结算后下回合恢复
# =============================================================================



# =============================================================================
# 16. 血渍怀表 on_game_start 置顶
# =============================================================================



# =============================================================================
# 17. 萤石减伤与回血
# =============================================================================



# =============================================================================
# 18. 钝锈指针不阻止 EVENT_TURN_START
# =============================================================================

def test_dunxiu_zhizhen_does_not_block_turn_start():
    """钝锈指针：仅跳过 resolve_phase，不阻止 turn_start 事件。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "钝锈指针")
    h.play_strategy(p1, "钝锈指针")

    with EventSpy(h.game) as spy:
        h.start_turn(p1, p2)
        spy.assert_fired("turn_start")


# =============================================================================
# 19. 保卫者受伤成长
# =============================================================================



# =============================================================================
# 20. 亡的左轮费用修正
# =============================================================================



# =============================================================================
# 21. 钝锈指针衍生卡有指针关键词
# =============================================================================



# =============================================================================
# 22. 血契 2 级受到 >=3 伤害触发
# =============================================================================

def test_blood_immersion_2_damage_trigger():
    """血契 2 级：受到单次 >=3 伤害时获得 3S。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.data.card_db import Pack
    p1.immersion_points[Pack.BLOOD] = 2

    p1.s_point = 0
    p1.health_change(-5)
    assert p1.s_point == 3, f"期望 3 S，实际 {p1.s_point}"


# =============================================================================
# 23. 冥刻 1 级开局 6 张松鼠
# =============================================================================



# =============================================================================
# 24. 冥刻 2 级兑换松鼠
# =============================================================================



def hand_contains_name(player, name):
    return any(c.name == name for c in player.card_hand)


# =============================================================================
# 25. 离散 1 级手牌上限 +1
# =============================================================================



# =============================================================================
# 26. 离散 2 级 T 槽上限 8
# =============================================================================



# =============================================================================
# 27. 金牙齿消灭后抽牌+1T
# =============================================================================



# =============================================================================
# 28. 扇子赋予临时空袭
# =============================================================================

def test_shanzi_grants_airraid():
    """扇子：使目标异象获得临时空袭，抽 1 张牌。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p1, (4, 0))
    h.give_hand(p1, "扇子")

    h.play_strategy(p1, "扇子", target=h.at((4, 0)))
    assert "空袭" in h.at((4, 0)).keywords


# =============================================================================
# 29. 臭虫减攻光环
# =============================================================================

def test_chouchong_aura():
    """臭虫：同列敌方异象攻击力 -1。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("臭虫", p1, (4, 2))
    h.deploy("烈焰人", p2, (0, 2))  # 同列，原攻 4

    h.game.refresh_all_auras()
    assert h.at((0, 2)).current_attack == 3, f"期望 3，实际 {h.at((0, 2)).current_attack}"


# =============================================================================
# 30. 白鼬受战斗伤害自毁
# =============================================================================

def test_baiyou_combat_death():
    """白鼬：受到战斗伤害后自毁。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("白鼬", p1, (4, 0))
    h.deploy("烈焰人", p2, (0, 0))

    from card_pools.effect_utils import deal_damage_to_minion
    deal_damage_to_minion(h.at((4, 0)), 1, source=h.at((0, 0)), game=h.game)

    assert h.at((4, 0)) is None or not h.at((4, 0)).is_alive()


# =============================================================================
# 31. 林鼠抉择抽牌或召唤松鼠
# =============================================================================



# =============================================================================
# 32. 狐免疫偶数伤害
# =============================================================================



# =============================================================================
# 33. 弱狼亡语对敌方主角造成伤害
# =============================================================================



# =============================================================================
# 34. 猫可被无限献祭
# =============================================================================

def test_mao_infinite_sacrifice():
    """猫：免疫献祭消灭，且 _sacrifice_remaining 不因献祭而降到 0，可无限次被献祭。"""
    h = GameHarness()
    p1, p2 = h.players

    # 部署猫（冥刻异象自动获得献祭1/丰饶1）
    mao = h.deploy("猫", p1, (4, 0))
    assert mao is not None
    assert mao.is_alive()
    assert getattr(mao, '_sacrifice_remaining', 0) == 1

    # 给 p1 手牌两张需要 B 费用的异象（猫自身 1T1B）
    h.give_hand(p1, "猫", "猫")

    # 注入献祭选择器：总是选场上的猫
    p1.sacrifice_chooser = lambda req_blood: [mao]

    # 第一次打出：献祭猫，猫应保留且 _sacrifice_remaining 仍 > 0
    h.play_minion(p1, "猫", (4, 1))
    assert mao.is_alive(), "猫免疫献祭消灭，应仍然存活"
    assert mao._sacrifice_remaining > 0, "猫被献祭后 _sacrifice_remaining 不应耗尽"

    # 第二次打出：再次献祭同一只猫，应仍然成功
    h.play_minion(p1, "猫", (4, 2))
    assert mao.is_alive(), "猫应仍然存活"
    assert mao._sacrifice_remaining > 0, "猫应仍可被献祭"


# =============================================================================
# 35. 过曝！费用修正
# =============================================================================

def test_guobao_cost_reduction():
    """过曝！：对手每有1张手牌，费用-1S。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p2 5张手牌
    from card_pools.effect_utils import create_card_by_name
    for _ in range(5):
        card = create_card_by_name("书", p2)
        p2.card_hand.append(card)
    assert len(p2.card_hand) == 5

    h.give_hand(p1, "过曝！")
    guobao = p1.card_hand[0]

    # 验证修正后费用 = 10S - 5S = 5S
    cost = p1._get_play_cost(guobao)
    assert cost.s == 5, f"过曝！费用应为5S，实际={cost.s}S"
    assert cost.t == 0, f"过曝！T应为0，实际={cost.t}T"


def test_guobao_cost_capped_at_zero():
    """过曝！：费用修正不会低于0。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p2 10张手牌（直接 append 绕过堆叠和上限）
    from card_pools.effect_utils import create_card_by_name
    for _ in range(10):
        card = create_card_by_name("书", p2)
        p2.card_hand.append(card)
    assert len(p2.card_hand) == 10

    h.give_hand(p1, "过曝！")
    guobao = p1.card_hand[0]

    # 验证修正后费用 = max(0, 10S - 10S) = 0S
    cost = p1._get_play_cost(guobao)
    assert cost.s == 0, f"过曝！费用应为0S，实际={cost.s}S"


# =============================================================================
# 36. 鹤预设目标机制
# =============================================================================

def test_he_resolve_effect_target():
    """鹤：结算阶段开始时，若已预设目标，自动重置目标攻防并给玩家+1HP。"""
    h = GameHarness()
    p1, p2 = h.players

    # 部署鹤和敌方书架
    he = h.deploy("鹤", p1, (4, 0))
    shujia = h.deploy("书架", p2, (0, 0))

    # 给书架加 buff 并扣血
    shujia.perm_attack_bonus = 2
    shujia.perm_max_health_bonus = 2
    shujia.recalculate()
    shujia.current_health = 4  # 不满血
    assert shujia.current_attack == 2
    assert shujia.current_max_health == 5
    assert shujia.current_health == 4

    # 预设目标：书架
    he._pending_effect_target = shujia

    # 先让玩家失去一些 HP（避免超出上限）
    p1.health = 25

    # 发射结算阶段开始（触发鹤的 on_turn_start）
    h.resolve_phase(p1, p2)

    # 验证书架被重置
    assert shujia.current_attack == 0, f"期望 0，实际 {shujia.current_attack}"
    assert shujia.current_max_health == 3, f"期望 3，实际 {shujia.current_max_health}"
    assert shujia.current_health == 3, f"期望 3，实际 {shujia.current_health}"

    # 验证玩家+1HP
    assert p1.health == 26, f"期望 26，实际 {p1.health}"
    # 预设目标应被清空
    assert getattr(he, '_pending_effect_target', None) is None


def test_he_no_target_skips():
    """鹤：没有预设目标时，结算阶段开始不执行效果。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("鹤", p1, (4, 0))
    p1_health_before = p1.health

    h.resolve_phase(p1, p2)

    assert p1.health == p1_health_before


def test_he_target_removed_skips():
    """鹤：预设目标在结算前被移除，效果跳过。"""
    h = GameHarness()
    p1, p2 = h.players

    he = h.deploy("鹤", p1, (4, 0))
    shujia = h.deploy("书架", p2, (0, 0))
    he._pending_effect_target = shujia

    # 移除书架
    h.game.board.remove_minion((0, 0))

    p1_health_before = p1.health
    h.resolve_phase(p1, p2)

    assert p1.health == p1_health_before
    assert getattr(he, '_pending_effect_target', None) is None


# =============================================================================
# 37. effect_utils 崩溃点回归
# =============================================================================

def test_register_terrain_enforcement_without_owner_does_not_crash():
    """register_terrain_enforcement：旧调用不传 owner 时不应引用不存在的 minion。"""
    h = GameHarness()

    from card_pools.effect_utils import register_terrain_enforcement

    register_terrain_enforcement(h.game, column=0, forced_terrain="水路", end_turn=h.game.current_turn)

    assert h.game._terrain_overrides[(0, 0)] == "水路"
    cleanup = h.game._delayed_effects[-1]["fn"]
    cleanup()
    assert (0, 0) not in h.game._terrain_overrides


def test_health_lost_this_phase_uses_current_history_api():
    """health_lost_this_phase：使用现有 GameHistory.query_events() 接口统计，不应因旧参数崩溃。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import health_lost_this_phase

    h.resolve_phase(p1, p2)
    p1.health_change(-3)

    assert health_lost_this_phase(h.game, p1) == 3


# =============================================================================
# 38. 雕像 special_fn 绑定
# =============================================================================

def test_statue_cards_bind_effects_through_special_fn():
    """雕像牌的融合回调由 special_fn 部署时绑定，而不是直接挂在卡定义字段上。"""
    from tards.data.card_db import DEFAULT_REGISTRY

    statue_names = [
        "节肢座首", "多足底座",
        "水肺座首", "鳍尾底座",
        "尖牙座首", "利爪底座",
        "丰饶座首", "牢牲底座",
        "长翅座首", "破风底座",
    ]

    for name in statue_names:
        card_def = DEFAULT_REGISTRY.get(name)
        assert card_def is not None, f"缺少雕像卡定义：{name}"
        assert card_def.special_fn is not None, f"{name} 应通过 special_fn 绑定雕像效果"
        assert card_def.on_statue_activate is None
        assert card_def.on_statue_fuse is None


def test_direct_summoned_avian_statues_fuse_via_special_fn():
    """直接召唤雕像时，special_fn 也应绑定运行时雕像字段并触发融合。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import summon_minion_by_name

    bird = summon_minion_by_name(h.game, "鸥", p1, (4, 4))
    bird.tags.append("飞禽")
    base_attack = bird.current_attack
    top = summon_minion_by_name(h.game, "长翅座首", p1, (4, 1))
    bottom = summon_minion_by_name(h.game, "破风底座", p1, (4, 0))

    assert top.statue_top is True
    assert top.statue_pair == "avian"
    assert callable(top.on_statue_activate)
    assert bottom.statue_bottom is True
    assert bottom.statue_pair == "avian"
    assert callable(bottom.on_statue_fuse)
    assert len(h.game._pending_statues) == 1
    edge = h.game.fusion_system.edge_between(top, bottom)
    assert edge is not None
    assert edge.kind == "statue"
    assert edge["top"] is top
    assert edge["bottom"] is bottom

    h.game._resolve_statue_fusions()

    assert bird.keywords.get("迅捷") is True
    assert bird.current_attack == base_attack + 2
    assert not top.is_alive()
    assert not bottom.is_alive()


# =============================================================================
# N. 骷髅马骑士加费效果死亡/下回合清理
# =============================================================================

def test_kuloumaqishi_cost_modifier_removed_on_death():
    """骷髅马骑士：部署后手牌+1T；死亡时应立即移除修正。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "探索", "骷髅马骑士")
    h.play_minion(p1, "骷髅马骑士", (4, 2))

    explore = next(c for c in p1.card_hand if c.name == "探索")
    assert p1._get_play_cost(explore).t == 2, "部署后探索费用应为 2T"

    from card_pools.effect_utils import destroy_minion
    kulou = h.game.board.get_minion_at((4, 2))
    destroy_minion(kulou, h.game)

    assert p1._get_play_cost(explore).t == 1, "骷髅马骑士死亡后费用应恢复为 1T"


def test_kuloumaqishi_cost_modifier_removed_after_next_turn():
    """骷髅马骑士：活到下回合结束时费用修正应自动移除。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "探索", "骷髅马骑士")
    h.play_minion(p1, "骷髅马骑士", (4, 2))

    explore = next(c for c in p1.card_hand if c.name == "探索")
    assert p1._get_play_cost(explore).t == 2, "部署后探索费用应为 2T"

    # 推进一回合并触发回合结束事件（即使结算阶段被跳过也能清理）
    h.advance_turn()
    h.game.emit_event("turn_end", turn=h.game.current_turn, first=p1, second=p2)

    assert p1._get_play_cost(explore).t == 1, "下回合结束后费用应恢复为 1T"


def test_kuloumaqishi_cost_modifier_removed_when_resolve_skipped():
    """骷髅马骑士：下回合结算阶段被跳过时，回合结束仍应移除修正。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "探索", "骷髅马骑士")
    h.play_minion(p1, "骷髅马骑士", (4, 2))

    explore = next(c for c in p1.card_hand if c.name == "探索")
    assert p1._get_play_cost(explore).t == 2, "部署后探索费用应为 2T"

    # 推进一回合，跳过结算阶段，只触发 turn_end
    h.advance_turn()
    h.game._skip_resolve_phase = True
    h.game.emit_event("turn_end", turn=h.game.current_turn, first=p1, second=p2)

    assert p1._get_play_cost(explore).t == 1, "跳过结算阶段后回合结束费用应恢复为 1T"


# =============================================================================
# N+1. 惊喜礼物亡语抽牌
# =============================================================================

def test_jingxiliwu_deathrattle_draws():
    """惊喜礼物：亡语使你抽1张，对手抽2张。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import create_card_by_name
    for _ in range(5):
        p1.card_deck.append(create_card_by_name("时空灵", p1))
        p2.card_deck.append(create_card_by_name("时空灵", p2))

    h.deploy("惊喜礼物", p1, (4, 2))
    gift = h.game.board.get_minion_at((4, 2))
    assert gift is not None

    p1_hand_before = len(p1.card_hand)
    p2_hand_before = len(p2.card_hand)

    from card_pools.effect_utils import destroy_minion
    destroy_minion(gift, h.game)

    assert len(p1.card_hand) == p1_hand_before + 1, "惊喜礼物亡语应使拥有者抽1张"
    assert len(p2.card_hand) == p2_hand_before + 2, "惊喜礼物亡语应使对手抽2张"


# =============================================================================
# N+2. 竹心部署消灭协同敌方异象
# =============================================================================

def test_zhuxin_deploy_targets_enemy_coordinated_minion():
    """竹心：部署时选择并消灭一个处于协同的敌方异象。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 在同列放置两个敌方异象，使保卫者处于协同状态
    h.deploy("保卫者", p2, (0, 0))
    h.deploy("蠹虫", p2, (1, 0))
    assert h.at((0, 0)) is not None, "保卫者应被部署"
    assert h.at((1, 0)) is not None, "同列友方异象应存在"

    # p1 手牌有竹心，并设置指向器总是选择第一个合法目标
    h.give_hand(p1, "竹心")
    h.game.targeting_provider = lambda game, request, targets: targets[0]

    # p1 部署竹心
    assert h.play_minion(p1, "竹心", (4, 0)), "竹心应成功部署"
    assert h.at((4, 0)) is not None, "竹心应存在于战场"
    assert h.at((0, 0)) is None, "竹心应消灭处于协同的敌方保卫者"
    assert h.at((1, 0)) is not None, "同列另一个友方异象应保留"


# =============================================================================
# N+3. 矢量炮可以正常部署
# =============================================================================

def test_shiliangpao_can_deploy():
    """矢量炮：作为异象卡应能正常部署到友方位置。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "矢量炮")
    assert h.play_minion(p1, "矢量炮", (4, 0)), "矢量炮应能成功部署"
    assert h.at((4, 0)) is not None, "矢量炮应存在于战场"
    assert h.at((4, 0)).name == "矢量炮", "该位置应为矢量炮"


# =============================================================================
# N+4. 轰击可以选中受伤异象
# =============================================================================

def test_hongji_targets_injured_minion():
    """轰击：可以选中并消灭受伤异象，并将 TNT炮 加入手牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 部署一个异象并使其受伤
    h.deploy("保卫者", p2, (0, 0))
    defender = h.at((0, 0))
    defender.current_health = 1

    # p1 手牌有轰击，并设置指向器总是选择第一个合法目标
    h.give_hand(p1, "轰击")
    h.game.targeting_provider = lambda game, request, targets: targets[0]

    # p1 使用轰击
    assert h.play_strategy(p1, "轰击"), "轰击应成功使用"
    assert h.at((0, 0)) is None, "轰击应消灭受伤的保卫者"
    assert any(c.name == "TNT炮" for c in p1.card_hand), "轰击应将 TNT炮 加入手牌"


# =============================================================================
# N+5. 流明不会把非两栖精灵召唤到水路
# =============================================================================

def test_liuming_does_not_summon_spirits_to_water():
    """流明：随机召唤精灵时只选择对该精灵合法的位置，不会放到水路。"""
    h = GameHarness()
    p1, p2 = h.players

    # 占据大部分陆地位置，只给流明和精灵留合法陆地空位
    h.deploy("书架", p1, (4, 1))
    h.deploy("书架", p1, (4, 2))
    h.deploy("书架", p1, (3, 0))
    h.deploy("书架", p1, (3, 1))
    h.deploy("书架", p1, (3, 2))

    p1.s_point = 6
    h.give_hand(p1, "流明")
    assert h.play_minion(p1, "流明", (4, 0)), "流明应成功部署"

    # 所有精灵都不是两栖，不应出现在水路列（第4列）
    for pos, m in h.game.board.minion_place.items():
        if "精灵" in getattr(m, "tags", []):
            assert pos[1] != 4, f"精灵不应被召唤到水路：{pos}"


# =============================================================================
# N+6. 劫掠兽使 HP=1 的入场异象死亡
# =============================================================================

def test_jielueshou_kills_1hp_minion_on_deploy():
    """劫掠兽：HP=1 的异象进入战场时，受到 -1HP 后应立即死亡。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("劫掠兽", p1, (4, 0))
    h.give_hand(p1, "时空灵")
    assert h.play_minion(p1, "时空灵", (4, 1)), "时空灵应成功部署"
    assert h.at((4, 1)) is None, "HP=1 的时空灵应被劫掠兽效果消灭"


# =============================================================================
# N+7. 鹏的部署钩子签名
# =============================================================================

def test_peng_deploy_hook_signature():
    """鹏：部署钩子应只接收被部署异象一个参数；此前 def deploy_hook(g, deployed)
    导致 _default_minion_effect 调用 hook(minion) 时抛出 TypeError。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("鹏", p1, (4, 0))
    h.give_hand(p1, "松鼠")
    assert h.play_minion(p1, "松鼠", (4, 1)), "松鼠应成功部署"
    assert_minion_keyword(h.game, (4, 1), "休眠", 2,
                          msg="非飞禽且花费≤5的松鼠被鹏赋予休眠2")


# =============================================================================
# N+8. 狂风阻止对方部署并在下回合结束时解除
# =============================================================================

def test_kuangfeng_blocks_opponent_deploy_then_expires():
    """狂风：对方在限制期间无法打出异象，下一回合结束时限制解除。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "狂风")
    p1.t_point = 10
    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "狂风"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "狂风应成功打出"
    assert len(h.game._global_deploy_restrictions) == 1, "应存在全局部署限制"

    # 给 p2 一张 0 费异象
    h.give_hand(p2, "烛烟")
    p2.t_point = 10
    p2_serial = next((i + 1 for i, c in enumerate(p2.card_hand) if c.name == "烛烟"), None)
    assert p2_serial is not None

    attempts = [0]
    def provider(game, active, opponent):
        if active == p2 and attempts[0] == 0:
            attempts[0] += 1
            return {"type": "play", "serial": p2_serial, "target": (0, 2)}
        return {"type": "brake"}

    h.game.action_provider = provider
    h.game.action_phase(p1, p2)
    assert not h.game.board.minion_place, "狂风限制应阻止 p2 部署烛烟"

    # 下一回合结束后限制解除
    h.game.current_turn += 1
    h.game.action_provider = lambda g, a, o: {"type": "brake"}
    h.game.run_turn()
    assert len(h.game._global_deploy_restrictions) == 0, "狂风限制应已解除"


# =============================================================================
# N+9. 血瓶提供的 B 点可用于支付异象鲜血费用
# =============================================================================

def test_xueping_b_point_pays_minion_blood_cost():
    """血瓶：获得的 B 点可直接用于部署带鲜血费用的异象，无需额外献祭。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p1 血瓶、猫（1T1B）、松鼠（作为血瓶弃牌目标）
    h.give_hand(p1, "血瓶", "猫", "松鼠")
    p1.t_point = 4  # 3T 血瓶 + 1T 猫

    # 固定指向提供商，让血瓶总是弃掉松鼠
    def _pick_squirrel(game, request, valid_targets):
        for t in valid_targets:
            if getattr(t, "name", None) == "松鼠":
                return t
        return valid_targets[0] if valid_targets else None

    h.game.targeting_provider = _pick_squirrel

    # 打血瓶，获得 3B
    xueping_serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "血瓶"), None)
    assert xueping_serial is not None
    assert p1.play_card(xueping_serial, target=None, game=h.game), "血瓶应成功打出"
    assert p1.b_point == 3, "血瓶应提供 3B"

    # 用 B 点支付猫的 1B 费用，无需献祭
    mao_serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "猫"), None)
    assert mao_serial is not None
    assert p1.play_card(mao_serial, target=(4, 0), game=h.game), "猫应用血瓶B点成功部署"

    assert h.at((4, 0)) is not None, "猫应被部署到 (4,0)"
    assert h.at((4, 0)).name == "猫"
    assert p1.b_point == 2, "应只消耗 1B，剩余 2B"


# =============================================================================
# N+10. 不寐抉择：消灭沉浸度为3的异象
# =============================================================================

def test_bumei_destroy_level3_minion():
    """不寐：选择消灭分支后，可消灭场上一个沉浸度为3的异象。"""
    h = GameHarness()
    p1, p2 = h.players

    # 部署一只沉浸度为3的异象（狐）
    fox = h.deploy("狐", p2, (0, 0))
    assert fox is not None
    assert fox.is_alive()

    h.give_hand(p1, "不寐")
    p1.t_point = 3

    # 强制选择“消灭”分支
    h.game.choice_provider = lambda game, player, options, title: "消灭一个沉浸度为3的异象"

    def _pick_fox(game, request, valid_targets):
        for t in valid_targets:
            if getattr(t, "name", None) == "狐":
                return t
        return valid_targets[0] if valid_targets else None

    h.game.targeting_provider = _pick_fox

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "不寐"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "不寐应成功打出"

    assert not fox.is_alive(), "狐应被不寐消灭"


# =============================================================================
# N+11. 不寐抉择：对手随机弃一张沉浸度为3的手牌
# =============================================================================

def test_bumei_discard_opponent_level3_hand():
    """不寐：选择弃牌分支后，对手随机弃一张沉浸度为3的手牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给对手一张沉浸度为3的手牌（骨王）
    h.give_hand(p2, "骨王")
    assert any(c.name == "骨王" for c in p2.card_hand)

    h.give_hand(p1, "不寐")
    p1.t_point = 3

    # 强制选择“弃牌”分支
    h.game.choice_provider = lambda game, player, options, title: "对手随机弃一张沉浸度为3的手牌"

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "不寐"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "不寐应成功打出"

    assert not any(c.name == "骨王" for c in p2.card_hand), "骨王应从对手手牌中弃置"
    assert any(c.name == "骨王" for c in p2.card_dis), "骨王应进入对手弃牌堆"


# =============================================================================
# N+12. 不寐无合法目标时仍应正常结算
# =============================================================================

def test_bumei_fizzles_gracefully_when_no_targets():
    """不寐：两个分支均无合法目标时，仍弹出抉择并正常结算（不退回手牌）。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "不寐")
    p1.t_point = 3

    # 强制选择弃牌分支，但对手手中没有沉浸度为3的牌
    h.game.choice_provider = lambda game, player, options, title: "对手随机弃一张沉浸度为3的手牌"

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "不寐"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "不寐应正常结算"

    # 卡牌应进入弃牌堆，而不是回到手牌
    assert not any(c.name == "不寐" for c in p1.card_hand)
    assert any(c.name == "不寐" for c in p1.card_dis)


# =============================================================================
# N+13. 污煤：获得T槽、抽牌并降低自然上限
# =============================================================================

def test_wumei_gain_t_slot_draw_and_reduce_natural_cap():
    """污煤：获得1个T槽，抽1张牌，T槽自然上限-2。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import create_card_by_name
    p1.card_deck.append(create_card_by_name("漩涡", p1))

    h.give_hand(p1, "污煤")
    p1.t_point = 1
    p1.t_point_max = 0

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "污煤"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "污煤应成功打出"

    assert p1.t_point_max == 1, "应获得1个T槽"
    assert any(c.name == "漩涡" for c in p1.card_hand), "应抽1张牌"
    assert p1._natural_t_max_cap_modifier == -2, "T槽自然上限修正应为-2"


# =============================================================================
# N+14. 污煤降低后的T槽自然上限生效
# =============================================================================

def test_wumei_reduced_natural_cap_applies_in_draw_phase():
    """污煤：降低自然上限后，抽牌阶段T槽不再按原上限（10）增长。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import create_card_by_name
    p1.card_deck.append(create_card_by_name("漩涡", p1))
    p2.card_deck.append(create_card_by_name("漩涡", p2))

    h.give_hand(p1, "污煤")
    p1.t_point = 1

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "污煤"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "污煤应成功打出"

    # 将T槽设为8，再经过一个非特殊回合的抽牌阶段
    p1.t_point_max = 8
    h.game.current_turn = 8
    h.game.draw_phase(p1, p2)

    assert p1.t_point_max == 8, "自然上限被污煤降至8后，T槽不应继续增长到9"


# =============================================================================
# N+15. 灵动：将双方牌库中折算花费最小的牌移到牌库顶
# =============================================================================

def test_lingdong_moves_cheapest_cards_to_top():
    """灵动：双方牌库中折算花费最小的牌应被移到牌库顶（列表末尾）。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import create_card_by_name

    # p1 牌库：根除(5T) 漩涡(3T) 火灵(1T) → 最便宜的火灵移到顶
    p1.card_deck = [
        create_card_by_name("根除", p1),
        create_card_by_name("漩涡", p1),
        create_card_by_name("火灵", p1),
    ]
    # p2 牌库：火灵(1T) 根除(5T) 漩涡(3T) 火灵(1T) → 两张火灵移到顶（保持原有顺序）
    p2.card_deck = [
        create_card_by_name("火灵", p2),
        create_card_by_name("根除", p2),
        create_card_by_name("漩涡", p2),
        create_card_by_name("火灵", p2),
    ]

    h.give_hand(p1, "灵动")
    p1.t_point = 1

    serial = next((i + 1 for i, c in enumerate(p1.card_hand) if c.name == "灵动"), None)
    assert serial is not None
    assert p1.play_card(serial, target=None, game=h.game), "灵动应成功打出"

    assert p1.card_deck[-1].name == "火灵", "p1 最便宜的牌应移到牌库顶"
    assert [c.name for c in p2.card_deck[-2:]] == ["火灵", "火灵"], "p2 两张最便宜的牌应移到牌库顶并保持顺序"
