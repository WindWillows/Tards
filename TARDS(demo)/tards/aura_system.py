#!/usr/bin/env python3
"""光环系统（Aura System）。

统一管理动态攻击力、最大生命值和关键词光环，支持来源追踪、自动过期和向后兼容。
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cards import Minion


@dataclass
class AuraEntry:
    """光环条目。

    Fields:
        source: 来源对象（Minion/Card/Game），用于追踪和批量清理
        fn: 光环计算函数
        expires_on: 过期时机。None=不过期。常用值：
            - "turn_end": 回合结束时自动清理
            - "phase_end": 阶段结束时自动清理
    """
    source: Any
    fn: Callable
    expires_on: Optional[str] = None


class AuraProvider:
    """光环提供者。

    管理某一类光环（攻击力/最大生命值/关键词）的注册、清理和求值。
    提供新旧两套 API：
      - 新 API: add(fn, source, expires_on), remove_by_source(source), expire(trigger)
      - 旧兼容 API: append(fn), remove(fn)
    """

    def __init__(self, minion: "Minion"):
        self._minion = minion
        self._entries: List[AuraEntry] = []

    # ------------------------------------------------------------------
    # 新 API
    # ------------------------------------------------------------------

    def add(self, fn: Callable, source: Any = None, expires_on: Optional[str] = None) -> None:
        """添加一个光环条目。"""
        self._entries.append(AuraEntry(source=source, fn=fn, expires_on=expires_on))
        self._minion.recalculate()

    def remove_by_source(self, source: Any) -> int:
        """移除指定来源的所有光环，返回移除数量。"""
        original = len(self._entries)
        self._entries = [e for e in self._entries if e.source is not source]
        if len(self._entries) != original:
            self._minion.recalculate()
        return original - len(self._entries)

    def remove_by_fn(self, fn: Callable) -> bool:
        """按函数引用移除单个光环，返回是否成功移除。"""
        for i, e in enumerate(list(self._entries)):
            if e.fn is fn:
                self._entries.pop(i)
                self._minion.recalculate()
                return True
        return False

    def expire(self, trigger: str) -> int:
        """按过期时机清理光环，返回移除数量。"""
        original = len(self._entries)
        self._entries = [e for e in self._entries if e.expires_on != trigger]
        if len(self._entries) != original:
            self._minion.recalculate()
        return original - len(self._entries)

    def evaluate(self) -> Any:
        """执行所有光环函数并返回聚合结果。

        子类应覆盖此方法以实现不同聚合逻辑（sum、dict merge 等）。
        """
        raise NotImplementedError

    def clear(self) -> None:
        """清空所有光环。"""
        if self._entries:
            self._entries.clear()
            self._minion.recalculate()

    def __len__(self) -> int:
        return len(self._entries)

    # ------------------------------------------------------------------
    # 旧兼容 API
    # ------------------------------------------------------------------

    def append(self, fn: Callable) -> None:
        """向后兼容：添加无来源/无过期的光环。"""
        self.add(fn)

    def remove(self, fn: Callable) -> None:
        """向后兼容：按函数引用移除光环。"""
        self.remove_by_fn(fn)

    def __iter__(self):
        """向后兼容：遍历所有光环函数。"""
        return iter(e.fn for e in self._entries)


class AttackAuraProvider(AuraProvider):
    """攻击力光环：求和。"""

    def evaluate(self) -> int:
        return sum(e.fn(self._minion) for e in self._entries)


class MaxHealthAuraProvider(AuraProvider):
    """最大生命值光环：求和。"""

    def evaluate(self) -> int:
        return sum(e.fn(self._minion) for e in self._entries)


class KeywordAuraProvider(AuraProvider):
    """关键词光环：字典合并。"""

    def evaluate(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for e in self._entries:
            for k, v in e.fn(self._minion).items():
                result[k] = self._merge_kw(result.get(k), v)
        return result

    @staticmethod
    def _merge_kw(old, new):
        if isinstance(old, int) and isinstance(new, int):
            return old + new
        return new
