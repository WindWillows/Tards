from typing import Any, Callable, Dict, List, Optional
from ..core.board import Board
from ..cards import MineralCard, Minion, MinionCard, Strategy, Conspiracy
from ..data.card_db import DEFAULT_REGISTRY, CardType, Pack
from ..constants import (
    EVENT_BELL,
    EVENT_BRAKE,
    EVENT_CARD_PLAYED,
    EVENT_CONSPIRACY_TRIGGERED,
    EVENT_DEATH,
    EVENT_DEPLOYED,
    EVENT_DRAW,
    EVENT_PHASE_END,
    EVENT_PHASE_START,
    EVENT_PLAYER_DAMAGE,
    EVENT_SACRIFICE,
    EVENT_TURN_END,
    EVENT_TURN_START,
)
from ..effect_queue import EffectQueue
from ..events import EventBus, GameEvent
from ..core.fusion import FusionSystem
from ..core.game_history import GameHistory
from ..core.game_logger import GameLogger
from ..core.player import Player
from ..core.targeting import TargetingRequest, TargetingSystem

class CombatMixin:

    def is_immune(self, target: Any, source_player: Player, effect_type: str = "strategy") -> bool:
        """检查目标是否免疫某类效果（用于绝缘等机制）。"""
        if effect_type == "strategy" and isinstance(target, Minion):
            if target.keywords.get("绝缘", False) and target.owner != source_player:
                print(f"  {target.name} 绝缘，免疫策略效果")
                return True
            # 虎的全局绝缘：对方无法使用策略指向友方异象
            if target.owner and target.owner != source_player:
                if getattr(target.owner, "_global_insulation_count", 0) > 0:
                    print(f"  {target.name} 受虎保护，免疫策略效果")
                    return True
        return False

    def register_damage_replacement(
        self,
        filter_fn: Callable[[Any, int, Any], bool],
        replace_fn: Callable[[int], int],
        once: bool = True,
        reason: str = "伤害替换",
    ):
        """注册一个伤害替换效果。

        filter_fn(target, damage, source) -> bool  判断是否匹配本次伤害。
        replace_fn(damage) -> int                  返回新伤害值（0 表示完全取消）。
        once=True 时触发一次后自动移除。
        """
        self._damage_replacements.append({
            "filter": filter_fn,
            "replace": replace_fn,
            "once": once,
            "reason": reason,
        })

    def add_damage_replacement(
        self,
        filter_fn: Callable[[Any, int, Any], bool],
        replace_fn: Callable[[int], int],
        once: bool = True,
        reason: str = "伤害替换",
    ) -> None:
        """注册一个伤害替换效果。

        filter_fn(target, damage, source) -> bool 判断某次伤害是否被替换。
        replace_fn(damage) -> int 返回替换后的伤害值（0 表示取消）。
        """
        self._damage_replacements.append({
            "filter": filter_fn,
            "replace": replace_fn,
            "once": once,
            "reason": reason,
        })

    def apply_damage_replacements(self, target: Any, damage: int, source: Any) -> int:
        """按注册顺序依次应用伤害替换，返回最终伤害值（0 表示被取消）。"""
        if damage <= 0:
            return 0
        if not self._damage_replacements:
            return damage
        remaining = damage
        to_remove = []
        for i, entry in enumerate(self._damage_replacements):
            if entry["filter"](target, remaining, source):
                new_damage = entry["replace"](remaining)
                if new_damage != remaining:
                    print(f"  [{entry['reason']}] {getattr(target, 'name', str(target))} 受到的 {remaining} 点伤害 -> {new_damage}")
                remaining = new_damage
                if entry.get("once", True):
                    to_remove.append(i)
                if remaining <= 0:
                    break
        for i in reversed(to_remove):
            self._damage_replacements.pop(i)
        return max(0, remaining)

    def protect_target(
        self,
        filter_fn: Callable[[Any, Any], bool],
        reason: str = "指向保护",
        once: bool = True,
    ):
        """注册一个指向保护效果。

        filter_fn(target, source) -> bool  判断某次指向是否被保护。
        被保护的目标在 Strategy.effect() 执行前会被拦截，卡牌正常消耗但效果不执行。
        """
        self._target_protections.append({
            "filter": filter_fn,
            "reason": reason,
            "once": once,
        })

    def is_target_protected(self, target: Any, source: Any) -> bool:
        """检查目标是否被保护（指向被无效化）。返回 True 表示效果应被取消。"""
        if not self._target_protections:
            return False
        to_remove = []
        for i, entry in enumerate(self._target_protections):
            if entry["filter"](target, source):
                print(f"  [{entry['reason']}] {getattr(target, 'name', str(target))} 的指向被保护，效果被取消")
                if entry.get("once", True):
                    to_remove.append(i)
                for j in reversed(to_remove):
                    self._target_protections.pop(j)
                return True
        return False

    def clear_protections(self):
        """清理所有持续保护效果（结算阶段结束/开始时调用）。"""
        self._target_protections.clear()
        # 移除所有 once=False 的伤害替换（持续型）
        self._damage_replacements = [
            r for r in self._damage_replacements if r.get("once", True)
        ]

    def _process_delayed_effects(self, trigger: str):
        """处理延迟效果队列中匹配当前触发时机的回调。

        新增：若条目绑定了 owner，且 owner 已死亡/不在场上，则跳过执行。
        """
        if not hasattr(self, "_delayed_effects"):
            return
        to_run = []
        remaining = []
        for entry in self._delayed_effects:
            # owner 存活检查
            owner = entry.get("owner")
            if owner is not None:
                is_alive = getattr(owner, "is_alive", None)
                if is_alive is not None and not is_alive():
                    continue  # owner 已死亡，跳过该条目

            if entry.get("trigger") == trigger:
                turn = entry.get("turn", 0)
                player = entry.get("player")
                if trigger == "turn_start" and self.current_turn == turn:
                    if player is None or player == self.current_player:
                        to_run.append(entry["fn"])
                    else:
                        remaining.append(entry)
                elif trigger == "turn_end" and self.current_turn == turn:
                    to_run.append(entry["fn"])
                else:
                    remaining.append(entry)
            else:
                remaining.append(entry)
        self._delayed_effects = remaining
        for fn in to_run:
            try:
                fn()
            except Exception as e:
                print(f"  [延迟效果错误] {e}")

