"""事件追踪器 — 在代码块执行期间记录所有事件，支持断言。"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from tards.game import Game


class EventSpy:
    """上下文管理器：临时监听所有事件并记录。

    用法：
        with EventSpy(game) as spy:
            game.emit_event(EVENT_PHASE_START, ...)
            spy.assert_fired(EVENT_PHASE_START, phase="resolve")
            spy.assert_count(EVENT_CARD_PLAYED, 2)
    """

    def __init__(self, game: Game) -> None:
        self.game = game
        self.events: List[Tuple[str, Dict[str, Any]]] = []
        self._lid: Optional[int] = None

    def __enter__(self) -> EventSpy:
        def _callback(event: Any, g: Any) -> None:
            # 浅拷贝 data（保留对象引用，以便用 ==/is 匹配 Player/Minion）
            self.events.append((event.type, dict(event.data)))

        self._lid = self.game.history.listen("*", _callback)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._lid is not None:
            self.game.history.unlisten(self._lid)
            self._lid = None

    # ------------------------------------------------------------------
    # 查询 API
    # ------------------------------------------------------------------

    def fired(
        self,
        event_type: str,
        **kwargs: Any,
    ) -> bool:
        """检查是否触发过满足条件的事件。"""
        for typ, data in self.events:
            if typ != event_type:
                continue
            if all(data.get(k) == v for k, v in kwargs.items()):
                return True
        return False

    def count(
        self,
        event_type: str,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """统计某事件的触发次数。"""
        total = 0
        for typ, data in self.events:
            if typ != event_type:
                continue
            if filter_fn is not None and not filter_fn(data):
                continue
            total += 1
        return total

    def of_type(self, event_type: str) -> List[Dict[str, Any]]:
        """获取某类型事件的所有 data 列表。"""
        return [data for typ, data in self.events if typ == event_type]

    def types(self) -> List[str]:
        """获取按顺序出现的事件类型列表。"""
        return [typ for typ, _ in self.events]

    # ------------------------------------------------------------------
    # 断言 API
    # ------------------------------------------------------------------

    def assert_fired(
        self,
        event_type: str,
        msg: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """断言至少触发过一次满足条件的事件。"""
        if self.fired(event_type, **kwargs):
            return
        details = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        raise AssertionError(
            f"事件 [{event_type}]({details}) 未触发"
            + (f" | {msg}" if msg else "")
        )

    def assert_not_fired(
        self,
        event_type: str,
        msg: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """断言没有触发过满足条件的事件。"""
        if not self.fired(event_type, **kwargs):
            return
        details = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        raise AssertionError(
            f"事件 [{event_type}]({details}) 不应触发，但被触发了"
            + (f" | {msg}" if msg else "")
        )

    def assert_count(
        self,
        event_type: str,
        expected: int,
        msg: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> None:
        """断言某事件的触发次数。"""
        actual = self.count(event_type, filter_fn=filter_fn)
        if actual != expected:
            raise AssertionError(
                f"事件 [{event_type}] 触发 {actual} 次，期望 {expected}"
                + (f" | {msg}" if msg else "")
            )

    def assert_order(
        self,
        *event_types: str,
        msg: Optional[str] = None,
    ) -> None:
        """断言事件按指定顺序出现（不要求连续，只要求相对顺序）。"""
        idx = 0
        for typ, _ in self.events:
            if idx < len(event_types) and typ == event_types[idx]:
                idx += 1
        if idx == len(event_types):
            return

        found = [t for t, _ in self.events if t in event_types]
        raise AssertionError(
            f"事件顺序 {found} 不符合期望 {list(event_types)}"
            + (f" | {msg}" if msg else "")
        )

    def assert_exact_order(
        self,
        *event_types: str,
        msg: Optional[str] = None,
    ) -> None:
        """断言事件按指定顺序**连续**出现。"""
        actual = [t for t, _ in self.events]
        for i in range(len(actual) - len(event_types) + 1):
            if actual[i : i + len(event_types)] == list(event_types):
                return
        raise AssertionError(
            f"事件序列 {actual} 中未找到连续子序列 {list(event_types)}"
            + (f" | {msg}" if msg else "")
        )
