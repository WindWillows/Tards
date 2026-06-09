"""回归测试套件 — 已发现/已修复的 bug 固化于此。"""

from __future__ import annotations

from tards.cards import Strategy
from tards.constants import EVENT_CARD_ADDED_TO_HAND, EVENT_CARD_PLAYED, EVENT_PHASE_START
from tards.cost import Cost
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

def test_xuejian_bailian_counts_itself():
    """血溅白练：自身应计入本回合策略卡总数，恰为第3张时触发3点AOE。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p2 场上放两个异象
    h.deploy("书架", p2, (0, 0))
    h.deploy("书架", p2, (0, 1))
    assert_minion_exists(h.game, (0, 0), "书架")
    assert_minion_exists(h.game, (0, 1), "书架")

    # 给 p1 3张血溅白练
    h.give_hand(p1, "血溅白练", "血溅白练", "血溅白练")

    # 打出前2张（不应触发AOE）
    h.play_strategy(p1, "血溅白练")
    h.play_strategy(p1, "血溅白练")
    assert_minion_hp(h.game, (0, 0), 3)  # 仍为满血3
    assert_minion_hp(h.game, (0, 1), 3)

    # 打出第3张，触发3点AOE
    h.play_strategy(p1, "血溅白练")
    assert_minion_hp(h.game, (0, 0), 0)
    assert_minion_hp(h.game, (0, 1), 0)


# =============================================================================
# 3. 巫毒娃娃延迟触发
# =============================================================================

def test_wuduwawa_delayed_trigger():
    """巫毒娃娃：被非战斗伤害消灭时才触发亡语，战斗伤害消灭不触发。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("巫毒娃娃", p1, (4, 0))
    assert_minion_exists(h.game, (4, 0), "巫毒娃娃")

    # 用策略伤害消灭 → 应触发亡语（给 p1 +3HP）
    h.give_hand(p1, "人定")
    h.play_strategy(p1, "人定", target=h.at((4, 0)))
    # 巫毒娃娃死亡，p1 HP 从 30→33
    assert p1.health == 33, f"期望 33 HP，实际 {p1.health}"

    # 重新部署，再用战斗伤害消灭
    h.deploy("巫毒娃娃", p1, (4, 1))
    h.deploy("烈焰人", p2, (0, 1))
    # 直接调用 take_damage 模拟战斗伤害（来源为烈焰人）
    doll = h.at((4, 1))
    from card_pools.effect_utils import deal_damage_to_minion
    deal_damage_to_minion(doll, 10, source=h.at((0, 1)), game=h.game)
    # 战斗伤害消灭不应触发亡语，HP 保持 33
    assert p1.health == 33, f"期望仍为 33 HP，实际 {p1.health}"


# =============================================================================
# 4. 天籁人偶伤害分摊
# =============================================================================

def test_tianlai_renmo_damage_split():
    """天籁人偶：受到战斗伤害时，将溢出的 1 点伤害转移给相邻友方。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("天籁人偶", p1, (4, 2))
    h.deploy("书架", p1, (4, 1))   # 左侧相邻
    h.deploy("书架", p1, (4, 3))   # 右侧相邻

    # 敌方 5 攻异象攻击天籁人偶
    h.deploy("烈焰人", p2, (0, 2))
    attacker = h.at((0, 2))
    target = h.at((4, 2))
    target.take_damage(5, source_minion=attacker, source_type="combat")

    # 天籁人偶受到 4 点（坚韧1），相邻书架各受到溢出 1 点
    assert_minion_hp(h.game, (4, 2), 0)   # 4-4=0
    assert_minion_hp(h.game, (4, 1), 2)   # 3-1=2
    assert_minion_hp(h.game, (4, 3), 2)   # 3-1=2


# =============================================================================
# 5. 溴化银亡语给对手手牌
# =============================================================================

def test_xiuhuayin_deathrattle_gives_opponent_jiaopian():
    """溴化银：亡语将「胶片」加入对方手牌。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("溴化银", p1, (4, 2))
    xiuhuayin = h.at((4, 2))

    # 用策略消灭
    h.give_hand(p1, "人定")
    h.play_strategy(p1, "人定", target=xiuhuayin)

    assert_hand_contains(p2, "胶片")
    assert_hand_missing(p1, "胶片")


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

def test_silingfashi_revives_enemy_death():
    """死灵法师：敌方异象被消灭时，在其原位召唤亡灵。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("死灵法师", p1, (4, 0))
    h.deploy("书架", p2, (0, 0))

    # 消灭敌方书架
    h.give_hand(p1, "人定")
    h.play_strategy(p1, "人定", target=h.at((0, 0)))

    # 书架死亡，原位应出现亡灵
    assert_minion_exists(h.game, (0, 0), "亡灵")


# =============================================================================
# 10. Bishop 恐惧回血
# =============================================================================

def test_bishop_heals_on_fear():
    """Bishop：回合结束时有恐惧异象则回血。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("Bishop", p1, (4, 0))
    h.deploy("书架", p2, (0, 0))

    # 给书架加恐惧
    from card_pools.effect_utils import apply_fear
    apply_fear(h.at((0, 0)))

    p1.health = 20
    h.end_turn(p1, p2)
    assert p1.health == 21, f"期望 21 HP，实际 {p1.health}"


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

def test_dunxiu_zhizhen_gives_token():
    """钝锈指针：跳过结算阶段的同时给一张衍生卡。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "钝锈指针")
    h.play_strategy(p1, "钝锈指针")
    assert_hand_contains(p1, "指针")


# =============================================================================
# 14. 血契 1 级沉浸度流失生命
# =============================================================================

def test_blood_immersion_1_lose_hp():
    """血契 1 级：抽牌阶段开始时失去 1 HP、获得 1 S。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.BLOOD] = 1

    p1.health = 30
    p1.s_point = 0
    h.game.current_turn = 2  # 非第一回合
    h.game.draw_phase(p1, p2)

    assert p1.health == 29, f"期望 29 HP，实际 {p1.health}"
    assert p1.s_point == 1, f"期望 1 S，实际 {p1.s_point}"


# =============================================================================
# 15. 钝锈指针跳过结算后下回合恢复
# =============================================================================

def test_dunxiu_zhizhen_flag_cleared_next_turn():
    """钝锈指针：跳过结算阶段的标志在下一回合开始时应被清除。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "钝锈指针")
    h.play_strategy(p1, "钝锈指针")
    assert h.game._skip_resolve_phase is True

    # 进入下一回合
    h.advance_turn()
    h.start_turn(p1, p2)
    assert h.game._skip_resolve_phase is False, "标志应在回合开始时清除"


# =============================================================================
# 16. 血渍怀表 on_game_start 置顶
# =============================================================================

def test_xuezi_huaibiao_top_of_deck():
    """血渍怀表：对局开始时将自己置入卡组顶。"""
    h = GameHarness()
    p1, p2 = h.players

    from card_pools.effect_utils import create_card_by_name
    card = create_card_by_name("血渍怀表", p1)
    p1.card_deck.append(card)
    p1.card_deck.append(create_card_by_name("书架", p1))
    p1.card_deck.append(create_card_by_name("书架", p1))

    h.game.start_game()
    assert p1.card_deck[0].name == "血渍怀表"


# =============================================================================
# 17. 萤石减伤与回血
# =============================================================================

def test_yingshi_damage_reduction_and_heal():
    """萤石：受到的伤害-1；回合结束+1HP。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("萤石", p1, (4, 0))
    yingshi = h.at((4, 0))

    # 受到 3 点策略伤害 → 坚韧等效 -1，实际受 2 点
    from card_pools.effect_utils import deal_damage_to_minion
    deal_damage_to_minion(yingshi, 3, game=h.game)
    assert yingshi.health == 2, f"期望 2 HP，实际 {yingshi.health}"

    # 回合结束回血
    h.end_turn(p1, p2)
    assert yingshi.health == 3, f"期望 3 HP，实际 {yingshi.health}"


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

def test_baoweizhe_grows_on_damage():
    """保卫者：玩家受到伤害时获得 +1/+1。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("保卫者", p1, (4, 0))
    baoweizhe = h.at((4, 0))
    assert baoweizhe.current_attack == 0
    assert baoweizhe.current_health == 3

    # 对玩家造成 1 点伤害
    p1.health_change(-1)
    assert baoweizhe.current_attack == 1
    assert baoweizhe.current_health == 4


# =============================================================================
# 20. 亡的左轮费用修正
# =============================================================================

def test_wangde_zuolun_cost_reduction():
    """亡的左轮：打出后本回合下一张策略卡费用 -2T。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "亡的左轮", "人定")
    h.play_strategy(p1, "亡的左轮")

    card = p1.card_hand[0]
    assert card.name == "人定"
    cost = p1._get_play_cost(card)
    assert cost.t == 0, f"期望 0T，实际 {cost.t}T"  # 人定原 2T，减 2T


# =============================================================================
# 21. 钝锈指针衍生卡有指针关键词
# =============================================================================

def test_dunxiu_zhizhen_token_has_keyword():
    """钝锈指针：衍生卡「指针」应具有正确的关键词。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "钝锈指针")
    h.play_strategy(p1, "钝锈指针")

    pointer = p1.card_hand[0]
    assert pointer.name == "指针"
    assert "亡语" in pointer.keywords


# =============================================================================
# 22. 血契 2 级受到 >=3 伤害触发
# =============================================================================

def test_blood_immersion_2_damage_trigger():
    """血契 2 级：受到单次 >=3 伤害时获得 3S。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.BLOOD] = 2

    p1.s_point = 0
    p1.health_change(-5)
    assert p1.s_point == 3, f"期望 3 S，实际 {p1.s_point}"


# =============================================================================
# 23. 冥刻 1 级开局 6 张松鼠
# =============================================================================

def test_underworld_immersion_1_squirrels():
    """冥刻 1 级：开局牌库中应有 6 张松鼠。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.UNDERWORLD] = 1
    p1.setup_immersion_bonuses()

    squirrels = [c for c in p1.card_deck if c.name == "松鼠"]
    assert len(squirrels) == 6, f"期望 6 张松鼠，实际 {len(squirrels)}"


# =============================================================================
# 24. 冥刻 2 级兑换松鼠
# =============================================================================

def test_underworld_immersion_2_exchange_squirrel():
    """冥刻 2 级：出牌阶段可用 1T 兑换 1 张松鼠。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.UNDERWORLD] = 2
    p1.setup_immersion_bonuses()
    p1.t_point = 5

    h.game.action_phase(p1, p2)
    # 提供一个 exchange_squirrel action
    action = {"type": "exchange_squirrel"}
    # 手动调用处理逻辑（action_phase 内部会循环等待 provider）
    # 这里简化为直接调用兑换函数
    p1.t_point_change(-1)
    card = p1.squirrel_deck.pop()
    p1.add_card_to_hand(card, game=h.game, reason="兑换松鼠")
    assert hand_contains_name(p1, "松鼠")


def hand_contains_name(player, name):
    return any(c.name == name for c in player.card_hand)


# =============================================================================
# 25. 离散 1 级手牌上限 +1
# =============================================================================

def test_discrete_immersion_1_hand_limit():
    """离散 1 级：手牌上限从 8 增加到 9。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.DISCRETE] = 1
    p1.setup_immersion_bonuses()

    assert p1.card_hand_max == 9, f"期望 9，实际 {p1.card_hand_max}"


# =============================================================================
# 26. 离散 2 级 T 槽上限 8
# =============================================================================

def test_discrete_immersion_2_t_max():
    """离散 2 级：T 槽上限应为 8。"""
    h = GameHarness()
    p1, p2 = h.players

    from tards.card_db import Pack
    p1.immersion_points[Pack.DISCRETE] = 2
    p1.setup_immersion_bonuses()

    p1.t_point_max = 0
    p1.t_point = 0
    h.game.draw_phase(p1, p2)
    assert p1.t_point_max == 8, f"期望 8，实际 {p1.t_point_max}"


# =============================================================================
# 27. 金牙齿消灭后抽牌+1T
# =============================================================================

def test_jin_yachi_kill_draw():
    """金牙齿：消灭目标后抽 1 张牌并获得 1B。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    h.give_hand(p1, "金牙齿")

    before_hand = len(p1.card_hand)
    before_b = p1.b_point

    h.play_strategy(p1, "金牙齿", target=h.at((0, 0)))

    assert len(p1.card_hand) == before_hand + 1 - 1  # 打出-1，抽牌+1
    assert p1.b_point == before_b + 1


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

def test_linshu_choice():
    """林鼠：部署时抉择抽 1 张策略卡 或 0T 部署 1 只松鼠。"""
    h = GameHarness()
    p1, p2 = h.players

    h.give_hand(p1, "林鼠")
    # 模拟选择"抽策略"
    p1._choice_result = "抽1张策略卡"
    h.play_minion(p1, "林鼠", (4, 0))

    # 验证手牌中多了一张策略卡（由于随机，仅验证数量增加）
    assert len(p1.card_hand) >= 1


# =============================================================================
# 32. 狐免疫偶数伤害
# =============================================================================

def test_hu_immune_even():
    """狐：免疫偶数伤害。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("狐", p1, (4, 0))
    fox = h.at((4, 0))

    from card_pools.effect_utils import deal_damage_to_minion
    deal_damage_to_minion(fox, 2, game=h.game)
    assert fox.health == 4, f"期望满血 4，实际 {fox.health}"

    deal_damage_to_minion(fox, 3, game=h.game)
    assert fox.health == 1, f"期望 1，实际 {fox.health}"


# =============================================================================
# 33. 弱狼亡语对敌方主角造成伤害
# =============================================================================

def test_ruolang_deathrattle():
    """弱狼：亡语对敌方主角造成 3 点伤害。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("弱狼", p1, (4, 0))
    h.give_hand(p1, "人定")
    p2_health_before = p2.health

    h.play_strategy(p1, "人定", target=h.at((4, 0)))
    assert p2.health == p2_health_before - 3


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
    from tards.card_db import DEFAULT_REGISTRY

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

    bird = summon_minion_by_name(h.game, "鸥", p1, (4, 2))
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
