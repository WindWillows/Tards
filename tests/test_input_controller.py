"""输入控制器回归测试 — 手牌点击/快捷键行为。"""

from __future__ import annotations

from unittest.mock import MagicMock

from gui.battle.input_controller import InputController
from tests.harness import GameHarness


def _make_mock_frame(game, local_player):
    """构造满足 InputController 最小访问需求的 mock frame。"""
    frame = MagicMock()
    frame.duel = MagicMock()
    frame.duel.game = game
    frame.duel.is_remote = False
    frame.local_player = local_player
    frame.state = MagicMock()
    frame.state._is_playing_card = False
    frame.state._in_targeting_mode = False
    frame.state._in_sacrifice_mode = False
    frame.state._targeting_valid_targets = []
    frame.state._targeting_on_confirm = None
    frame.state._targeting_on_cancel = None
    frame.state.selected_card_idx = None
    frame.state.selected_card = None
    frame.state.valid_targets = []
    frame.state._pending_sacrifices = []
    frame.action_controller = MagicMock()
    return frame


def test_unplayable_minion_card_is_silently_ignored():
    """费用不足的异象卡被点击时，不应提交行动或进入指向/献祭模式。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1
    h.give_hand(p1, "书架")
    # p1 默认 0 资源，书架 3T 无法支付

    frame = _make_mock_frame(h.game, p1)
    ctrl = InputController(frame)

    ctrl.on_hand_card_click(0)

    # 不应提交任何本地行动
    frame.duel.submit_local_action.assert_not_called()
    # 不应进入任何交互模式
    assert frame.state._in_targeting_mode is False
    assert frame.state._in_sacrifice_mode is False
    # 防重入标志应立即释放（未触发实际出牌流程）
    assert frame.state._is_playing_card is False


def test_unplayable_strategy_card_is_silently_ignored():
    """费用不足的策略卡被点击时，不应提交行动或进入指向模式。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1
    h.give_hand(p1, "劫掠")
    # p1 默认 0 资源，劫掠无法支付

    frame = _make_mock_frame(h.game, p1)
    ctrl = InputController(frame)

    ctrl.on_hand_card_click(0)

    frame.duel.submit_local_action.assert_not_called()
    assert frame.state._in_targeting_mode is False
    assert frame.state._in_sacrifice_mode is False


def test_playable_minion_card_enters_targeting():
    """资源足够的异象卡被点击时，应正常进入部署指向模式。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1
    h.give_hand(p1, "书架")
    p1.t_point = 3

    frame = _make_mock_frame(h.game, p1)
    ctrl = InputController(frame)

    ctrl.on_hand_card_click(0)

    # 应进入指向模式（空棋盘下书架有多个可选位置）
    assert frame.state._in_targeting_mode is True
    frame.duel.submit_local_action.assert_not_called()


def test_helper_considers_blood_sacrifice():
    """_card_is_potentially_playable 在鲜血不足但可献祭时应返回 True。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1
    # 给 p1 一个鲜血费用异象（假设其原始费用包含 B）
    from card_pools.effect_utils import create_card_by_name
    card = create_card_by_name("书架", p1)
    # 强制改为鲜血费用以测试献祭路径
    from tards.core.cost import Cost
    card.cost = Cost(t=0, b=2)
    p1.add_card_to_hand(card, game=h.game, emit_events=False)

    # 场上放一只友方异象，可提供 1B（默认丰饶=1），不足以献祭
    h.deploy("亡灵", p1, (3, 0))

    frame = _make_mock_frame(h.game, p1)
    ctrl = InputController(frame)

    assert ctrl._card_is_potentially_playable(1, card, p1) is False

    # 再部署一只友方异象，使可献祭血量足够
    h.deploy("亡灵", p1, (3, 1))

    assert ctrl._card_is_potentially_playable(1, card, p1) is True


def test_blood_cost_minion_with_enough_b_point_skips_sacrifice():
    """B点足够的鲜血费用异象被点击时，应直接进入部署指向，不进入献祭模式。"""
    h = GameHarness()
    p1, p2 = h.players
    h.game.current_player = p1
    h.give_hand(p1, "猫")
    p1.t_point = 1
    p1.b_point = 1  # 足够支付猫 1B 费用

    frame = _make_mock_frame(h.game, p1)
    ctrl = InputController(frame)

    ctrl.on_hand_card_click(0)

    assert frame.state._in_targeting_mode is True, "B点足够时应直接进入部署指向"
    assert frame.state._in_sacrifice_mode is False, "不应进入献祭模式"
    frame.duel.submit_local_action.assert_not_called()
