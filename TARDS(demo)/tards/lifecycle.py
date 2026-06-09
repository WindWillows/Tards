"""监听器生命周期管理器（Listener Lifetime Manager）。

将分散在 minion_death()、remove_minion()、move_to() 等处的监听器清理逻辑
统一到一个中心，避免遗漏和重复。

设计原则：
- 不修改任何现有的注册代码（register_listener、history.listen、Card.on 等）
- 只统一清理路径：一处调用即可清理某个实体关联的所有监听器
- 未来新增监听器系统时，只需在此添加对应的清理逻辑
"""

from typing import Any, Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .cards import Card, Minion
    from .game import Game
    from .player import Player


class ListenerLifetimeManager:
    """统一监听器生命周期管理器。

    所有与实体（Minion/Card/Player）关联的监听器清理都通过此类完成。
    """

    def __init__(self, game: "Game"):
        self._game = game

    # ------------------------------------------------------------------
    # 公共 API
    # ------------------------------------------------------------------

    def clear_minion(self, minion: "Minion", *, reason: str = "") -> None:
        """统一清理与某个异象关联的所有监听器和动态回调。

        应在 minion_death() 的 do_remove、remove_minion()、
        以及任何将异象从战场永久移除的操作中调用。
        """
        prefix = f"  [{minion.name}]" if reason else f"  [{minion.name} ({reason})]"

        # 1. 部署钩子
        if hasattr(minion, "clear_deploy_hook"):
            minion.clear_deploy_hook(self._game)

        # 2. 提供的所有光环
        if hasattr(minion, "clear_all_provided_auras"):
            minion.clear_all_provided_auras()

        # 3. EventBus 监听器（旧兼容层 _event_owner_id）
        if hasattr(minion, "_event_owner_id"):
            self._game.unregister_listeners_by_owner(minion._event_owner_id)

        # 4. GameHistory 统一监听器
        if hasattr(self._game, "history"):
            self._game.history.unlisten_by_owner(minion)

        # 5. Card.on() 卡实例级监听器
        if hasattr(minion, "off_all"):
            minion.off_all()

        # 6. 延迟效果（_delayed_effects）
        self._clear_delayed_effects_by_owner(minion)

        # 7. 动态时间节点回调（Minion 级）
        self._clear_temporal_callbacks(minion)

        # 8. 战斗相关回调
        self._clear_combat_callbacks(minion)

        # 9. 费用修正（source 绑定到该异象的修正）
        player = getattr(minion, "owner", None)
        if player and hasattr(player, "_cost_modifier_system"):
            removed = player._cost_modifier_system.remove_by_source(minion)
            if removed:
                print(f"{prefix} 清理 {removed} 个费用修正")

    def clear_card(self, card: "Card", *, reason: str = "") -> None:
        """统一清理与某个卡牌关联的所有监听器。

        应在卡牌被弃置、消耗、回手或销毁时调用。
        """
        # 1. Card.on() 监听器
        if hasattr(card, "off_all"):
            card.off_all()

        # 2. EventBus 监听器（旧兼容层）
        if hasattr(card, "_event_owner_id"):
            self._game.unregister_listeners_by_owner(card._event_owner_id)

        # 3. GameHistory 监听器
        if hasattr(self._game, "history"):
            self._game.history.unlisten_by_owner(card)

        # 4. 延迟效果
        self._clear_delayed_effects_by_owner(card)

    def clear_player(self, player: "Player") -> None:
        """统一清理与某个玩家关联的所有动态回调和监听器。"""
        # 1. GameHistory 监听器
        if hasattr(self._game, "history"):
            self._game.history.unlisten_by_owner(player)

        # 2. 动态时间节点回调
        self._clear_temporal_callbacks(player)

        # 3. 部署增益
        if hasattr(player, "_deploy_buffs"):
            player._deploy_buffs.clear()

        # 4. 开发回调
        if hasattr(player, "_on_develop_callbacks"):
            player._on_develop_callbacks.clear()

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _clear_delayed_effects_by_owner(self, owner: Any) -> int:
        """从 _delayed_effects 中移除指定 owner 的所有条目，返回移除数量。"""
        if not hasattr(self._game, "_delayed_effects"):
            return 0
        original = len(self._game._delayed_effects)
        self._game._delayed_effects = [
            e for e in self._game._delayed_effects
            if e.get("owner") is not owner
        ]
        return original - len(self._game._delayed_effects)

    def _clear_temporal_callbacks(self, obj: Any) -> None:
        """清理动态注入的时间节点回调属性。"""
        for attr in ("on_turn_start", "on_turn_end", "on_phase_start", "on_phase_end",
                     "_injected_turn_start", "_injected_turn_end"):
            if hasattr(obj, attr):
                setattr(obj, attr, None)

    def _clear_combat_callbacks(self, minion: "Minion") -> None:
        """清理战斗相关回调列表。"""
        if hasattr(minion, "_pre_attack_fns"):
            minion._pre_attack_fns.clear()
        if hasattr(minion, "_on_take_combat_damage"):
            minion._on_take_combat_damage.clear()
