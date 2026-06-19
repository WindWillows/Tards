"""天下无“双”回归测试 — 当前 HP 驱动循环，且无条件先射 1 次。"""

from __future__ import annotations

from tests.assertions import assert_minion_exists, assert_minion_hp
from tests.harness import GameHarness


def test_tianxia_wushuang_always_fires_once():
    """只要有敌方异象，卡牌至少会射出 1 次（即使初始当前 HP 全为奇数）。"""
    h = GameHarness()
    p1, p2 = h.players

    # p2 部署两个 3 血异象（当前 HP 均为奇数）
    h.deploy("书架", p2, (0, 0))
    h.deploy("书架", p2, (0, 1))
    assert_minion_hp(h.game, (0, 0), 3)
    assert_minion_hp(h.game, (0, 1), 3)

    h.give_hand(p1, "天下无“双”")
    result = h.play_strategy(p1, "天下无“双”")
    assert result, "天下无双应成功执行"

    # 至少造成 1 点伤害；两个 3 血书架不可能同时保持 3 血
    m0 = h.at((0, 0))
    m1 = h.at((0, 1))
    assert (m0 is None or m0.current_health < 3 or m1 is None or m1.current_health < 3)


def test_tianxia_wushuang_deals_one_to_single_even_hp_minion():
    """单个当前 HP 为偶数的敌方异象只会被削 1 点 HP（变为奇数后循环停止）。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))  # 基础 3 血
    minion = h.at((0, 0))
    minion.current_health = 2  # 当前 HP 为偶数
    assert_minion_hp(h.game, (0, 0), 2)

    h.give_hand(p1, "天下无“双”")
    result = h.play_strategy(p1, "天下无“双”")
    assert result

    # 只扣 1 点，当前 HP 变为 1（奇数），循环停止
    assert_minion_hp(h.game, (0, 0), 1)
    assert_minion_exists(h.game, (0, 0), "书架")


def test_tianxia_wushuang_repeats_while_even_hp_exists():
    """只要场上仍有当前 HP 为偶数的敌方异象，效果就会继续。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    h.deploy("书架", p2, (0, 1))
    h.at((0, 0)).current_health = 2
    h.at((0, 1)).current_health = 2

    h.give_hand(p1, "天下无“双”")
    result = h.play_strategy(p1, "天下无“双”")
    assert result

    # 过程结束后，所有存活异象当前 HP 必为奇数（否则还会继续）
    m0 = h.at((0, 0))
    m1 = h.at((0, 1))
    if m0 and m0.is_alive():
        assert m0.current_health % 2 == 1
    if m1 and m1.is_alive():
        assert m1.current_health % 2 == 1


def test_tianxia_wushuang_one_hp_board_kills_exactly_one():
    """场上全是 1 血异象时，卡牌只打死 1 个就停止。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    h.deploy("书架", p2, (0, 1))
    h.deploy("书架", p2, (0, 2))
    h.at((0, 0)).current_health = 1
    h.at((0, 1)).current_health = 1
    h.at((0, 2)).current_health = 1

    h.give_hand(p1, "天下无“双”")
    result = h.play_strategy(p1, "天下无“双”")
    assert result

    alive_count = sum(1 for m in h.game.board.minion_place.values() if m.owner == p2 and m.is_alive())
    assert alive_count == 2, "应只消灭 1 个 1 血异象"
