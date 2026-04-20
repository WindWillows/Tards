from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING
from .constants import (
    EVENT_DEPLOY, EVENT_DEATH, EVENT_SACRIFICE, GENERAL_KEYWORDS,
    EVENT_BEFORE_DAMAGE, EVENT_DAMAGED, EVENT_AFTER_DAMAGE,
    EVENT_BEFORE_ATTACK, EVENT_ATTACKED, EVENT_AFTER_ATTACK,
    EVENT_BEFORE_DESTROY, EVENT_DESTROYED, EVENT_AFTER_DESTROY,
    EVENT_BEFORE_DEPLOY, EVENT_DEPLOYED, EVENT_AFTER_DEPLOY,
)
from .cost import Cost

if TYPE_CHECKING:
    from .player import Player
    from .board import Board
    from .game import Game


class Card:
    """所有卡牌的基类。"""

    def __init__(self, name: str, cost: Cost, targets: Callable[["Player", "Board"], List[Any]],
                 on_turn_start: Optional[Callable] = None,
                 on_turn_end: Optional[Callable] = None,
                 on_phase_start: Optional[Callable] = None,
                 on_phase_end: Optional[Callable] = None):
        self.name = name
        self.cost = cost
        self.can_play = True
        self.targets = targets
        self.echo_level = 0  # 回响等级，0 表示无回响
        self.on_turn_start = on_turn_start
        self.on_turn_end = on_turn_end
        self.on_phase_start = on_phase_start
        self.on_phase_end = on_phase_end

    def __repr__(self) -> str:
        return f"{self.name}({self.cost})"


class MineralCard(Card):
    """矿物卡（离散卡包资源）。
    
    兑换时支付 exchange_cost，兑换后进入手牌。
    打出时无费用，直接产生效果。
    """

    def __init__(
        self,
        name: str,
        mineral_type: str,  # I, G, D, M
        exchange_cost: Cost,
        play_effect: Optional[Callable[["Player", "Game"], Any]] = None,
        stack_limit: int = 1,
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
    ):
        super().__init__(name, Cost(), lambda p, b: [None], on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.exchange_cost = exchange_cost
        self.mineral_type = mineral_type
        self.stack_limit = stack_limit
        self.play_effect_fn = play_effect
        self.tags: List[str] = []

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        if self.play_effect_fn:
            self.play_effect_fn(player, game)
        return True


class MinionCard(Card):
    """异象卡（随从卡）。"""

    def __init__(
        self,
        name: str,
        owner: "Player",
        cost: Cost,
        targets: Callable[["Player", "Board"], List[Any]],
        attack: int,
        health: int,
        special: Optional[Callable[["Minion", "Player", "Game"], Any]] = None,
        keywords: Optional[Dict[str, Any]] = None,
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
        tags: Optional[List[str]] = None,
        hidden_keywords: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.attack = attack
        self.health = health
        self.special = special
        self.owner = owner
        self.keywords = keywords or {}
        self.evolve_to: Optional[str] = None
        self.tags = tags or []
        self.hidden_keywords = hidden_keywords or {}

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        if not game.board.target_check(target):
            return False
        if not game.board.is_valid_deploy(target, player, self):
            print("  无法在此位置部署异象。")
            return False
        if game.board.get_minion_at(target) is not None:
            print("  该格子已被占用")
            return False

        # 鲜血费用：执行献祭（消灭友方异象、触发事件，不管理 b_point）
        if self.cost.b > 0:
            sacrifices = player.request_sacrifice(self.cost.b)
            if sacrifices is None:
                print("  献祭不足，无法部署")
                return False
            for m in sacrifices:
                # 检查献祭次数
                if getattr(m, '_sacrifice_remaining', 0) <= 0:
                    print(f"  {m.name} 献祭次数已耗尽，无法再献祭")
                    return False
                m._sacrifice_remaining -= 1
                blood = m.keywords.get("丰饶", 1)
                # 献祭变身（13号孩子）
                transform_target = getattr(m, "_transform_on_sacrifice", None)
                if transform_target and game:
                    from .card_db import DEFAULT_REGISTRY, CardType
                    target_def = DEFAULT_REGISTRY.get(transform_target)
                    if target_def and target_def.card_type == CardType.MINION:
                        new_minion = game.transform_minion(m, target_def, preserve_summon_turn=False)
                        if new_minion:
                            print(f"  {m.name} 献祭后变身为 {new_minion.name}！")
                            m = new_minion
                            blood = m.keywords.get("丰饶", 1)
                            continue
                # 非变身：消灭异象并触发亡语（免疫献祭的异象除外）
                if getattr(m, '_immune_to_sacrifice', False):
                    print(f"  献祭 {m.name}（免疫献祭，异象保留），获得 {blood}B")
                else:
                    m.current_health = 0
                    m.minion_death()
                    print(f"  献祭 {m.name}，获得 {blood}B")
                game.emit_event(EVENT_SACRIFICE, minion=m, player=player)

        minion = Minion(
            name=self.name,
            owner=player,
            position=target,
            attack=self.attack,
            health=self.health,
            source_card=self,
            board=game.board,
            keywords=self.keywords.copy(),
            on_turn_start=self.on_turn_start,
            on_turn_end=self.on_turn_end,
            on_phase_start=self.on_phase_start,
            on_phase_end=self.on_phase_end,
            statue_top=getattr(self, 'statue_top', False),
            statue_bottom=getattr(self, 'statue_bottom', False),
            statue_pair=getattr(self, 'statue_pair', None),
            on_statue_activate=getattr(self, 'on_statue_activate', None),
            on_statue_fuse=getattr(self, 'on_statue_fuse', None),
            tags=list(self.tags) if hasattr(self, 'tags') else [],
            hidden_keywords=getattr(self, 'hidden_keywords', None),
        )
        minion._extra_targets = extra_targets or []

        # === BEFORE_DEPLOY 事件 ===
        deploy_event = game.emit_event(
            EVENT_BEFORE_DEPLOY,
            source=player,
            target=minion,
            player=player,
            minion=minion,
            card=self,
            position=target,
        )
        if getattr(deploy_event, "cancelled", False):
            print(f"  {minion.name} 的部署被取消")
            return False

        if game.board.place_minion(minion, target):
            # 应用部署增益（雕像等）
            for buff in getattr(player, '_deploy_buffs', []):
                buff(minion)
            print(f"  {player.name} 在 {target} 部署了 {minion.name}")
            minion.summon_turn = game.current_turn
            # 休眠：非迅捷异象部署时具有休眠1
            if "迅捷" not in minion.keywords and "休眠" not in minion.base_keywords:
                minion.base_keywords["休眠"] = 1
                minion.recalculate()
            # 触发全局部署光环钩子
            for hook in getattr(game, "deploy_hooks", []):
                hook(minion)
            if self.special:
                import inspect
                sig = inspect.signature(self.special)
                if len(sig.parameters) >= 4:
                    self.special(minion, player, game, extra_targets or [])
                else:
                    self.special(minion, player, game)
            game.emit_event(EVENT_DEPLOYED, minion=minion, player=player, card=self)

            # === AFTER_DEPLOY 事件 ===
            game.emit_event(
                EVENT_AFTER_DEPLOY,
                source=player,
                target=minion,
                player=player,
                minion=minion,
                card=self,
                position=target,
            )
            return True
        return False


class Strategy(Card):
    """策略卡。打出后立即生效。"""

    def __init__(
        self,
        name: str,
        cost: Cost,
        effect_fn: Optional[Callable[["Player", Any, "Game"], bool]],
        targets: Callable[["Player", "Board"], List[Any]],
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
        hidden_keywords: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.effect_fn = effect_fn
        self.hidden_keywords = hidden_keywords or {}

    def effect(self, player: "Player", target: Any, game: "Game", extra_targets: Optional[List[Any]] = None) -> bool:
        if self.effect_fn is None:
            return True
        # 指向保护（"取消该指向"等机制）
        if game.is_target_protected(target, self):
            return True
        import inspect
        sig = inspect.signature(self.effect_fn)
        param_count = len(sig.parameters)
        if param_count >= 4:
            return self.effect_fn(player, target, game, extra_targets or [])
        else:
            return self.effect_fn(player, target, game)


class Conspiracy(Card):
    """阴谋卡。激活后进入活跃阴谋区，条件满足时触发。

    通过 EventBus 的通配符监听器 '*' 监听所有事件，
    condition_fn 自行判断是否响应。
    """

    def __init__(
        self,
        name: str,
        cost: Cost,
        condition_fn: Callable[["Game", Dict[str, Any], "Player"], bool],
        effect_fn: Callable[["Game", Dict[str, Any], "Player"], Any],
        targets: Callable[["Player", "Board"], List[Any]],
        on_turn_start: Optional[Callable] = None,
        on_turn_end: Optional[Callable] = None,
        on_phase_start: Optional[Callable] = None,
        on_phase_end: Optional[Callable] = None,
    ):
        super().__init__(name, cost, targets, on_turn_start, on_turn_end, on_phase_start, on_phase_end)
        self.condition_fn = condition_fn
        self.effect_fn = effect_fn
        self._listener_owner_id: Optional[int] = None  # EventBus 批量注销用


class Minion:
    """战场上的战斗异象。"""

    def __init__(
        self,
        name: str,
        owner: "Player",
        position: Any,
        attack: int,
        health: int,
        source_card: MinionCard,
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
        # 动态注入的回合效果（金西瓜片、重生锚等赋予）
        self._injected_turn_start: List[Callable] = []
        self._injected_turn_end: List[Callable] = []
        self.statue_top = statue_top
        self.statue_bottom = statue_bottom
        self.statue_pair = statue_pair
        self.on_statue_activate = on_statue_activate
        self.on_statue_fuse = on_statue_fuse
        self.tags = tags or []
        self.hidden_keywords = hidden_keywords or {}

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

        # 临时修饰（直到回合结束等）
        self.temp_attack_bonus = 0
        self.temp_health_bonus = 0
        self.temp_max_health_bonus = 0
        self.temp_keywords: Dict[str, Any] = {}

        # 临时光环回调（具有）
        self._aura_attack_fns: List[Callable[["Minion"], int]] = []
        self._aura_health_fns: List[Callable[["Minion"], int]] = []
        self._aura_max_health_fns: List[Callable[["Minion"], int]] = []
        self._aura_keyword_fns: List[Callable[["Minion"], Dict[str, Any]]] = []

        # 本 minion 向其它异象提供的光环记录（死亡/离场时自动清理）
        self._provided_auras: List[Tuple["Minion", str, Callable]] = []

        self._fear_active = self.base_keywords.get("恐惧", False)

        # "也算作是本异象"（命名牌等效果赋予）
        self.alias_name: Optional[str] = None

        # 伤害来源追踪（豪猪/环形虫/鹳/鬣狗/水螅岩等需要）
        self._last_damage_source: Optional["Minion"] = None
        self._last_damage_type: str = ""
        self._last_damage_amount: int = 0

        # 献祭次数限制（"献祭X"：可被献祭X次）
        sacrifice_kw = self.base_keywords.get("献祭", False)
        if sacrifice_kw is True:
            self._sacrifice_remaining = 1
        elif isinstance(sacrifice_kw, int):
            self._sacrifice_remaining = sacrifice_kw
        else:
            self._sacrifice_remaining = 0

        # 战斗伤害回调
        self._on_take_combat_damage: List[Callable[[], None]] = []

        # 当前生效值
        self.current_attack = attack
        self.current_health = health
        self.current_max_health = health
        self.keywords: Dict[str, Any] = dict(self.base_keywords)

        self.recalculate()

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
        from .card_db import DEFAULT_REGISTRY, CardType
        card_def = DEFAULT_REGISTRY.get(next_name)
        if not card_def or card_def.card_type != CardType.MINION:
            print(f"  {self.name} 的下一个形态 {next_name} 未找到或不是异象")
            return False
        new_minion = game.transform_minion(self, card_def, preserve_summon_turn=True)
        if new_minion:
            print(f"  {self.name} 成长为 {new_minion.name}！")
            return True
        return False

    def recalculate(self):
        """重新计算当前生效的面板和关键词。"""
        # 攻击力
        aura_atk = sum(fn(self) for fn in self._aura_attack_fns)
        self.current_attack = self.base_attack + self.perm_attack_bonus + self.temp_attack_bonus + aura_atk

        # 最大生命值
        aura_max = sum(fn(self) for fn in self._aura_max_health_fns)
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
        for fn in self._aura_keyword_fns:
            for k, v in fn(self).items():
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
        self._aura_attack_fns.clear()
        self._aura_health_fns.clear()
        self._aura_max_health_fns.clear()
        self._aura_keyword_fns.clear()
        self._fear_active = False
        self.current_health = self.base_health
        self.current_max_health = self.base_max_health
        self.recalculate()

    def clear_temp_effects(self):
        """回合结束时调用：清除所有临时修饰。"""
        if self.temp_attack_bonus or self.temp_health_bonus or self.temp_max_health_bonus or self.temp_keywords:
            self.temp_attack_bonus = 0
            self.temp_health_bonus = 0
            self.temp_max_health_bonus = 0
            self.temp_keywords.clear()
            self.recalculate()

    # ----- 光环回调注册 -----
    def add_aura_attack(self, fn: Callable[["Minion"], int]):
        self._aura_attack_fns.append(fn)
        self.recalculate()

    def remove_aura_attack(self, fn: Callable[["Minion"], int]):
        if fn in self._aura_attack_fns:
            self._aura_attack_fns.remove(fn)
            self.recalculate()

    def add_aura_max_health(self, fn: Callable[["Minion"], int]):
        self._aura_max_health_fns.append(fn)
        self.recalculate()

    def remove_aura_max_health(self, fn: Callable[["Minion"], int]):
        if fn in self._aura_max_health_fns:
            self._aura_max_health_fns.remove(fn)
            self.recalculate()

    def add_aura_keywords(self, fn: Callable[["Minion"], Dict[str, Any]]):
        self._aura_keyword_fns.append(fn)
        self.recalculate()

    def remove_aura_keywords(self, fn: Callable[["Minion"], Dict[str, Any]]):
        if fn in self._aura_keyword_fns:
            self._aura_keyword_fns.remove(fn)
            self.recalculate()

    # ----- 光环提供者 API（自动追踪，便于死亡/离场时清理） -----

    def provide_aura_attack(self, target: "Minion", fn: Callable[["Minion"], int]) -> None:
        """向目标提供攻击力光环，并记录以便自动清理。"""
        target.add_aura_attack(fn)
        self._provided_auras.append((target, "attack", fn))

    def provide_aura_max_health(self, target: "Minion", fn: Callable[["Minion"], int]) -> None:
        """向目标提供最大生命值光环，并记录以便自动清理。"""
        target.add_aura_max_health(fn)
        self._provided_auras.append((target, "max_health", fn))

    def provide_aura_keywords(self, target: "Minion", fn: Callable[["Minion"], Dict[str, Any]]) -> None:
        """向目标提供关键词光环，并记录以便自动清理。"""
        target.add_aura_keywords(fn)
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

    def minion_death(self):
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

                self.clear_all_provided_auras()
                self.board.remove_minion(self.position)

                # 清理本异象的 EventBus 监听器
                if game and hasattr(self, '_event_owner_id'):
                    game.unregister_listeners_by_owner(self._event_owner_id)

                if game:
                    game.emit_event(EVENT_DEATH, minion=self, player=self.owner)

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
                    if deathrattle:
                        def make_dr(m=self, dr=deathrattle):
                            def fn():
                                print(f"  {m.name} 的亡语触发")
                                dr(m, m.owner, m.board)
                            return fn
                        game.effect_queue.queue(f"亡语 [{self.name}]", make_dr())

            if self.board.game_ref:
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
        # 迅捷覆盖休眠（光环赋予的迅捷应能抵消部署时的休眠）
        if "迅捷" in self.keywords:
            return True
        if self.keywords.get("休眠", 0) > 0:
            return False
        return self.summon_turn < turn_number

    def attack_target(self, target: Any):
        from .player import Player
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
            # 串击/穿刺/穿透：对同列所有敌方异象造成伤害
            if self.keywords.get("串击", False) or self.keywords.get("穿刺", False) or self.keywords.get("穿透", False):
                col = self.position[1]
                enemies = [m for m in self.board.get_enemy_minions_in_column(col, self.owner) if m.is_alive()]
                if enemies:
                    print(f"  {self.name} 串击同列所有敌方异象")
                    for enemy in enemies:
                        enemy.take_damage(self.current_attack, source_minion=self, source_type="combat", is_combat_damage=True)
                        if enemy.is_alive():
                            spike = enemy.keywords.get("尖刺", 0)
                            if spike > 0:
                                print(f"  {enemy.name} 的尖刺反弹 {spike} 点伤害")
                                self.take_damage(spike, source_type="combat", is_combat_damage=True)
                else:
                    player_target = self.board.game_ref.p2 if self.owner == self.board.game_ref.p1 else self.board.game_ref.p1
                    print(f"  {self.name} 直接攻击 {player_target.name}，造成 {self.current_attack} 点伤害")
                    player_target.health_change(-self.current_attack)
            else:
                print(f"  {self.name} 攻击 {target.name}，造成 {self.current_attack} 点伤害")
                target.take_damage(self.current_attack, source_minion=self, source_type="combat", is_combat_damage=True)
                target._last_attacker = self
                if target.is_alive():
                    spike = target.keywords.get("尖刺", 0)
                    if spike > 0:
                        print(f"  {target.name} 的尖刺反弹 {spike} 点伤害")
                        self.take_damage(spike, source_type="combat", is_combat_damage=True)
        elif isinstance(target, Player):
            print(f"  {self.name} 直接攻击 {target.name}，造成 {self.current_attack} 点伤害")
            target.health_change(-self.current_attack)

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
