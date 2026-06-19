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

class EventMixin:

    def register_listener(self, event_type: str, fn: Callable[[GameEvent], None],
                          priority: int = 0, owner_id: Optional[int] = None) -> int:
        """注册一个事件监听器。返回 owner_id 可用于后续批量注销。"""
        return self.event_bus.register(event_type, fn, priority, owner_id)

    def unregister_listener(self, event_type: str, fn: Callable[[GameEvent], None]) -> None:
        """注销单个监听器。"""
        self.event_bus.unregister(event_type, fn)

    def unregister_listeners_by_owner(self, owner_id: int) -> None:
        """注销某个 owner_id 下的所有监听器。用于异象死亡时自动清理。"""
        self.event_bus.unregister_by_owner(owner_id)

    def emit_event(self, event_type: str, source: Optional[Any] = None, **kwargs) -> Optional[GameEvent]:
        if self.game_over:
            return None

        # === 新版事件总线（含通配符监听器，阴谋在此触发） ===
        event = self.event_bus.emit(event_type, source=source, **kwargs)

        # === 自动化时间节点效果（结算阶段开始/结束等） ===
        event_data = dict(event_type=event_type, **kwargs)
        if event_type in (EVENT_TURN_START, EVENT_TURN_END, EVENT_PHASE_START,
                          EVENT_PHASE_END, EVENT_DEPLOYED, EVENT_DEATH,
                          EVENT_CARD_PLAYED, EVENT_DRAW, EVENT_SACRIFICE,
                          EVENT_BELL, EVENT_PLAYER_DAMAGE):
            self._trigger_auto_effects(event_type, event_data)

            # 异象融合检测与结算
            if event_type == EVENT_DEPLOYED:
                self._check_fusion_edges(event_data)
            if event_type == EVENT_PHASE_END and event_data.get("phase") == self.PHASE_RESOLVE:
                self._resolve_fusions()
            if event_type == EVENT_TURN_END:
                self._resolve_fusions()

            # === 费用修正自动过期清理 ===
            if event_type == EVENT_TURN_END:
                for p in self.players:
                    if hasattr(p, "_cost_modifier_system"):
                        removed = p._cost_modifier_system.expire("turn_end")
                        if removed:
                            print(f"  [费用系统] {p.name} 清理 {removed} 个结算阶段结束过期的费用修正")
            elif event_type == EVENT_PHASE_END:
                for p in self.players:
                    if hasattr(p, "_cost_modifier_system"):
                        removed = p._cost_modifier_system.expire("phase_end")
                        if removed:
                            print(f"  [费用系统] {p.name} 清理 {removed} 个阶段结束过期的费用修正")

            # === 光环自动过期清理 ===
            if event_type == EVENT_TURN_END:
                for m in list(self.board.minion_place.values()):
                    if m.is_alive():
                        for prov in (m._aura_attack_provider, m._aura_max_health_provider, m._aura_keyword_provider):
                            removed = prov.expire("turn_end")
                            if removed:
                                print(f"  [光环系统] {m.name} 清理 {removed} 个结算阶段结束过期的光环")
            elif event_type == EVENT_PHASE_END:
                for m in list(self.board.minion_place.values()):
                    if m.is_alive():
                        for prov in (m._aura_attack_provider, m._aura_max_health_provider, m._aura_keyword_provider):
                            removed = prov.expire("phase_end")
                            if removed:
                                print(f"  [光环系统] {m.name} 清理 {removed} 个阶段结束过期的光环")

        # 更新机器日志
        if hasattr(self, "history"):
            self.history.on_event(event_type, **kwargs)

        if not self.effect_queue.is_resolving():
            self.refresh_all_auras()

        return event

    def register_conspiracy(self, conspiracy: "Conspiracy", player: "Player") -> int:
        """将阴谋注册到事件总线。返回 owner_id 用于后续注销。

        阴谋通过通配符监听器 '*' 监听所有事件，condition_fn 自行判断。
        优先级设为 50（在普通效果之后，但在大部分后置处理之前）。
        """
        owner_id = id(conspiracy)
        conspiracy._listener_owner_id = owner_id

        def listener(event: GameEvent):
            if conspiracy not in player.active_conspiracies:
                return  # 已被消耗或移除
            if not conspiracy.condition_fn:
                return
            # condition_fn 签名：(game, event_data_dict, player)
            # 为方便阴谋判断触发时机，自动注入 event_type
            event_data = dict(event.data)
            event_data["event_type"] = event.type
            event_data["_event_ref"] = event
            if conspiracy.condition_fn(self, event_data, player):
                # 满足条件：移出活跃区，注销监听器，推入 EffectQueue 执行
                player.active_conspiracies.remove(conspiracy)
                self.unregister_listeners_by_owner(owner_id)

                def make_trigger(c=conspiracy, p=player, ev=event):
                    def trigger():
                        print(f"  阴谋 [{c.name}] 被触发！")
                        c.effect_fn(self, ev.data, p)
                        if c in p.card_hand:
                            p.card_hand.remove(c)
                        p.card_dis.append(c)
                        self.emit_event(EVENT_CONSPIRACY_TRIGGERED, conspiracy=c, player=p)
                    return trigger
                # 动态选择 push_stack / queue：
                # - 若当前在堆栈解析中（出牌/部署/战斗等），使用 push_stack
                #   确保 effect_fn 在当前堆栈帧之前执行（堆栈反制型阴谋需要）。
                # - 若不在堆栈解析中（回合/阶段事件），使用 queue 立即执行。
                if self.effect_queue.is_resolving_stack():
                    self.effect_queue.push_stack(f"阴谋 [{conspiracy.name}]", make_trigger())
                else:
                    self.effect_queue.queue(f"阴谋 [{conspiracy.name}]", make_trigger())

        self.event_bus.register("*", listener, priority=50, owner_id=owner_id)
        return owner_id

    def unregister_conspiracy(self, conspiracy: "Conspiracy") -> None:
        """注销阴谋的事件监听器。"""
        owner_id = getattr(conspiracy, "_listener_owner_id", None)
        if owner_id:
            self.unregister_listeners_by_owner(owner_id)
            conspiracy._listener_owner_id = None

    def _trigger_auto_effects(self, event_type: str, event_data: Dict[str, Any]):
        """触发场上异象、手牌、玩家的自动化时间节点效果。

        规则："结算阶段开始/结束" 等价于 "结算阶段开始/结束"（PHASE_RESOLVE）。
        """
        attrs_to_trigger = []
        trigger_injected_start = False
        trigger_injected_end = False

        normal_attr = self._EVENT_ATTR_MAP.get(event_type)
        if normal_attr:
            attrs_to_trigger.append(normal_attr)

        # 结算阶段开始 = 结算阶段开始
        if event_type == EVENT_PHASE_START and event_data.get("phase") == self.PHASE_RESOLVE:
            attrs_to_trigger.append("on_turn_start")
            trigger_injected_start = True
        # 结算阶段结束 = 结算阶段结束
        elif event_type == EVENT_PHASE_END and event_data.get("phase") == self.PHASE_RESOLVE:
            attrs_to_trigger.append("on_turn_end")
            trigger_injected_end = True

        for attr_name in attrs_to_trigger:
            if not attr_name:
                continue

            specific_only = event_type in self._EVENT_SPECIFIC_TARGET
            specific_target = event_data.get("card") if specific_only else None

            # 场上存活异象
            for m in list(self.board.minion_place.values()):
                if not m.is_alive():
                    continue
                if specific_target is not None and m is not specific_target:
                    continue
                fn = getattr(m, attr_name, None)
                if fn:
                    self.effect_queue.queue(
                        f"{m.name} 的 {event_type}",
                        lambda m=m, fn=fn: fn(self, event_data, m),
                    )
                # 注入的动态效果（金西瓜片、重生锚等赋予的额外回合效果）
                if trigger_injected_start and attr_name == "on_turn_start":
                    for inj_fn in list(getattr(m, "_injected_turn_start", []) or []):
                        self.effect_queue.queue(
                            f"{m.name} 的注入结算阶段开始效果",
                            lambda m=m, inj_fn=inj_fn: inj_fn(m, m.owner, self),
                        )
                elif trigger_injected_end and attr_name == "on_turn_end":
                    for inj_fn in list(getattr(m, "_injected_turn_end", []) or []):
                        self.effect_queue.queue(
                            f"{m.name} 的注入结算阶段结束效果",
                            lambda m=m, inj_fn=inj_fn: inj_fn(m, m.owner, self),
                        )

            # 双方手牌
            for p in self.players:
                for card in list(p.card_hand):
                    if specific_target is not None and card is not specific_target:
                        continue
                    fn = getattr(card, attr_name, None)
                    if fn:
                        self.effect_queue.queue(
                            f"{card.name} 的 {event_type}",
                            lambda c=card, fn=fn: fn(self, event_data, c),
                        )

            # 玩家自身
            for p in self.players:
                if specific_target is not None and p is not specific_target:
                    continue
                fn = getattr(p, attr_name, None)
                if fn:
                    self.effect_queue.queue(
                        f"{p.name} 的 {event_type}",
                        lambda pl=p, fn=fn: fn(self, event_data, pl),
                    )

