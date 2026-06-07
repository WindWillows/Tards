"""
GameHistory 纯事件日志模块（v3.0）

仅记录对局进行中与异象使用相关的关键历史事件，不做任何预计算。
外部通过 query_events + filter_fn 按需筛选并实时计数。

架构原则：
1. 零硬编码计数器 — TurnRecord 只存 _event_log，不存 cards_played 等聚合字段。
2. 零领域查询 — GameHistory 不提供 strategies_played_this_turn() 等 getter，
   这些逻辑全部下沉到 effect_utils.py 的条件筛选函数中。
3. 统一监听器 — listen / unlisten / unlisten_by_owner 统一 API，
   替代分散的 EventBus/Card.on()/effect_utils 中的手动注册方式。
   支持 once（只执行一次）、condition（条件过滤）、priority（优先级排序）。

设计原则
- 只存事件：TurnRecord 是单回合容器，GameHistory 管理全局存储与查询。
- 外部计算：effect_utils 提供基于 query_events + filter_fn 的筛选函数。
- 不替旧数据：支持 Game._state_log 等旧机制，GameHistory 作为新数据补充。
"""

from __future__ import annotations

import inspect
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

if TYPE_CHECKING:
    from .cards import Minion
    from .events import GameEvent
    from .player import Player


def _invoke_callback(callback: Callable, event: "GameEvent", game: Any) -> None:
    """调用监听器回调，自动匹配 (event) 或 (event, game) 两种签名"""
    try:
        sig = inspect.signature(callback)
        positional = [
            p for p in sig.parameters.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(positional) >= 2:
            callback(event, game)
        else:
            callback(event)
    except TypeError:
        # 签名检查失败时回退到单参数
        callback(event)


# =============================================================================
# 监听器元数据
# =============================================================================

@dataclass
class ListenerEntry:
    """GameHistory 统一监听器的条目"""

    id: int
    event_type: str
    callback: Callable
    owner: Optional[Any] = None
    once: bool = False
    condition: Optional[Callable[["GameEvent"], bool]] = None
    priority: int = 0
    wrapped_fn: Optional[Callable] = None
    owner_id: int = 0


# =============================================================================
# 回合容器
# =============================================================================

class TurnRecord:
    """单回合历史记录。只存原始事件，不做任何预计算。"""

    def __init__(self, turn: int):
        self.turn = turn
        self._event_log: List[Dict[str, Any]] = []

    def log_event(self, event_type: str, **kwargs) -> None:
        """记录一条原始事件到本回合流水"""
        entry: Dict[str, Any] = {"event_type": event_type}
        for k, v in kwargs.items():
            entry[k] = v
        self._event_log.append(entry)

    def query_events(
        self,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """查询本回合事件流水"""
        results: List[Dict[str, Any]] = []
        for entry in self._event_log:
            if event_type and entry.get("event_type") != event_type:
                continue
            if filter_fn and not filter_fn(entry):
                continue
            results.append(entry)
        return results

    def count_events(
        self,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        return len(self.query_events(event_type, filter_fn))


# =============================================================================
# 全局历史记录
# =============================================================================

class GameHistory:
    """
    全局机器日志：按回存储 TurnRecord，提供通用事件查询与统一监听器管理。

    使用方式：
        # 通用查询
        game.history.query_events(event_type=EVENT_CARD_PLAYED,
                                  filter_fn=lambda e: e["player"] is p1)
        game.history.count_events(event_type=EVENT_SACRIFICE,
                                  filter_fn=lambda e: e["player"] is p1)

        # 统一监听器
        lid = game.history.listen(EVENT_TURN_START, my_callback, owner=minion)
        game.history.unlisten_by_owner(minion)   # 异象离场时自动清理
    """

    def __init__(self, game: Any):
        self.game = game
        self._records: List[TurnRecord] = []
        self._current: TurnRecord = TurnRecord(0)

        # v3.0 统一监听器管理
        self._listener_entries: Dict[int, ListenerEntry] = {}
        self._next_listener_id = 1
        self._owner_registry: Dict[int, List[int]] = {}  # id(owner) -> [listener_id, ...]

    # ------------------------------------------------------------------
    # 回合推进
    # ------------------------------------------------------------------

    def advance_turn(self, turn: int) -> None:
        """推进新回合。将当前记录归档，创建新的 TurnRecord。"""
        self._records.append(self._current)
        self._current = TurnRecord(turn)

    # ------------------------------------------------------------------
    # 事件接收（由 Game.emit_event 调用）
    # ------------------------------------------------------------------

    def on_event(self, event_type: str, **kwargs) -> None:
        """接收到事件时，只写入当前回合的 _event_log，不做任何预计算。"""
        self._current.log_event(event_type, **kwargs)

    def _get_record(self, turn: Optional[int] = None) -> TurnRecord:
        if turn is None:
            return self._current
        if self._current.turn == turn:
            return self._current
        for rec in self._records:
            if rec.turn == turn:
                return rec
        return TurnRecord(turn)

    # =============================================================================
    # v3.0 统一监听器管理
    # =============================================================================

    def listen(
        self,
        event_type: str,
        callback: Callable[["GameEvent", Any], None],
        owner: Optional[Any] = None,
        once: bool = False,
        condition: Optional[Callable[["GameEvent"], bool]] = None,
        priority: int = 0,
    ) -> int:
        """统一注册事件监听器，返回 listener_id 便于注销。

        Args:
            event_type: 事件类型常量，如 EVENT_TURN_START 等
            callback:   回调函数，签名为 fn(event: GameEvent, game: Game) -> None
            owner:      绑定所有者（如 Minion），离场/出场时自动注销
            once:       是否只执行一次（执行后自动注销）
            condition:  条件过滤，签名 fn(event: GameEvent) -> bool
            priority:   优先级，越小越先执行（同优先级按注册顺序）

        Returns:
            listener_id: 监听器编号，可用于 unlisten(lid) 注销
        """
        lid = self._next_listener_id
        self._next_listener_id += 1

        def make_wrapper(lid_local: int) -> Callable[["GameEvent"], None]:
            def wrapper(event: "GameEvent") -> None:
                if condition is not None and not condition(event):
                    return
                try:
                    _invoke_callback(callback, event, self.game)
                except Exception as e:
                    import traceback

                    tb = traceback.format_exc().strip().splitlines()[-1]
                    print(f"  [监听器错误] {event_type} #{lid_local}: {e}  {tb}")
                if once:
                    self.unlisten(lid_local)

            return wrapper

        wrapped = make_wrapper(lid)

        # owner_id 策略：有 owner 用 id(owner)，无 owner 用 listener_id
        if owner is not None:
            owner_id = id(owner)
        else:
            owner_id = lid

        # 注册到底层 EventBus（Game 提供封装）
        self.game.register_listener(event_type, wrapped, priority, owner_id)

        entry = ListenerEntry(
            id=lid,
            event_type=event_type,
            callback=callback,
            owner=owner,
            once=once,
            condition=condition,
            priority=priority,
            wrapped_fn=wrapped,
            owner_id=owner_id,
        )
        self._listener_entries[lid] = entry
        if owner is not None:
            oid = id(owner)
            self._owner_registry.setdefault(oid, []).append(lid)

        return lid

    def listen_once(
        self,
        event_type: str,
        callback: Callable[["GameEvent", Any], None],
        owner: Optional[Any] = None,
        condition: Optional[Callable[["GameEvent"], bool]] = None,
        priority: int = 0,
    ) -> int:
        """注册只执行一次的监听器，执行后自动注销"""
        return self.listen(event_type, callback, owner, once=True, condition=condition, priority=priority)

    def unlisten(self, listener_id: int) -> bool:
        """注销指定监听器。成功返回 True，不存在返回 False。"""
        entry = self._listener_entries.pop(listener_id, None)
        if entry is None:
            return False
        self.game.unregister_listener(entry.event_type, entry.wrapped_fn)
        if entry.owner is not None:
            oid = id(entry.owner)
            reg = self._owner_registry.get(oid, [])
            if listener_id in reg:
                reg.remove(listener_id)
                if not reg:
                    self._owner_registry.pop(oid, None)
        return True

    def unlisten_by_owner(self, owner: Any) -> int:
        """注销某 owner（如 Minion/Card）名下的全部监听器。"""
        oid = id(owner)
        lids = list(self._owner_registry.pop(oid, []))
        count = 0
        for lid in lids:
            if self.unlisten(lid):
                count += 1
        return count

    def unlisten_all(self) -> int:
        """注销全部通过 GameHistory 注册的监听器。"""
        lids = list(self._listener_entries.keys())
        count = 0
        for lid in lids:
            if self.unlisten(lid):
                count += 1
        return count

    def listener_count(self, owner: Optional[Any] = None) -> int:
        """返回监听器总数。若指定 owner，只返回该 owner 的监听器数量。"""
        if owner is None:
            return len(self._listener_entries)
        oid = id(owner)
        return len(self._owner_registry.get(oid, []))

    def get_listeners_by_owner(self, owner: Any) -> List[ListenerEntry]:
        """返回绑定到指定 owner 的所有监听器条目。"""
        oid = id(owner)
        lids = self._owner_registry.get(oid, [])
        return [self._listener_entries[lid] for lid in lids if lid in self._listener_entries]

    # =============================================================================
    # v3.0 通用事件查询 API
    # =============================================================================

    def query_events(
        self,
        turn: Optional[int] = None,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """查询事件流水。

        Args:
            turn: 指定回合号。None 表示查询所有回合（当前 + 历史）。
            event_type: 过滤事件类型。None 表示所有类型。
            filter_fn: 自定义过滤函数，接收 event entry dict。

        Returns:
            匹配的事件列表（按时间顺序）。
        """
        if turn is not None:
            records = [self._get_record(turn)]
        else:
            records = self._records + [self._current]

        results: List[Dict[str, Any]] = []
        for rec in records:
            for entry in rec._event_log:
                if event_type and entry.get("event_type") != event_type:
                    continue
                if filter_fn and not filter_fn(entry):
                    continue
                results.append(entry)
        return results

    def count_events(
        self,
        turn: Optional[int] = None,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """统计事件流水中匹配事件的数目。"""
        return len(self.query_events(turn, event_type, filter_fn))

    def sum_events(
        self,
        turn: Optional[int] = None,
        event_type: Optional[str] = None,
        value_fn: Optional[Callable[[Dict[str, Any]], int]] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """对事件流水做数值聚合。

        Args:
            value_fn: 从事件 entry 提取数值。
                      默认尝试 amount / damage / delta / blood / heal / 0。
        """
        if value_fn is None:
            def _default_value_fn(e: Dict[str, Any]) -> int:
                return (
                    e.get("amount", 0)
                    or e.get("damage", 0)
                    or e.get("delta", 0)
                    or e.get("blood", 0)
                    or e.get("heal", 0)
                    or 0
                )
            value_fn = _default_value_fn

        total = 0
        for entry in self.query_events(turn, event_type, filter_fn):
            total += value_fn(entry)
        return total

    def query_cards_played(
        self,
        turn: Optional[int] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """查询卡牌打出事件，返回事件流水明细。"""
        from .constants import EVENT_CARD_PLAYED
        return self.query_events(turn, EVENT_CARD_PLAYED, filter_fn)

    def count_cards_played(
        self,
        turn: Optional[int] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """统计卡牌打出事件的数目。"""
        return len(self.query_cards_played(turn, filter_fn))

    # =============================================================================
    # 调试用摘要
    # =============================================================================

    def summary(self) -> Dict[str, Any]:
        """返回机器日志摘要（调试用）。只基于事件流统计。"""
        from .constants import (
            EVENT_CARD_PLAYED, EVENT_DEPLOYED, EVENT_SACRIFICE,
            EVENT_DEATH, EVENT_DRAW, EVENT_DISCARDED, EVENT_MILLED,
        )
        summary = {"turns": len(self._records) + (1 if self._current else 0)}
        for rec in self._records + [self._current]:
            for entry in rec._event_log:
                et = entry.get("event_type")
                if et == EVENT_CARD_PLAYED:
                    summary["card_played"] = summary.get("card_played", 0) + 1
                elif et == EVENT_DEPLOYED:
                    summary["deployed"] = summary.get("deployed", 0) + 1
                elif et == EVENT_SACRIFICE:
                    summary["sacrificed"] = summary.get("sacrificed", 0) + 1
                elif et == EVENT_DEATH:
                    summary["deaths"] = summary.get("deaths", 0) + 1
                elif et == EVENT_DRAW:
                    summary["drawn"] = summary.get("drawn", 0) + 1
                elif et == EVENT_DISCARDED:
                    summary["discarded"] = summary.get("discarded", 0) + 1
                elif et == EVENT_MILLED:
                    summary["milled"] = summary.get("milled", 0) + 1
        return summary
