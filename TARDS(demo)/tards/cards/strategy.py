from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
import inspect
from ..core.cost import Cost
from .base import Card

if TYPE_CHECKING:
    from ..core.player import Player
    from ..core.board import Board
    from ..game import Game


class Strategy(Card):
    """策略卡。打出后立即生效。"""

    def __init__(
        self,
        name: str,
        cost: Cost,
        effect_fn: Optional[Callable[["Player", Any, "Game"], bool]],
        targets: Callable[["Player", "Board"], List[Any]],
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
        hidden_keywords: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.effect_fn = effect_fn
        self.hidden_keywords = hidden_keywords or {}

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        if self.effect_fn is None:
            return True
        # 指向保护（"取消该指向"等机制）
        if game.is_target_protected(target, self):
            return True
        sig = inspect.signature(self.effect_fn)
        param_count = len(sig.parameters)
        if param_count >= 5:
            # 第5个参数传入 Strategy 实例自身，供 effect_fn 注册卡级别监听器
            return self.effect_fn(player, target, game, extra_targets or [], self)
        elif param_count >= 4:
            return self.effect_fn(player, target, game, extra_targets or [])
        else:
            return self.effect_fn(player, target, game)
