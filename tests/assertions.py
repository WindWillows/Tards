"""Tards 游戏专用断言 — 失败时提供清晰的上下文信息。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from tards.cards import Minion
from tards.game import Game
from tards.player import Player


def _fmt_pos(pos: Tuple[int, int]) -> str:
    from tards.board import Board
    r, c = pos
    col_name = Board.COL_NAMES[c] if 0 <= c < 5 else str(c)
    return f"({r},{col_name})"


def assert_minion_exists(
    game: Game,
    pos: Tuple[int, int],
    name: Optional[str] = None,
    msg: Optional[str] = None,
) -> Minion:
    """断言指定位置存在异象，可选验证名称。"""
    m = game.board.get_minion_at(pos)
    prefix = f"位置 {_fmt_pos(pos)}"
    if m is None:
        raise AssertionError(
            f"{prefix} 没有异象" + (f" | {msg}" if msg else "")
        )
    if name is not None and m.name != name:
        raise AssertionError(
            f"{prefix} 的异象是 [{m.name}]，期望 [{name}]"
            + (f" | {msg}" if msg else "")
        )
    return m


def assert_minion_hp(
    game: Game,
    pos: Tuple[int, int],
    expected: int,
    msg: Optional[str] = None,
) -> None:
    """断言指定位置异象的当前生命值。"""
    m = assert_minion_exists(game, pos, msg=msg)
    if m.current_health != expected:
        raise AssertionError(
            f"位置 {_fmt_pos(pos)} 的 [{m.name}] HP={m.current_health}，期望 {expected}"
            + (f" | {msg}" if msg else "")
        )


def assert_minion_attack(
    game: Game,
    pos: Tuple[int, int],
    expected: int,
    msg: Optional[str] = None,
) -> None:
    """断言指定位置异象的当前攻击力。"""
    m = assert_minion_exists(game, pos, msg=msg)
    if m.current_attack != expected:
        raise AssertionError(
            f"位置 {_fmt_pos(pos)} 的 [{m.name}] ATK={m.current_attack}，期望 {expected}"
            + (f" | {msg}" if msg else "")
        )


def assert_minion_keyword(
    game: Game,
    pos: Tuple[int, int],
    keyword: str,
    expected: Any,
    msg: Optional[str] = None,
) -> None:
    """断言指定位置异象的关键字值。

    expected=None 表示断言该关键字不存在。
    """
    m = assert_minion_exists(game, pos, msg=msg)
    actual = m.keywords.get(keyword)
    if actual != expected:
        raise AssertionError(
            f"位置 {_fmt_pos(pos)} 的 [{m.name}] 关键字 [{keyword}]={actual!r}，"
            f"期望 {expected!r}"
            + (f" | {msg}" if msg else "")
        )


def assert_minion_has_keyword(
    game: Game,
    pos: Tuple[int, int],
    keyword: str,
    msg: Optional[str] = None,
) -> None:
    """断言指定位置异象拥有某关键字（值可为任何真值）。"""
    m = assert_minion_exists(game, pos, msg=msg)
    if keyword not in m.keywords:
        raise AssertionError(
            f"位置 {_fmt_pos(pos)} 的 [{m.name}] 缺少关键字 [{keyword}]"
            + (f" | {msg}" if msg else "")
        )


def assert_minion_missing_keyword(
    game: Game,
    pos: Tuple[int, int],
    keyword: str,
    msg: Optional[str] = None,
) -> None:
    """断言指定位置异象没有某关键字。"""
    m = assert_minion_exists(game, pos, msg=msg)
    if keyword in m.keywords:
        raise AssertionError(
            f"位置 {_fmt_pos(pos)} 的 [{m.name}] 不应有关键字 [{keyword}]"
            + (f" | {msg}" if msg else "")
        )


def assert_board_empty(
    game: Game,
    *positions: Tuple[int, int],
    msg: Optional[str] = None,
) -> None:
    """断言指定位置没有异象。"""
    for pos in positions:
        m = game.board.get_minion_at(pos)
        if m is not None:
            raise AssertionError(
                f"位置 {_fmt_pos(pos)} 应为空，但存在 [{m.name}]"
                + (f" | {msg}" if msg else "")
            )


def assert_hand_contains(
    player: Player,
    card_name: str,
    msg: Optional[str] = None,
) -> None:
    """断言玩家手牌中包含指定名称的卡牌。"""
    names = [c.name for c in player.card_hand]
    if card_name not in names:
        raise AssertionError(
            f"{player.name} 手牌 {names} 中不包含 [{card_name}]"
            + (f" | {msg}" if msg else "")
        )


def assert_hand_missing(
    player: Player,
    card_name: str,
    msg: Optional[str] = None,
) -> None:
    """断言玩家手牌中不包含指定名称的卡牌。"""
    names = [c.name for c in player.card_hand]
    if card_name in names:
        raise AssertionError(
            f"{player.name} 手牌不应包含 [{card_name}]"
            + (f" | {msg}" if msg else "")
        )


def assert_event_count(
    game: Game,
    event_type: str,
    expected: int,
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    msg: Optional[str] = None,
) -> None:
    """断言当前回合某事件的出现次数。"""
    events = game.history._current.query_events(event_type=event_type, filter_fn=filter_fn)
    actual = len(events)
    if actual != expected:
        raise AssertionError(
            f"事件 [{event_type}] 出现 {actual} 次，期望 {expected}"
            + (f" | {msg}" if msg else "")
        )


def assert_player_hp(
    player: Player,
    expected: int,
    msg: Optional[str] = None,
) -> None:
    """断言玩家当前生命值。"""
    if player.health != expected:
        raise AssertionError(
            f"{player.name} HP={player.health}，期望 {expected}"
            + (f" | {msg}" if msg else "")
        )
