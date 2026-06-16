"""劫掠测试"""

from __future__ import annotations

from tests.assertions import (
    assert_board_empty,
    assert_hand_contains,
    assert_hand_missing,
    assert_minion_exists,
)
from tests.harness import GameHarness

from card_pools.effect_utils import convert_cost_to_t


# =============================================================================
# 费用折算验证（辅助）
# =============================================================================

def test_cost_conversion_boundary():
    """验证关键卡牌的费用折算值，确保边界理解正确。"""
    from card_pools.effect_utils import get_card_definition

    mite = get_card_definition("末影螨")   # 1I
    ghast = get_card_definition("恶魂")    # 1T1G
    rod = get_card_definition("钓鱼竿")    # 4T
    enderman = get_card_definition("末影人")  # 1D

    assert convert_cost_to_t(mite.cost) == 1, f"末影螨 1I 应折算为 1T"
    assert convert_cost_to_t(ghast.cost) == 3, f"恶魂 1T1G 应折算为 3T"
    assert convert_cost_to_t(rod.cost) == 4, f"钓鱼竿 4T 应折算为 4T"
    assert convert_cost_to_t(enderman.cost) == 4, f"末影人 1D 应折算为 4T"


# =============================================================================
# 劫掠效果测试
# =============================================================================

def test_jielue_basic_destroy():
    """劫掠：消灭1个花费≤3T的敌方异象，目标不协同，不抽牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 部署一个 3T 费用的书架（合法目标，不协同）
    h.deploy("书架", p2, (0, 2))
    assert_minion_exists(h.game, (0, 2), "书架")

    # p1 手牌有劫掠并打出
    h.give_hand(p1, "劫掠")
    result = h.play_strategy(p1, "劫掠")
    assert result, "劫掠应成功执行"

    # 书架被消灭
    assert_board_empty(h.game, (0, 2))
    # p1 没有抽到牌
    assert_hand_missing(p1, "书架")


def test_jielue_synergy_draws_card():
    """劫掠：消灭处于协同状态的敌方异象，从对方牌库顶抽1张牌。"""
    h = GameHarness()
    p1, p2 = h.players

    # 给 p2 牌库放一张牌
    from card_pools.effect_utils import create_card_by_name
    card = create_card_by_name("火把", p2)
    p2.card_deck.append(card)

    # p2 在同一列（河岸）部署两个异象（书架 3T + 钓鱼竿 4T）
    # 书架是合法目标，钓鱼竿不合法但提供协同
    h.deploy("书架", p2, (0, 3))
    h.deploy("钓鱼竿", p2, (1, 3))
    assert_minion_exists(h.game, (0, 3), "书架")
    assert_minion_exists(h.game, (1, 3), "钓鱼竿")

    # p1 打出劫掠
    h.give_hand(p1, "劫掠")
    result = h.play_strategy(p1, "劫掠")
    assert result, "劫掠应成功执行"

    # 书架被消灭，钓鱼竿存活
    assert_board_empty(h.game, (0, 3))
    assert_minion_exists(h.game, (1, 3), "钓鱼竿")

    # p1 从 p2 牌库顶抽到了火把
    assert_hand_contains(p1, "火把")


def test_jielue_no_valid_target():
    """劫掠：场上没有花费≤3T的敌方异象时，效果无事发生。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 只部署一个 4T 的钓鱼竿（不合法目标），钓鱼竿只能放在河岸
    h.deploy("钓鱼竿", p2, (0, 3))
    assert_minion_exists(h.game, (0, 3), "钓鱼竿")

    # p1 打出劫掠，没有合法目标
    h.give_hand(p1, "劫掠")
    result = h.play_strategy(p1, "劫掠")
    # 无合法目标时 request_target 返回 None，effect_fn 返回 False
    assert not result, "劫掠应因无合法目标而失败"

    # 钓鱼竿仍在场上
    assert_minion_exists(h.game, (0, 3), "钓鱼竿")


def test_jielue_cost_boundary_includes_3t():
    """劫掠：花费恰好=3T折算的异象可以被选中。"""
    h = GameHarness()
    p1, p2 = h.players

    # 恶魂 1T1G = 折算3T，恰好是边界
    h.deploy("恶魂", p2, (0, 2))
    assert_minion_exists(h.game, (0, 2), "恶魂")

    h.give_hand(p1, "劫掠")
    result = h.play_strategy(p1, "劫掠")
    assert result, "劫掠应能选择折算费用=3T的恶魂"

    assert_board_empty(h.game, (0, 2))


def test_jielue_cost_boundary_excludes_4t():
    """劫掠：花费>3T折算的异象不能被选中。"""
    h = GameHarness()
    p1, p2 = h.players

    # 末影人 1D = 折算4T，超出边界
    h.deploy("末影人", p2, (0, 2))
    assert_minion_exists(h.game, (0, 2), "末影人")

    h.give_hand(p1, "劫掠")
    result = h.play_strategy(p1, "劫掠")
    assert not result, "劫掠不应能选择折算费用=4T的末影人"

    assert_minion_exists(h.game, (0, 2), "末影人")
