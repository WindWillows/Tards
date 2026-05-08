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


# =============================================================================
# 统一目标选择器
# =============================================================================

def target(source: str, **conditions):
    """统一目标选择器。

    通过 source 指定目标属性，通过 conditions 叠加额外判断条件。
    返回一个 (player, board) -> List[Any] 的 callable。

    Args:
        source: 目标来源属性
            - "minion"      场上异象
            - "hand"        手牌
            - "deck"        牌库
            - "discard"     弃牌堆
            - "position"    棋盘位置
            - "player"      玩家
            - "column"      列号

        conditions: 额外判断条件
            - friendly=True/False     仅友方（minion/player）
            - enemy=True/False        仅敌方（minion/player）
            - alive=True/False        仅存活（minion，默认 True）
            - keyword="xxx"           关键词（minion/hand/deck/discard）
            - tag="xxx"               标签（minion）
            - injured=True/False      受伤（minion）
            - empty=True/False        空格（position）
            - range=[...]             范围（column）
            - card_type="xxx"         卡牌类型（hand/deck/discard）
            - custom_filter=callable  自定义过滤函数
    """
    friendly = conditions.get("friendly", True)
    enemy = conditions.get("enemy", True)
    alive = conditions.get("alive", True)
    keyword = conditions.get("keyword")
    tag = conditions.get("tag")
    injured = conditions.get("injured", False)
    empty = conditions.get("empty", False)
    range_ = conditions.get("range")
    card_type = conditions.get("card_type")
    custom_filter = conditions.get("custom_filter")

    def _selector(player, board):
        # 1. 根据 source 获取基础集合
        if source == "minion":
            candidates = list(board.minion_place.values())
            if alive:
                candidates = [m for m in candidates if m.is_alive()]
        elif source == "hand":
            candidates = list(player.card_hand)
        elif source == "deck":
            candidates = list(player.card_deck)
        elif source == "discard":
            candidates = list(player.card_dis)
        elif source == "position":
            if friendly and not enemy:
                rows = player.get_friendly_rows()
            elif enemy and not friendly:
                if board.game_ref:
                    opponent = board.game_ref.p2 if player == board.game_ref.p1 else board.game_ref.p1
                    rows = opponent.get_friendly_rows()
                else:
                    rows = []
            else:
                rows = list(range(board.SIZE))
            candidates = [(r, c) for r in rows for c in range(5)]
            if empty:
                occupied = {m.position for m in board.minion_place.values()}
                candidates = [pos for pos in candidates if pos not in occupied]
        elif source == "player":
            if board.game_ref:
                candidates = list(board.game_ref.players)
                if friendly and not enemy:
                    candidates = [p for p in candidates if p == player]
                elif enemy and not friendly:
                    candidates = [p for p in candidates if p != player]
            else:
                candidates = []
        elif source == "column":
            candidates = range_ if range_ is not None else list(range(board.SIZE))
        else:
            raise ValueError(f"未知的目标来源: {source}")

        # 2. 应用通用过滤条件
        result = []
        for item in candidates:
            # 阵营过滤（仅适用于有 owner 的对象）
            if hasattr(item, "owner"):
                is_friendly = item.owner == player
                if is_friendly and not friendly:
                    continue
                if not is_friendly and not enemy:
                    continue

            # 关键词过滤
            if keyword:
                kw = None
                if hasattr(item, "keywords"):
                    kw = item.keywords.get(keyword)
                elif hasattr(item, "base_keywords"):
                    kw = item.base_keywords.get(keyword)
                if not kw:
                    continue

            # 标签过滤
            if tag:
                tags = getattr(item, "tags", set())
                if tag not in tags:
                    continue

            # 受伤过滤
            if injured:
                if not hasattr(item, "current_health") or not hasattr(item, "current_max_health"):
                    continue
                if item.current_health >= item.current_max_health:
                    continue

            # 卡牌类型过滤
            if card_type:
                from .cards import MinionCard, Strategy, MineralCard
                type_map = {
                    "minion": MinionCard,
                    "strategy": Strategy,
                    "mineral": MineralCard,
                }
                expected_type = type_map.get(card_type)
                if expected_type and not isinstance(item, expected_type):
                    continue

            # 自定义过滤
            if custom_filter and not custom_filter(item):
                continue

            result.append(item)

        return result

    return _selector


def target_mix(*selectors):
    """混合多个目标选择器的结果，去重。

    用于需要同时指向多种目标类型的效果（如"指向场上异象或敌方玩家"）。
    """
    def _selector(player, board):
        result = []
        seen = set()
        for sel in selectors:
            for item in sel(player, board):
                key = id(item)
                if key not in seen:
                    result.append(item)
                    seen.add(key)
        return result
    return _selector
