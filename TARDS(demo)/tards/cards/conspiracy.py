from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from ..core.cost import Cost
from .base import Card

if TYPE_CHECKING:
    from ..core.player import Player
    from ..core.board import Board
    from ..game import Game


class Conspiracy(Card):
    """阴谋卡。激活后进入活跃阴谋区，条件满足时触发。

    通过 EventBus 的通配符监听器 '*' 监听所有事件，
    condition_fn 自行判断是否响应。
    """

    def __init__(
        self,
        name: str,
        cost: Cost,
        condition_fn: Callable[["Game", Dict[str, Any], "Player"], bool],
        effect_fn: Callable[["Game", Dict[str, Any], "Player"], Any],
        targets: Callable[["Player", "Board"], List[Any]],
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.condition_fn = condition_fn
        self.effect_fn = effect_fn
        self._listener_owner_id: Optional[int] = None  # EventBus 批量注销用
