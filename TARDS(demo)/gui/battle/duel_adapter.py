"""对战控制器适配器。

将 `LocalDuel` 与 `NetworkDuel` 的差异收敛到这里，
使 `BattleFrame` 不再依赖 `isinstance(self.duel, NetworkDuel)` 分支。
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from local_duel import LocalDuel
from tards.net_game import NetworkDuel


class DuelAdapter:
    """统一本地/网络对战控制器的接口。"""

    def __init__(self, duel: Any):
        self._duel = duel

    # ------------------------------------------------------------------
    # 透传属性
    # ------------------------------------------------------------------
    @property
    def game(self) -> Optional[Any]:
        return self._duel.game

    @property
    def local_player(self) -> Any:
        return self._duel.local_player

    @property
    def is_remote(self) -> bool:
        """是否为网络对战。"""
        return isinstance(self._duel, NetworkDuel)

    # ------------------------------------------------------------------
    # 回调透传（读写）
    # ------------------------------------------------------------------
    @property
    def local_turn_callback(self) -> Optional[Callable[[], None]]:
        return getattr(self._duel, "local_turn_callback", None)

    @local_turn_callback.setter
    def local_turn_callback(self, value: Optional[Callable[[], None]]) -> None:
        self._duel.local_turn_callback = value

    @property
    def game_over_callback(self) -> Optional[Callable[[Optional[str]], None]]:
        return getattr(self._duel, "game_over_callback", None)

    @game_over_callback.setter
    def game_over_callback(self, value: Optional[Callable[[Optional[str]], None]]) -> None:
        self._duel.game_over_callback = value

    @property
    def discover_request_callback(self) -> Optional[Callable[[List[str]], None]]:
        return getattr(self._duel, "discover_request_callback", None)

    @discover_request_callback.setter
    def discover_request_callback(self, value: Optional[Callable[[List[str]], None]]) -> None:
        self._duel.discover_request_callback = value

    @property
    def choice_request_callback(self) -> Optional[Callable[[List[Any], str], None]]:
        return getattr(self._duel, "choice_request_callback", None)

    @choice_request_callback.setter
    def choice_request_callback(self, value: Optional[Callable[[List[Any], str], None]]) -> None:
        self._duel.choice_request_callback = value

    @property
    def targeting_request_callback(self) -> Optional[Callable[[Any, List[Any]], None]]:
        return getattr(self._duel, "targeting_request_callback", None)

    @targeting_request_callback.setter
    def targeting_request_callback(self, value: Optional[Callable[[Any, List[Any]], None]]) -> None:
        self._duel.targeting_request_callback = value

    @property
    def mulligan_request_callback(self) -> Optional[Callable[[Any], None]]:
        return getattr(self._duel, "mulligan_request_callback", None)

    @mulligan_request_callback.setter
    def mulligan_request_callback(self, value: Optional[Callable[[Any], None]]) -> None:
        self._duel.mulligan_request_callback = value

    @property
    def resolve_step_callback(self) -> Optional[Callable[[], None]]:
        return getattr(self._duel, "resolve_step_callback", None)

    @resolve_step_callback.setter
    def resolve_step_callback(self, value: Optional[Callable[[], None]]) -> None:
        self._duel.resolve_step_callback = value

    # ------------------------------------------------------------------
    # 提交通用方法
    # ------------------------------------------------------------------
    def submit_local_action(self, action: Dict[str, Any]) -> None:
        self._duel.submit_local_action(action)

    def submit_local_targeting(self, target: Any) -> None:
        self._duel.submit_local_targeting(target)

    def submit_local_discover(self, chosen: str) -> None:
        self._duel.submit_local_discover(chosen)

    def submit_local_choice(self, chosen: str) -> None:
        self._duel.submit_local_choice(chosen)

    def submit_local_mulligan(self, indices: List[int]) -> None:
        self._duel.submit_local_mulligan(indices)

    # ------------------------------------------------------------------
    # 运行与关闭
    # ------------------------------------------------------------------
    def run_game(self, opponent: Any, *, logger: Optional[Any] = None) -> None:
        """统一启动入口。"""
        self._duel.run_game(opponent, logger=logger)

    def close(self) -> None:
        """关闭对战。"""
        if hasattr(self._duel, "close"):
            self._duel.close()

    def force_terminate(self) -> None:
        """强制终止对战并释放所有阻塞式输入等待。"""
        # 注入一个无害 action 以唤醒 LocalDuel 的 action_provider
        if hasattr(self._duel, "_local_action"):
            self._duel._local_action = {"type": "brake"}
        for attr in (
            "_local_action_event",
            "_discover_event",
            "_choice_event",
            "_targeting_event",
            "_mulligan_event",
        ):
            event = getattr(self._duel, attr, None)
            if event is not None:
                event.set()

    # ------------------------------------------------------------------
    # 语义抹平
    # ------------------------------------------------------------------
    @property
    def display_player(self) -> Optional[Any]:
        """手牌与资源面板应显示的玩家。

        本地对战显示当前回合玩家；网络对战始终显示本地玩家。
        """
        game = self.game
        if game is None:
            return self.local_player
        return self.local_player if self.is_remote else game.current_player

    def can_operate(self, player: Optional[Any] = None) -> bool:
        """当前是否允许对 `player` 进行操作。

        网络对战中只允许操作本地玩家；本地对战中由调用方保证回合/阶段语义。
        """
        if player is None:
            return False
        if self.is_remote:
            return player is self.local_player
        return True

    @property
    def needs_continuous_refresh(self) -> bool:
        """是否需要每 tick 无条件刷新 UI（网络对战需要）。"""
        return self.is_remote

    @property
    def mulligan_waits_for_remote(self) -> bool:
        """Mulligan 确认后是否需要等待远端。"""
        return self.is_remote

    @property
    def supports_local_log_ui(self) -> bool:
        """是否把结构化日志实时回调到 GUI。"""
        return isinstance(self._duel, LocalDuel)

    def hint_for_active(self, active: Optional[Any]) -> str:
        """根据当前玩家生成提示文本。"""
        if not active:
            return "游戏加载中..."
        if self.is_remote:
            return "轮到你的行动" if active is self.local_player else "等待对手行动..."
        return f"轮到 {active.name} 行动"
