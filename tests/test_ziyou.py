"""自由即奴役回归测试"""

from __future__ import annotations

from tests.harness import GameHarness


def _play_ziyou(h: GameHarness, target):
    """辅助：让 p1 从手牌打出自由即奴役并指向 target。"""
    p1, p2 = h.players
    h.game.targeting_provider = lambda game, request, valid_targets: target
    from card_pools.blood_effects import _ziyou_effect
    return _ziyou_effect(p1, None, h.game)


def test_ziyou_kills_minion_and_adds_echo():
    """目标本回合死亡时，应获得其回响。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    h.at((0, 0)).current_health = 1
    h.give_hand(p1, "自由即奴役")

    result = _play_ziyou(h, h.at((0, 0)))
    assert result, "自由即奴役应成功执行"
    assert h.at((0, 0)) is None or not h.at((0, 0)).is_alive(), "书架应被消灭"

    h.game._process_delayed_effects("turn_end")
    assert any(c.name == "书架" for c in p1.card_hand), "应获得书架回响"


def test_ziyou_damages_but_not_kills_no_echo():
    """目标未在本回合死亡时，不应获得回响。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))  # 3 血
    h.give_hand(p1, "自由即奴役")

    result = _play_ziyou(h, h.at((0, 0)))
    assert result
    assert h.at((0, 0)).is_alive(), "书架应仍存活"

    h.game._process_delayed_effects("turn_end")
    assert not any(c.name == "书架" for c in p1.card_hand), "不应获得书架回响"


def test_ziyou_no_source_card_no_echo():
    """目标无 source_card 时，即使死亡也不应崩溃或错误获得回响。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    m = h.at((0, 0))
    m.current_health = 1
    # 模拟无源卡场景
    m.source_card = None
    h.give_hand(p1, "自由即奴役")

    result = _play_ziyou(h, m)
    assert result

    h.game._process_delayed_effects("turn_end")
    # 手牌中除自由即奴役外不应多出任何异象回响
    assert not any(getattr(c, "_is_echo", False) for c in p1.card_hand)


def test_ziyou_one_hp_board_kills_exactly_one():
    """1 血目标被消灭后获得回响。"""
    h = GameHarness()
    p1, p2 = h.players

    h.deploy("书架", p2, (0, 0))
    h.at((0, 0)).current_health = 1
    h.give_hand(p1, "自由即奴役")

    result = _play_ziyou(h, h.at((0, 0)))
    assert result

    h.game._process_delayed_effects("turn_end")
    echo_names = [c.name for c in p1.card_hand if getattr(c, "_is_echo", False)]
    assert echo_names == ["书架"], f"应只获得书架回响，实际 {echo_names}"
