from typing import List, Any, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player
    from .board import Board
    from .cards import Minion


def target_friendly_positions(player: "Player", board: "Board") -> List[Tuple[int, int]]:
    rows = player.get_friendly_rows()
    return [(r, c) for r in rows for c in range(5)]


def target_enemy_minions(player: "Player", board: "Board") -> List["Minion"]:
    return [m for m in board.minion_place.values() if m.owner != player]


def target_any_minion(player: "Player", board: "Board") -> List["Minion"]:
    return list(board.minion_place.values())


def target_self(player: "Player", board: "Board") -> List["Player"]:
    return [player]


def target_none(player: "Player", board: "Board") -> List[Any]:
    return [None]


def target_enemy_player(player: "Player", board: "Board") -> List["Player"]:
    if board.game_ref:
        return [p for p in board.game_ref.players if p != player]
    return []


def target_friendly_minions(player: "Player", board: "Board") -> List["Minion"]:
    return [m for m in board.minion_place.values() if m.owner == player]


def target_hand_minions(player: "Player", board: "Board" = None) -> List[Any]:
    """返回玩家手牌中的所有单位卡（MinionCard）。"""
    from .cards import MinionCard
    return [c for c in player.card_hand if isinstance(c, MinionCard)]
