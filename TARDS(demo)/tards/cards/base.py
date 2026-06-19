from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from ..constants import (
    EVENT_DEPLOY, EVENT_DEATH, EVENT_SACRIFICE, GENERAL_KEYWORDS,
    EVENT_BEFORE_DAMAGE, EVENT_DAMAGED, EVENT_AFTER_DAMAGE,
    EVENT_BEFORE_ATTACK, EVENT_ATTACKED, EVENT_AFTER_ATTACK,
    EVENT_BEFORE_DESTROY, EVENT_DESTROYED, EVENT_AFTER_DESTROY,
    EVENT_BEFORE_DEPLOY, EVENT_DEPLOYED, EVENT_AFTER_DEPLOY,
)
from ..core.cost import Cost

if TYPE_CHECKING:
    from ..core.player import Player
    from ..core.board import Board
    from ..game import Game


class Card:
    """所有卡牌的基类。

    每张卡牌实例都可以持有自己的事件监听器（通过 ``on()`` 注册），
    并通过 ``move_to()`` 统一追踪所在位置（deck/hand/discard/board/exile）。
    """

    # 通用时间节点回调（可在实例创建后动态设置）
    on_game_start: Optional[Callable] = None

    def __init__(self, name: str, cost: Cost, targets: Callable[["Player", "Board"], List[Any]],
                 on_turn_start: Optional[Callable] = None,
                 on_turn_end: Optional[Callable] = None,
                 on_phase_start: Optional[Callable] = None,
                 on_phase_end: Optional[Callable] = None):
        self.name = name
        self.cost = cost
        self.can_play = True
        self.targets = targets
        self.echo_level = 0  # 回响等级，0 表示无回响
        self.on_turn_start = on_turn_start
        self.on_turn_end = on_turn_end
        self.on_phase_start = on_phase_start
        self.on_phase_end = on_phase_end
        self._card_cost_modifiers: List[Callable[["Card", "Cost"], None]] = []
        self.asset_id: Optional[str] = None
        self.asset_back_id: Optional[str] = None

        # === 堆叠机制 ===
        self.stack_count: int = 1
        self.stack_limit: int = 1

        # === 卡的位置与事件监听（引擎扩展）===
        self._location: Optional[str] = None  # "deck", "hand", "discard", "board", "exile"
        self._card_listeners: List[tuple] = []  # (event_type, listener_fn)
        self.owner: Optional["Player"] = None

        # === 展示标记（被对手见过的牌）===
        self._shown_to_opponent: bool = False

    def __repr__(self) -> str:
        return f"{self.name}({self.cost})"

    @property
    def location(self) -> Optional[str]:
        return self._location

    # ----- 卡级别事件监听 API -----
    def on(self, event_type: str, listener: Callable) -> None:
        """注册此卡实例专属的事件监听器。当卡已有 owner 和 game 时立即生效。"""
        self._card_listeners.append((event_type, listener))
        board = getattr(self.owner, "board_ref", None)
        game = getattr(board, "game_ref", None) if board else None
        if game and hasattr(game, "event_bus"):
            game.event_bus.register(event_type, listener)

    def off_all(self) -> None:
        """注销此卡实例的所有事件监听器。"""
        board = getattr(self.owner, "board_ref", None)
        game = getattr(board, "game_ref", None) if board else None
        if game and hasattr(game, "event_bus"):
            for event_type, listener in self._card_listeners:
                game.event_bus.unregister(event_type, listener)
        self._card_listeners.clear()

    # ----- 统一移动接口 -----
    def move_to(self, new_location: str, game: Optional["Game"] = None) -> None:
        """统一移动接口。更新 location 并可选地触发 card_moved 事件。

        新增：卡牌离开手牌时，自动清理以本卡为 source 的费用修正。
        """
        old_location = self._location
        self._location = new_location

        # === 费用修正自动清理：手牌 → 非手牌 ===
        if old_location == "hand" and new_location != "hand":
            owner = getattr(self, "owner", None)
            if owner and hasattr(owner, "_cost_modifier_system"):
                removed = owner._cost_modifier_system.remove_by_source(self)
                if removed:
                    print(f"  [{self.name}] 离开手牌，清理 {removed} 个费用修正")
                removed_expire = owner._cost_modifier_system.expire("card_leave_hand")
                if removed_expire:
                    print(f"  [{self.name}] 离开手牌，清理 {removed_expire} 个临时费用修正")
            # 向后兼容：同时清理 _card_cost_modifiers
            if hasattr(self, "_card_cost_modifiers"):
                self._card_cost_modifiers.clear()
            # 恢复临时修改的攻防属性（如植物学家等手牌buff）
            if hasattr(self, '_original_attack'):
                self.attack = self._original_attack
                del self._original_attack
            if hasattr(self, '_original_health'):
                self.health = self._original_health
                del self._original_health

        # 卡牌离开战场/场上时，自动清理 Card.on() 等监听器
        if old_location in ("board", "hand") and new_location in ("graveyard", "discard", "exiled"):
            if game and hasattr(game, "lifecycle"):
                game.lifecycle.clear_card(self, reason=f"{old_location}->{new_location}")
            else:
                self.off_all()

        if game and hasattr(game, "event_bus"):
            game.emit_event("card_moved", card=self, from_loc=old_location, to_loc=new_location)
