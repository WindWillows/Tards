from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from ..constants import (
    EVENT_BEFORE_DAMAGE, EVENT_DAMAGED, EVENT_AFTER_DAMAGE,
    EVENT_BEFORE_ATTACK, EVENT_ATTACKED, EVENT_AFTER_ATTACK,
    EVENT_BEFORE_DESTROY, EVENT_DESTROYED, EVENT_AFTER_DESTROY,
    EVENT_DEATH, GENERAL_KEYWORDS,
)
from ..core.aura_system import AttackAuraProvider, MaxHealthAuraProvider, KeywordAuraProvider

if TYPE_CHECKING:
    from ..core.player import Player
    from ..core.board import Board
    from ..game import Game
    from .minion_card import MinionCard


class Minion:
    """战场上的战斗异象。"""

    def __init__(
        self,
        name: str,
        owner: "Player",
        position: Any,
        attack: int,
        health: int,
        source_card: "MinionCard",
        board: "Board",
        keywords: Optional[Dict[str, Any]] = None,
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
        statue_top: bool = False,
        statue_bottom: bool = False,
        statue_pair: Optional[str] = None,
        on_statue_activate: Optional[Callable] = None,
        on_statue_fuse: Optional[Callable] = None,
        tags: Optional[List[str]] = None,
        hidden_keywords: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.owner = owner
        self.position = position
        self.source_card = source_card
        self.board = board
        self.can_attack = True
        self.summon_turn = -1
        self.on_turn_start = on_turn_start
        self.on_turn_end = on_turn_end
        self.on_phase_start = on_phase_start
        self.on_phase_end = on_phase_end
        # 动态注入的回合效果（金西瓜片、重生锚等效果赋予）
        self._injected_turn_start: List[Callable] = []
        self._injected_turn_end: List[Callable] = []
        self.statue_top = statue_top
        self.statue_bottom = statue_bottom
        self.statue_pair = statue_pair
        self.on_statue_activate = on_statue_activate
        self.on_statue_fuse = on_statue_fuse
        self.tags = tags or []
        self.hidden_keywords = hidden_keywords or {}
        self.asset_id: Optional[str] = None

        # 基础面板（卡牌定义时的原始值）
        self.base_attack = attack
        self.base_health = health
        self.base_max_health = health
        self.base_keywords = dict(keywords) if keywords else {}

        # 永久修饰（获得）
        self.perm_attack_bonus = 0
        self.perm_health_bonus = 0
        self.perm_max_health_bonus = 0
        self.perm_keywords: Dict[str, Any] = {}

        # 临时修饰（直到结算阶段结束等）
        self.temp_attack_bonus = 0
        self.temp_health_bonus = 0
        self.temp_max_health_bonus = 0
        self.temp_keywords: Dict[str, Any] = {}

        # 临时光环回调（具有）— 统一使用 AuraProvider
        self._aura_attack_provider = AttackAuraProvider(self)
        self._aura_max_health_provider = MaxHealthAuraProvider(self)
        self._aura_keyword_provider = KeywordAuraProvider(self)
        # 向后兼容别名
        self._aura_attack_fns = self._aura_attack_provider
        self._aura_max_health_fns = self._aura_max_health_provider
        self._aura_keyword_fns = self._aura_keyword_provider

        # 本 minion 向其它异象提供的光环记录（死亡/离场时自动清理）
        self._provided_auras: List[Tuple["Minion", str, Callable]] = []

        self._fear_active = self.base_keywords.get("恐惧", False)

        # "也算作是本异象"（命名牌等效果赋予）
        self.alias_name: Optional[str] = None

        # 伤害来源追踪（豪猪/环形虫/鹳/鬣狗/水螅岩等需要）
        self._last_damage_source: Optional["Minion"] = None
        self._last_damage_type: str = ""
        self._last_damage_amount: int = 0

        # 献祭次数限制（"献祭X"：可被献祭X次，默认1次）
        sacrifice_kw = self.base_keywords.get("献祭", False)
        if sacrifice_kw is True:
            self._sacrifice_remaining = 1
        elif isinstance(sacrifice_kw, int):
            self._sacrifice_remaining = sacrifice_kw
        else:
            self._sacrifice_remaining = 1

        # 战斗伤害回调
        self._on_take_combat_damage: List[Callable[[], None]] = []

        # 当前生效值
        self.current_attack = attack
        self.current_health = health
        self.current_max_health = health
        self.keywords: Dict[str, Any] = dict(self.base_keywords)

        self.recalculate()

    @property
    def display_keywords(self) -> Dict[str, Any]:
        """返回用于 UI 展示的关键词字典。

        规则：迅捷异象的休眠层数=1时，隐藏"休眠"只显示"迅捷"。
        """
        kw = dict(self.keywords)
        if "迅捷" in kw and kw.get("休眠") == 1:
            kw.pop("休眠", None)
        return kw

    @property
    def attack(self) -> int:
        return self.current_attack

    @property
    def health(self) -> int:
        return self.current_health

    @property
    def max_health(self) -> int:
        return self.current_max_health

    def evolve(self, game: "Game") -> bool:
        """成长：替换为下一个形态的新异象。"""
        next_name = getattr(self.source_card, 'evolve_to', None)
        if not next_name:
            print(f"  {self.name} 没有可成长的下一个形态")
            return False
        from ..data.card_db import DEFAULT_REGISTRY, CardType
        card_def = DEFAULT_REGISTRY.get(next_name)
        if not card_def or card_def.card_type != CardType.MINION:
            print(f"  {self.name} 的下一个形态 {next_name} 未找到或不是异象")
            return False
        new_minion = game.transform_minion(self, card_def, preserve_summon_turn=True)
        if new_minion:
            print(f"  {self.name} 成长为 {new_minion.name}！")
            # 应用成长时buff（通用机制）
            buff = getattr(self, "_on_evolve_buff", None)
            if buff:
                atk_delta, hp_delta = buff
                new_minion.gain_attack(atk_delta, permanent=True)
                new_minion.gain_health_bonus(hp_delta, permanent=True)
                print(f"  {new_minion.name} 成长时获得+{atk_delta}/+{hp_delta}")
            return True
        return False

    def recalculate(self):
        """重新计算当前生效的面板和关键词。"""
        # 攻击力
        aura_atk = self._aura_attack_provider.evaluate()
        self.current_attack = self.base_attack + self.perm_attack_bonus + self.temp_attack_bonus + aura_atk

        # 最大生命值
        aura_max = self._aura_max_health_provider.evaluate()
        new_max = self.base_max_health + self.perm_max_health_bonus + self.temp_max_health_bonus + aura_max
        self.current_max_health = new_max
        if self.current_health > self.current_max_health:
            self.current_health = self.current_max_health

        # 关键词
        kw = dict(self.base_keywords)
        for k, v in self.perm_keywords.items():
            kw[k] = self._merge_kw(kw.get(k), v)
        for k, v in self.temp_keywords.items():
            kw[k] = self._merge_kw(kw.get(k), v)
        aura_kw = self._aura_keyword_provider.evaluate()
        for k, v in aura_kw.items():
            kw[k] = self._merge_kw(kw.get(k), v)

        # 恐惧覆盖
        if self._fear_active:
            for k in list(kw.keys()):
                if k in GENERAL_KEYWORDS and k not in ("协同", "亡语"):
                    del kw[k]
            kw["恐惧"] = True
            kw["协同"] = True

        self.keywords = kw

    def apply_fear(self):
        """使该异象获得恐惧。"""
        if not self._fear_active:
            self._fear_active = True
            self.base_keywords["恐惧"] = True
            self.recalculate()
            print(f"  {self.name} 获得恐惧！")

    def remove_fear(self):
        """移除该异象的恐惧。"""
        if self._fear_active:
            self._fear_active = False
            self.base_keywords.pop("恐惧", None)
            self.recalculate()
            print(f"  {self.name} 不再恐惧。")

    @staticmethod
    def _merge_kw(old, new):
        if isinstance(old, int) and isinstance(new, int):
            return old + new
        return new

    def gain_attack(self, delta: int, permanent: bool = True):
        if permanent:
            self.perm_attack_bonus += delta
        else:
            self.temp_attack_bonus += delta
        self.recalculate()

    def gain_health_bonus(self, delta: int, permanent: bool = True):
        """增加最大生命值（当前生命值不自动增加，但降低时会截断）。"""
        if permanent:
            self.perm_max_health_bonus += delta
        else:
            self.temp_max_health_bonus += delta
        self.recalculate()

    def gain_keyword(self, key: str, value=True, permanent: bool = True):
        target = self.perm_keywords if permanent else self.temp_keywords
        target[key] = self._merge_kw(target.get(key), value)
        self.recalculate()

    def lose_keyword(self, key: str):
        self.perm_keywords.pop(key, None)
        self.temp_keywords.pop(key, None)
        self.recalculate()

    def reset_stats(self):
        """重置：清除所有永久、临时和光环修饰，恢复基础面板和关键词。"""
        self.perm_attack_bonus = 0
        self.perm_health_bonus = 0
        self.perm_max_health_bonus = 0
        self.perm_keywords.clear()
        self.temp_attack_bonus = 0
        self.temp_health_bonus = 0
        self.temp_max_health_bonus = 0
        self.temp_keywords.clear()
        self._aura_attack_provider.clear()
        self._aura_max_health_provider.clear()
        self._aura_keyword_provider.clear()
        self._fear_active = False
        self.current_health = self.base_health
        self.current_max_health = self.base_max_health
        self.recalculate()

    def clear_temp_effects(self):
        """结算阶段结束时调用：清除所有临时修饰。"""
        if self.temp_attack_bonus or self.temp_health_bonus or self.temp_max_health_bonus or self.temp_keywords:
            self.temp_attack_bonus = 0
            self.temp_health_bonus = 0
            self.temp_max_health_bonus = 0
            self.temp_keywords.clear()
            self.recalculate()

    # ----- 光环回调注册 -----
    def add_aura_attack(self, fn: Callable[["Minion"], int]):
        self._aura_attack_provider.add(fn)

    def remove_aura_attack(self, fn: Callable[["Minion"], int]):
        self._aura_attack_provider.remove_by_fn(fn)

    def add_aura_max_health(self, fn: Callable[["Minion"], int]):
        self._aura_max_health_provider.add(fn)

    def remove_aura_max_health(self, fn: Callable[["Minion"], int]):
        self._aura_max_health_provider.remove_by_fn(fn)

    def add_aura_keywords(self, fn: Callable[["Minion"], Dict[str, Any]]):
        self._aura_keyword_provider.add(fn)

    def remove_aura_keywords(self, fn: Callable[["Minion"], Dict[str, Any]]):
        self._aura_keyword_provider.remove_by_fn(fn)

    # ----- 光环提供者 API（自动追踪，便于死亡/离场时清理） -----

    def provide_aura_attack(self, target: "Minion", fn: Callable[["Minion"], int], expires_on: Optional[str] = None) -> None:
        """向目标提供攻击力光环，并记录以便自动清理。"""
        target._aura_attack_provider.add(fn, source=self, expires_on=expires_on)
        self._provided_auras.append((target, "attack", fn))

    def provide_aura_max_health(self, target: "Minion", fn: Callable[["Minion"], int], expires_on: Optional[str] = None) -> None:
        """向目标提供最大生命值光环，并记录以便自动清理。"""
        target._aura_max_health_provider.add(fn, source=self, expires_on=expires_on)
        self._provided_auras.append((target, "max_health", fn))

    def provide_aura_keywords(self, target: "Minion", fn: Callable[["Minion"], Dict[str, Any]], expires_on: Optional[str] = None) -> None:
        """向目标提供关键词光环，并记录以便自动清理。"""
        target._aura_keyword_provider.add(fn, source=self, expires_on=expires_on)
        self._provided_auras.append((target, "keyword", fn))

    def clear_all_provided_auras(self) -> None:
        """清除本 minion 向所有存活目标提供的光环。"""
        for target, aura_type, fn in list(self._provided_auras):
            if target.is_alive():
                if aura_type == "attack":
                    target.remove_aura_attack(fn)
                elif aura_type == "max_health":
                    target.remove_aura_max_health(fn)
                elif aura_type == "keyword":
                    target.remove_aura_keywords(fn)
        self._provided_auras.clear()

    def is_alive(self) -> bool:
        return self.position in self.board.minion_place and self.board.minion_place[self.position] is self

    def register_deploy_hook(self, game: "Game", fn: Callable[["Minion"], None]):
        """注册一个部署光环钩子：当任何异象部署成功时触发。"""
        game.deploy_hooks.append(fn)
        self._deploy_hook_fn = fn

    def clear_deploy_hook(self, game: "Game"):
        """清理本异象的部署光环钩子。"""
        fn = getattr(self, "_deploy_hook_fn", None)
        if fn and fn in game.deploy_hooks:
            game.deploy_hooks.remove(fn)
            self._deploy_hook_fn = None

    def minion_death(self, sync: bool = False):
        """触发死亡流程。

        Args:
            sync: 为 True 时立即同步执行移除（用于献祭等需要在效果内
                  立即清理战场的场景），否则加入连锁队列延后处理。
        """
        if self.current_health <= 0 and self.is_alive() and not getattr(self, "_pending_death", False):
            print(f"  {self.name} 被消灭了！")
            self._pending_death = True

            # 清理部署钩子
            if self.board.game_ref:
                self.clear_deploy_hook(self.board.game_ref)

            # 宿主被消灭时，藤蔓同时被消灭
            if hasattr(self, 'vine_overlay') and self.vine_overlay:
                vine = self.vine_overlay
                if vine.is_alive():
                    vine.current_health = 0
                    vine.minion_death()

            def do_remove():
                game = self.board.game_ref

                # === BEFORE_DESTROY 事件 ===
                if game:
                    event = game.emit_event(
                        EVENT_BEFORE_DESTROY,
                        source=None,
                        target=self,
                        minion=self,
                        player=self.owner,
                    )
                    if getattr(event, "cancelled", False):
                        # 阻止消灭：恢复1点HP（最小值）
                        self.current_health = max(1, self.current_health)
                        self._pending_death = False
                        print(f"  {self.name} 的消灭被阻止")
                        return

                # 从棋盘移除（remove_minion 内部会自动调用 lifecycle.clear_minion 如果存在）
                self.board.remove_minion(self.position)

                # 降级：旧兼容路径（无 lifecycle 时手动清理）
                if not (game and hasattr(game, 'lifecycle')):
                    self.clear_all_provided_auras()
                    if game and hasattr(self, '_event_owner_id'):
                        game.unregister_listeners_by_owner(self._event_owner_id)
                    if game and hasattr(self, 'history'):
                        game.history.unlisten_by_owner(self)

                if game:
                    game.emit_event(EVENT_DEATH, minion=self, player=self.owner)
                    if hasattr(game, "_state_log"):
                        game._state_log.append({
                            "event": "minion_death",
                            "minion": self,
                            "player": self.owner,
                            "turn": getattr(game, "current_turn", 0),
                        })

                    # === DESTROYED 事件 ===
                    game.emit_event(
                        EVENT_DESTROYED,
                        source=None,
                        target=self,
                        minion=self,
                        player=self.owner,
                    )

                    # === AFTER_DESTROY 事件 ===
                    game.emit_event(
                        EVENT_AFTER_DESTROY,
                        source=None,
                        target=self,
                        minion=self,
                        player=self.owner,
                    )

                    deathrattle = self.keywords.get("亡语")
                    if deathrattle and callable(deathrattle):
                        def make_dr(m=self, dr=deathrattle):
                            def fn():
                                print(f"  {m.name} 的亡语触发")
                                dr(m, m.owner, m.board)
                            return fn
                        game.effect_queue.queue(f"亡语 [{self.name}]", make_dr())

            if sync:
                do_remove()
            elif self.board.game_ref:
                self.board.game_ref.effect_queue.queue(f"消灭 [{self.name}]", do_remove)
            else:
                do_remove()

    def take_damage(self, damage: int, source_minion: Optional["Minion"] = None,
                     source_type: str = "", is_combat_damage: bool = False):
        """对异象造成伤害。经过 before_damage → 实际扣血 → damaged → after_damage 完整事件链。

        Args:
            damage: 伤害数值
            source_minion: 伤害来源异象（如有）
            source_type: 伤害来源类型（"combat"/"strategy"/"effect"）
            is_combat_damage: 是否为战斗伤害（攻击流程中造成）
        """
        if damage <= 0:
            return

        game = getattr(self.board, "game_ref", None)

        # === 1. 伤害替换（保留现有机制）===
        if game:
            damage = game.apply_damage_replacements(self, damage, source_minion)
        if damage <= 0:
            return

        # === 2. BEFORE_DAMAGE 事件（可取消/修改）===
        if game:
            event = game.emit_event(
                EVENT_BEFORE_DAMAGE,
                source=source_minion,
                target=self,
                damage=damage,
                source_minion=source_minion,
                source_type=source_type,
                is_combat_damage=is_combat_damage,
            )
            if getattr(event, "cancelled", False):
                print(f"  {self.name} 的伤害被阻止")
                return
            damage = event.get("damage", damage)
            if damage <= 0:
                return

        # === 3. 藤蔓替伤（保留现有机制）===
        vine = getattr(self, "vine_overlay", None)
        if vine and vine.is_alive():
            print(f"  {self.name} 的藤蔓替其承受 {damage} 点伤害")
            vine.take_damage(damage, source_minion, source_type=source_type, is_combat_damage=is_combat_damage)
            if not vine.is_alive():
                print(f"  {vine.name} 被摧毁")
                self.vine_overlay = None
            return

        # === 4. 计算实际伤害（坚韧/破甲/脆弱/冰冻）===
        tough = self.keywords.get("坚韧", 0)
        fragile = self.keywords.get("脆弱", False)
        if fragile and isinstance(tough, int) and tough == 0:
            tough = -1
        if source_minion:
            # 通用标记：来源异象无视坚韧（如恶魂）
            if getattr(source_minion, "_ignore_toughness", False):
                tough = 0
            else:
                armor_break = source_minion.keywords.get("破甲", 0)
                if isinstance(armor_break, int) and armor_break > 0 and isinstance(tough, int):
                    tough = max(0, tough - armor_break)
        actual = max(0, damage - tough) if isinstance(tough, int) else damage

        # 冰冻：受到攻击伤害时削减一层，若因此归零则本次伤害翻倍
        if is_combat_damage and source_minion is not None:
            frozen = self.keywords.get("冰冻", 0)
            if isinstance(frozen, int) and frozen > 0:
                frozen -= 1
                if frozen <= 0:
                    actual *= 2
                    print(f"  {self.name} 的冰冻解除，本次伤害翻倍！")
                    self.keywords.pop("冰冻", None)
                else:
                    self.keywords["冰冻"] = frozen

        # === 5. 实际扣血 ===
        self.current_health -= actual
        print(f"  {self.name} 受到 {actual} 点伤害，剩余 {self.current_health}/{self.current_max_health}")

        # 记录伤害来源（用于亡语/效果中追溯伤害来源）
        if actual > 0:
            self._last_damage_source = source_minion
            self._last_damage_type = source_type
            self._last_damage_amount = actual

        # 旧的 combat damage 回调（保留兼容）
        if source_minion is not None:
            for fn in list(self._on_take_combat_damage):
                fn()

        # === 6. DAMAGED 事件（已发生，只读）===
        if game:
            game.emit_event(
                EVENT_DAMAGED,
                source=source_minion,
                target=self,
                actual=actual,
                original=damage,
                source_minion=source_minion,
                source_type=source_type,
                is_combat_damage=is_combat_damage,
            )

        # === 7. AFTER_DAMAGE 事件（只读）===
        if game:
            game.emit_event(
                EVENT_AFTER_DAMAGE,
                source=source_minion,
                target=self,
                actual=actual,
                original=damage,
                source_minion=source_minion,
                source_type=source_type,
                is_combat_damage=is_combat_damage,
            )

        # === 8. 检查死亡 ===
        if self.current_health <= 0:
            self.minion_death()

    def minion_heal(self, heal: int):
        self.current_health += heal
        if self.current_max_health < self.current_health:
            self.current_health = self.current_max_health

    def can_attack_this_turn(self, turn_number: int) -> bool:
        if self.current_attack <= 0:
            return False
        # 眩晕阻止攻击
        if self.keywords.get("眩晕", 0) > 0:
            return False
        # 休眠检查
        dormant = self.keywords.get("休眠", 0)
        if dormant > 0:
            # 迅捷异象在休眠层数为1时仍可攻击
            if "迅捷" in self.keywords and dormant == 1:
                return True
            return False
        return self.summon_turn < turn_number

    def attack_target(self, target: Any):
        from ..core.player import Player
        game = getattr(self.board, "game_ref", None)

        # 触发攻击前回调（雕的首次攻击效果等）
        for fn in getattr(self, "_pre_attack_fns", []):
            fn(self, target)

        # === BEFORE_ATTACK 事件（可取消/修改目标）===
        if game:
            event = game.emit_event(
                EVENT_BEFORE_ATTACK,
                source=self,
                target=target,
                attacker=self,
                defender=target,
            )
            if event is None:
                return
            if getattr(event, "cancelled", False):
                return
            target = event.get("target", target)
            target = event.get("defender", target)

        # 执行攻击
        if isinstance(target, Minion):
            # 串击：对同列所有敌方异象造成伤害
            if self.keywords.get("串击", False):
                col = self.position[1]
                enemies = [m for m in self.board.get_enemy_minions_in_column(col, self.owner) if m.is_alive()]
                if enemies:
                    print(f"  {self.name} 串击同列所有敌方异象")
                    for enemy in enemies:
                        was_alive = enemy.is_alive()
                        enemy.take_damage(self.current_attack, source_minion=self, source_type="combat", is_combat_damage=True)
                        if was_alive and not enemy.is_alive() and self.keywords.get("兴奋", False):
                            self._excitement_triggered = True
                        if enemy.is_alive():
                            spike = enemy.keywords.get("尖刺", 0)
                            if spike > 0:
                                print(f"  {enemy.name} 的尖刺反弹 {spike} 点伤害")
                                self.take_damage(spike, source_type="combat", is_combat_damage=True)
                else:
                    player_target = self.board.game_ref.p2 if self.owner == self.board.game_ref.p1 else self.board.game_ref.p1
                    print(f"  {self.name} 直接攻击 {player_target.name}，造成 {self.current_attack} 点伤害")
                    player_target.health_change(-self.current_attack, source=self)
            else:
                print(f"  {self.name} 攻击 {target.name}，造成 {self.current_attack} 点伤害")
                was_alive = target.is_alive()
                target.take_damage(self.current_attack, source_minion=self, source_type="combat", is_combat_damage=True)
                target._last_attacker = self
                if was_alive and not target.is_alive() and self.keywords.get("兴奋", False):
                    self._excitement_triggered = True
                if target.is_alive():
                    spike = target.keywords.get("尖刺", 0)
                    if spike > 0:
                        print(f"  {target.name} 的尖刺反弹 {spike} 点伤害")
                        self.take_damage(spike, source_type="combat", is_combat_damage=True)
                # 穿刺：攻击目标异象的同时，也会攻击对手英雄
                if self.keywords.get("穿刺", False):
                    player_target = self.board.game_ref.p2 if self.owner == self.board.game_ref.p1 else self.board.game_ref.p1
                    print(f"  {self.name} 穿刺攻击 {player_target.name}，造成 {self.current_attack} 点伤害")
                    player_target.health_change(-self.current_attack, source=self)
        elif isinstance(target, Player):
            print(f"  {self.name} 直接攻击 {target.name}，造成 {self.current_attack} 点伤害")
            target.health_change(-self.current_attack, source=self)

        # === ATTACKED / AFTER_ATTACK ===
        if game:
            game.emit_event(
                EVENT_ATTACKED,
                source=self,
                target=target,
                attacker=self,
                defender=target,
            )
            game.emit_event(
                EVENT_AFTER_ATTACK,
                source=self,
                target=target,
                attacker=self,
                defender=target,
            )

    def __str__(self) -> str:
        return f"{self.name}({self.current_attack}/{self.current_health})"
