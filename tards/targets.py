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
    """返回玩家手牌中的所有异象卡（MinionCard）。"""
    from .cards import MinionCard
    return [c for c in player.card_hand if isinstance(c, MinionCard)]


# =============================================================================
# 扩展：高频指向过滤器
# =============================================================================

def target_injured_minions(player: "Player", board: "Board",
                           friendly: bool = False, enemy: bool = True) -> List["Minion"]:
    """返回场上受伤（当前生命值 < 最大生命值）的异象。

    Args:
        friendly: 是否包含友方异象
        enemy: 是否包含敌方异象
    """
    result = []
    for m in board.minion_place.values():
        if not m.is_alive():
            continue
        is_friendly = m.owner == player
        if is_friendly and not friendly:
            continue
        if not is_friendly and not enemy:
            continue
        if m.current_health < m.current_max_health:
            result.append(m)
    return result


def target_minions_with_keyword(player: "Player", board: "Board",
                                keyword: str,
                                friendly: bool = True, enemy: bool = True) -> List["Minion"]:
    """返回场上具有指定关键词的存活异象。

    Args:
        friendly: 是否包含友方
        enemy: 是否包含敌方
    """
    result = []
    for m in board.minion_place.values():
        if not m.is_alive():
            continue
        is_friendly = m.owner == player
        if is_friendly and not friendly:
            continue
        if not is_friendly and not enemy:
            continue
        if m.keywords.get(keyword):
            result.append(m)
    return result


def target_friendly_minions_with_keyword(player: "Player", board: "Board",
                                         keyword: str) -> List["Minion"]:
    """返回场上具有指定关键词的友方存活异象。"""
    return target_minions_with_keyword(player, board, keyword, friendly=True, enemy=False)


def target_enemy_minions_with_keyword(player: "Player", board: "Board",
                                      keyword: str) -> List["Minion"]:
    """返回场上具有指定关键词的敌方存活异象。"""
    return target_minions_with_keyword(player, board, keyword, friendly=False, enemy=True)


def target_any_minion_or_enemy_player(player: "Player", board: "Board") -> List[Any]:
    """返回场上任意存活异象 + 敌方玩家（用于需要选择"一个目标"的效果）。"""
    result: List[Any] = [m for m in board.minion_place.values() if m.is_alive()]
    if board.game_ref:
        for p in board.game_ref.players:
            if p != player:
                result.append(p)
    return result


def target_any_minion_or_any_player(player: "Player", board: "Board") -> List[Any]:
    """返回场上任意存活异象 + 双方玩家。"""
    result: List[Any] = [m for m in board.minion_place.values() if m.is_alive()]
    if board.game_ref:
        result.extend(board.game_ref.players)
    return result


def target_minions_in_columns(player: "Player", board: "Board",
                              columns: List[int],
                              friendly: bool = True, enemy: bool = True) -> List["Minion"]:
    """返回指定列中的存活异象。"""
    result = []
    for m in board.minion_place.values():
        if not m.is_alive():
            continue
        if m.position[1] not in columns:
            continue
        is_friendly = m.owner == player
        if is_friendly and not friendly:
            continue
        if not is_friendly and not enemy:
            continue
        result.append(m)
    return result


def target_friendly_positions_with_minion(player: "Player", board: "Board") -> List[Tuple[int, int]]:
    """返回有友方存活异象占据的位置。"""
    return [m.position for m in board.minion_place.values()
            if m.is_alive() and m.owner == player]


def target_empty_friendly_positions(player: "Player", board: "Board") -> List[Tuple[int, int]]:
    """返回友方区域中的空位。"""
    rows = player.get_friendly_rows()
    all_positions = {(r, c) for r in rows for c in range(5)}
    occupied = {m.position for m in board.minion_place.values()}
    return [pos for pos in all_positions if pos not in occupied]


def target_hand_cards(player: "Player", board: "Board" = None) -> List[Any]:
    """返回玩家手牌中的所有卡牌（不限类型）。"""
    return list(player.card_hand)


def target_hand_strategies(player: "Player", board: "Board" = None) -> List[Any]:
    """返回玩家手牌中的所有策略卡（Strategy）。"""
    from .cards import Strategy
    return [c for c in player.card_hand if isinstance(c, Strategy)]


def target_discard_pile(player: "Player", board: "Board" = None) -> List[Any]:
    """返回玩家弃牌堆中的所有卡牌。"""
    return list(player.card_dis)


def target_deck(player: "Player", board: "Board" = None) -> List[Any]:
    """返回玩家牌库中的所有卡牌。"""
    return list(player.card_deck)
