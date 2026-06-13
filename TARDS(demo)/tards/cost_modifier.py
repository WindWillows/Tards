#!/usr/bin/env python3
"""费用修正系统（CostModifierSystem）。

统一管理人员级和卡牌级费用修正，支持来源追踪、自动过期和向后兼容。
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cards import Card
    from .cost import Cost


@dataclass
class CostModifier:
    """费用修正条目。

    Fields:
        apply_fn: 实际修正逻辑 (card, cost) -> None
        source: 来源对象（Minion/Card/Game），用于追踪和批量清理
        expires_on: 过期时机。None=不过期。常用值：
            - "turn_end": 结算阶段结束时自动清理
            - "phase_end": 阶段结束时自动清理
            - "card_leave_hand": 卡牌离开手牌时自动清理
            - "minion_death": 异象死亡时自动清理
    """
    apply_fn: Callable[["Card", "Cost"], None]
    source: Any = None
    expires_on: Optional[str] = None


class CostModifierSystem:
    """统一费用修正系统。

    同时管理玩家级和卡牌级修正（卡牌级修正通过 source=card 区分）。
    提供新旧两套 API：
      - 新 API: add(modifier), remove_by_source(source), expire(trigger)
      - 旧兼容 API: append(fn), remove(fn)
    """

    def __init__(self):
        self._modifiers: List[CostModifier] = []

    # ------------------------------------------------------------------
    # 新 API
    # ------------------------------------------------------------------

    def add(self, modifier: CostModifier) -> None:
        """添加一个费用修正条目。"""
        self._modifiers.append(modifier)

    def remove_by_source(self, source: Any) -> int:
        """移除指定来源的所有修正，返回移除数量。"""
        original = len(self._modifiers)
        self._modifiers = [m for m in self._modifiers if m.source is not source]
        return original - len(self._modifiers)

    def expire(self, trigger: str) -> int:
        """按过期时机清理修正，返回移除数量。"""
        original = len(self._modifiers)
        self._modifiers = [m for m in self._modifiers if m.expires_on != trigger]
        return original - len(self._modifiers)

    def apply(self, card: "Card", cost: "Cost") -> None:
        """对所有存活修正依次执行。"""
        for m in list(self._modifiers):
            try:
                m.apply_fn(card, cost)
            except Exception as e:
                print(f"  [费用修正错误] {e}")

    def clear(self) -> None:
        """清空所有修正。"""
        self._modifiers.clear()

    def __len__(self) -> int:
        return len(self._modifiers)

    # ------------------------------------------------------------------
    # 旧兼容 API（逐步迁移中）
    # ------------------------------------------------------------------

    def append(self, fn: Callable[["Card", "Cost"], None]) -> None:
        """向后兼容：将裸函数包装为 CostModifier 添加。

        新代码应使用 add(CostModifier(...)) 以支持来源追踪和自动过期。
        """
        self._modifiers.append(CostModifier(apply_fn=fn))

    def remove(self, fn: Callable[["Card", "Cost"], None]) -> None:
        """向后兼容：按函数引用移除修正。"""
        for i, m in enumerate(list(self._modifiers)):
            if m.apply_fn is fn:
                self._modifiers.pop(i)
                break

    # 让 for fn in system: 继续工作（旧代码可能直接遍历）
    def __iter__(self):
        """向后兼容：遍历所有 apply_fn。"""
        return iter(m.apply_fn for m in self._modifiers)
