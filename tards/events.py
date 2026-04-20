#!/usr/bin/env python3
"""通用事件总线与 GameEvent 对象。

设计原则：
  1. 任何状态修改都经过事件。
  2. 事件分 before_*（可阻止/修改）和主事件/after_*（已发生，只读）。
  3. 监听器按优先级排序，通过 EffectQueue 串行执行。
  4. 监听器内部触发的新事件，追加到同一队列。

监听器签名：
    def listener(event: GameEvent) -> None:
        if event.type.startswith("before_"):
            event.cancelled = True   # 阻止主行为
            event.data["damage"] = 1 # 修改数据
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class GameEvent:
    """统一事件对象。所有监听器共享同一实例。"""

    type: str
    source: Optional[Any] = None
    data: Dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False          # before_* 事件：是否被取消
    prevent_default: bool = False    # 是否阻止默认行为

    def __getitem__(self, key: str) -> Any:
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


class EventBus:
    """事件总线：负责监听器的注册、注销和事件发射。

    监听器通过 register(event_type, fn, priority) 注册。
    priority 越小越先执行（负数可用于最优先拦截）。
    """

    def __init__(self, game=None):
        self.game = game
        # event_type -> [(priority, fn, owner_id), ...]
        self._listeners: Dict[str, List[Tuple[int, Callable, Optional[int]]]] = {}
        # owner_id -> [event_type, ...]  用于批量注销
        self._owner_registry: Dict[int, List[str]] = {}
        self._next_owner_id = 1

    def register(self, event_type: str, fn: Callable[[GameEvent], None],
                 priority: int = 0, owner_id: Optional[int] = None) -> int:
        """注册一个监听器。返回 owner_id（可用于后续批量注销）。"""
        if owner_id is None:
            owner_id = self._next_owner_id
            self._next_owner_id += 1

        listeners = self._listeners.setdefault(event_type, [])
        listeners.append((priority, fn, owner_id))
        listeners.sort(key=lambda x: x[0])

        self._owner_registry.setdefault(owner_id, []).append(event_type)
        return owner_id

    def unregister(self, event_type: str, fn: Callable[[GameEvent], None]) -> None:
        """注销单个监听器。"""
        listeners = self._listeners.get(event_type, [])
        for i, (priority, listener_fn, owner_id) in enumerate(listeners):
            if listener_fn is fn:
                listeners.pop(i)
                # 清理 owner_registry 中的记录
                if owner_id is not None:
                    reg = self._owner_registry.get(owner_id, [])
                    if event_type in reg:
                        reg.remove(event_type)
                break

    def unregister_by_owner(self, owner_id: int) -> None:
        """注销某个 owner_id 下的所有监听器。用于单位死亡时自动清理。"""
        event_types = self._owner_registry.pop(owner_id, [])
        for event_type in event_types:
            listeners = self._listeners.get(event_type, [])
            self._listeners[event_type] = [
                (p, fn, oid) for (p, fn, oid) in listeners if oid != owner_id
            ]

    def emit(self, event_type: str, source: Optional[Any] = None,
             **kwargs) -> GameEvent:
        """发射一个事件，同步执行所有监听器（含通配符 * 监听器）。

        返回事件对象，调用方可检查 event.cancelled / event.prevent_default。
        监听器内部若调用 bus.emit() 触发新事件，新事件会同步执行。

        执行顺序：先 event_type 专用监听器（按 priority 排序），
                  再 "*" 通配符监听器（按 priority 排序）。
        """
        event = GameEvent(type=event_type, source=source, data=kwargs)

        # 收集专用监听器 + 通配符监听器，统一排序
        specific = self._listeners.get(event_type, [])
        wildcard = self._listeners.get("*", [])
        all_listeners = list(specific) + list(wildcard)
        all_listeners.sort(key=lambda x: x[0])

        for priority, fn, owner_id in all_listeners:
            # before_* 事件：一旦 cancelled，跳过后续监听器
            if event.cancelled and event_type.startswith("before_"):
                break
            try:
                fn(event)
            except Exception as e:
                print(f"  [事件错误] {event_type} 监听器 {fn.__name__}: {e}")
        return event

    def clear(self) -> None:
        """清空所有监听器。"""
        self._listeners.clear()
        self._owner_registry.clear()
