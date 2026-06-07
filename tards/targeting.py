#!/usr/bin/env python3
"""指向模块（Targeting System）。

架构：
  1. 目标提取区（TargetPool）：枚举所有可被指向的游戏对象。
  2. 请求发起：指向起点构造 TargetingRequest 并提交给 TargetingSystem。
  3. 请求接收区（TargetingSystem）：广播请求、计算合法目标、阻塞等待玩家选择、
     广播结果。

指向动作规范为单目标。多目标效果由调用方串行发起多次独立请求，
收集结果后统一传入效果函数。

新增：支持自然数数字目标（如"第n行"返回 1~5 的数字选项）。
"""

from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .board import Board
    from .cards import Minion
    from .game import Game
    from .player import Player


# =============================================================================
# 数据对象
# =============================================================================

@dataclass
class TargetingRequest:
    """指向请求。

    Fields:
        source: 指向起点（策略卡、异象、玩家等）。
        scope_fn: 目标范围过滤函数 (player, board) -> List[Any]。
                  当 numeric_options 为 None 时必须提供。
        numeric_options: 数字选项列表（如 [1,2,3,4,5]）。
                         若提供，则 scope_fn 被忽略，合法目标直接为这些数字。
        count: 需要选择的目标数量（默认 1）。
               注：TargetingSystem.request_target 始终返回单目标；count > 1 的场景
               由调用方拆分多次请求，或在 GUI 本地层自行处理多选。
        allow_repeat: 是否允许重复选择同一目标。
        prompt: 给玩家的提示文字。
        deciding_player: 谁来做选择。None 默认为 current_player。
        on_confirm: 选择完成后回调，接收 target（单目标时）或 List[target]（多目标时）。
        on_cancel: 取消时回调。
    """
    source: Any = None
    scope_fn: Optional[Callable[["Player", "Board"], List[Any]]] = None
    numeric_options: Optional[List[int]] = None
    count: int = 1
    allow_repeat: bool = False
    prompt: str = "请选择目标"
    deciding_player: Optional["Player"] = None
    on_confirm: Callable[[Any], None] = field(default=lambda _: None)
    on_cancel: Callable[[], None] = field(default=lambda: None)


@dataclass
class TargetingAction:
    """指向动作结果：起点 + 目标。"""
    source: Any
    target: Any


# =============================================================================
# 目标提取区
# =============================================================================

class TargetPool:
    """枚举所有可能被指向的游戏对象。

    对象池包括：
      - 棋盘格坐标 (row, col)
      - 已部署的异象（含存活与死亡，过滤由 scope_fn 负责）
      - 玩家
      - 卡牌（手牌 / 牌库 / 弃牌堆，携带 _location 标记）
      - 自然数数字（由 numeric_options 直接提供，不经过对象池）
    """

    @staticmethod
    def extract_positions(board: "Board") -> List[Tuple[int, int]]:
        """棋盘格坐标。"""
        size = getattr(board, "SIZE", 5)
        return [(r, c) for r in range(size) for c in range(size)]

    @staticmethod
    def extract_minions(board: "Board") -> List["Minion"]:
        """已部署的异象。"""
        return list(board.minion_place.values())

    @staticmethod
    def extract_players(game: "Game") -> List["Player"]:
        """玩家。"""
        return list(getattr(game, "players", []))

    @staticmethod
    def extract_cards(player: "Player") -> List[Any]:
        """卡牌（手牌、牌库、弃牌堆），并确保携带 _location 标记。"""
        cards = []
        for c in getattr(player, "card_hand", []):
            if hasattr(c, "move_to"):
                c._location = "hand"
            cards.append(c)
        for c in getattr(player, "card_deck", []):
            if hasattr(c, "move_to"):
                c._location = "deck"
            cards.append(c)
        for c in getattr(player, "card_dis", []):
            if hasattr(c, "move_to"):
                c._location = "discard"
            cards.append(c)
        return cards


# =============================================================================
# 请求接收区
# =============================================================================

class TargetingSystem:
    """处理指向请求：广播 -> 过滤 -> 阻塞等待 -> 广播结果。"""

    def __init__(self, game: "Game"):
        self.game = game

    # -------------------------------------------------------------------------
    # 公共 API
    # -------------------------------------------------------------------------

    def request_target(self, request: TargetingRequest) -> Optional[Any]:
        """同步阻塞请求单个目标。

        流程：
          1. 广播 targeting_request 事件。
          2. 计算合法目标列表 valid_targets。
          3. 调用 game.targeting_provider 阻塞等待玩家选择。
          4. 广播 targeting_completed / targeting_cancelled 事件。
          5. 返回 target 或 None。
        """
        valid_targets = self.get_valid_targets(request)

        # 广播请求（携带已计算的合法目标，供 GUI 直接渲染）
        self._emit("targeting_request", request=request, valid_targets=valid_targets)

        # 无合法目标：直接取消
        if not valid_targets:
            self._emit("targeting_cancelled", request=request, reason="无合法目标")
            request.on_cancel()
            return None

        # 唯一目标是 None（非指向性）：直接确认
        if len(valid_targets) == 1 and valid_targets[0] is None:
            result = valid_targets[0]
            self._emit("targeting_completed", request=request, target=result)
            request.on_confirm(result)
            return result

        # 通过 provider 阻塞等待玩家选择
        result = self._wait_for_choice(request, valid_targets)

        if result is not None:
            self._emit("targeting_completed", request=request, target=result)
            request.on_confirm(result)
        else:
            self._emit("targeting_cancelled", request=request, reason="玩家取消")
            request.on_cancel()
        return result

    def get_valid_targets(self, request: TargetingRequest) -> List[Any]:
        """根据请求计算合法目标列表。"""
        # 数字选项优先
        if request.numeric_options is not None:
            return list(request.numeric_options)

        if request.scope_fn is None:
            return []

        player = request.deciding_player or getattr(self.game, "current_player", None)
        board = getattr(self.game, "board", None)
        if player is None or board is None:
            return []

        try:
            candidates = request.scope_fn(player, board)
        except Exception as e:
            print(f"  [指向错误] scope_fn 执行异常: {e}")
            return []

        # 通用过滤：虚化
        filtered = []
        for item in candidates:
            if hasattr(item, "keywords") and item.keywords.get("虚化", False) or hasattr(item, "temp_keywords") and item.temp_keywords.get("虚化", False):
                continue
            filtered.append(item)
        return filtered

    # -------------------------------------------------------------------------
    # 内部辅助
    # -------------------------------------------------------------------------

    def _wait_for_choice(self, request: TargetingRequest, valid_targets: List[Any]) -> Optional[Any]:
        """阻塞等待玩家选择。"""
        provider = getattr(self.game, "targeting_provider", None)
        if provider is not None:
            try:
                return provider(self.game, request, valid_targets)
            except Exception as e:
                print(f"  [指向错误] targeting_provider 异常: {e}")
                return None

        # 无 provider（AI / 命令行回退）：随机选第一个
        import random
        return random.choice(valid_targets) if valid_targets else None

    def _emit(self, event_type: str, **kwargs) -> Optional[Any]:
        """安全发射事件。"""
        emit_fn = getattr(self.game, "emit_event", None)
        if emit_fn is not None:
            return emit_fn(event_type, **kwargs)
        return None


# =============================================================================
# 攻击目标候选（保留，供 GUI 攻击预设使用）
# =============================================================================

def get_attack_target_candidates(minion: "Minion", game: "Game") -> List[Any]:
    """返回该异象当前可以攻击的合法目标（包含敌方异象和敌方玩家）。

    有视野的异象可以攻击视野范围内的任意敌方异象（含潜水/潜行，因为指向发生在出牌阶段）；
    无视野的异象只能攻击同列最前排的敌方异象。
    """
    board = game.board
    vision_range = minion.keywords.get("视野", 0)
    base_col = minion.position[1]
    opponent = game.p2 if minion.owner == game.p1 else game.p1

    if vision_range > 0:
        enemies = [m for m in board.minion_place.values()
                   if m.owner != minion.owner and m.is_alive()
                   and abs(m.position[1] - base_col) <= vision_range
                   and not (m.keywords.get("虚化", False) or m.temp_keywords.get("虚化", False))]
        candidates = enemies + [opponent]
    else:
        front = board.get_front_minion(base_col, minion.owner, attacker=minion)
        candidates = [front] if front else [opponent]
    return candidates


# =============================================================================
# 兼容 shim（已废弃）
# =============================================================================

def get_deploy_extra_targets(
    player: "Player",
    board: "Board",
    card: Any,
) -> Tuple[List[Any], int, bool]:
    """[已废弃] 异象卡统一使用 extra_targeting_stages 处理额外指向。"""
    return [], 0, False
