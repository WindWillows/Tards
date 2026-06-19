from typing import Any, Callable, List, Optional, TYPE_CHECKING
from ..core.cost import Cost
from .base import Card

if TYPE_CHECKING:
    from ..core.player import Player
    from ..game import Game


class MineralCard(Card):
    """矿物卡（离散卡包资源）。
    
    兑换时支付 exchange_cost，兑换后进入手牌。
    打出时无费用，直接产生效果。
    """

    def __init__(
        self,
        name: str,
        mineral_type: str,  # I, G, D, M
        exchange_cost: Cost,
        play_effect: Optional[Callable[["Player", "Game"], Any]] = None,
        stack_limit: int = 1,
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
    ):
        super().__init__(name, Cost(), lambda p, b: [None], on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.exchange_cost = exchange_cost
        self.mineral_type = mineral_type
        self.stack_limit = stack_limit
        self.play_effect_fn = play_effect
        self.tags: List[str] = []

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        if self.play_effect_fn:
            self.play_effect_fn(player, game)
        return True
