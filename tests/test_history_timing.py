"""操作历史写入时机回归测试。

确保卡牌打出记录不在 submit_play 时写入，而是在效果结算后
(EVENT_CARD_PLAYED / EVENT_CONSPIRACY_TRIGGERED) 写入。
"""

from __future__ import annotations

from unittest.mock import MagicMock

from gui.battle.input_controller import InputController
from tards import Strategy
from tests.harness import GameHarness


def test_submit_play_does_not_write_history():
    """submit_play 不应再直接写入操作历史；历史由事件监听负责。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1

    h.give_hand(p1, "劫掠")
    card = h._find_in_hand(p1, "劫掠")
    assert isinstance(card, Strategy)

    frame = MagicMock()
    frame.duel = MagicMock()
    frame.duel.game = h.game
    frame.local_player = p1
    frame._pending_sacrifices = None
    frame._is_playing_card = False

    ctrl = InputController(frame)
    ctrl.submit_play(1, None)

    # submit_play 不再调用 _add_history
    frame._add_history.assert_not_called()
    # 但应提交出牌动作
    frame.duel.submit_local_action.assert_called_once()


def test_card_played_event_emitted_after_strategy_effect():
    """策略卡效果执行后应发射 EVENT_CARD_PLAYED。"""
    from tards.constants import EVENT_CARD_PLAYED

    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1

    # 给 p2 放一个 3T 以下花费目标
    h.deploy("书架", p2, (0, 0))
    target = h.at((0, 0))
    p1.t_point = 4  # 劫掠费用 4T
    h.give_hand(p1, "劫掠")

    # 设置指向 provider，自动选择书架
    h.game.targeting_provider = lambda game, request, valid_targets: target

    events = []
    h.game.register_listener(EVENT_CARD_PLAYED, lambda e: events.append(e))

    # 直接通过 play_card 执行，跳过 GUI
    serial = 1
    result = p1.play_card(serial, None, h.game)
    assert result, "劫掠应成功执行"

    assert len(events) == 1, f"应发射一次 EVENT_CARD_PLAYED，实际 {len(events)} 次"
    assert events[0].get("player") == p1
    assert events[0].get("card").name == "劫掠"
