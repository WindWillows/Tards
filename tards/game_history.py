"""
GameHistory —— 机器日志模块（v2.0）

记录对局进程中所有按回合索引的关键历史变量，供卡牌监听器和效果函数查询。
所有数据由 Game.emit_event 事件驱动自动更新，无需卡牌手动上报。

v2.0 新增能力：
1. 动态计数器：运行时可注册任意键名的计数器，无需预定义字段。
2. 事件流水：保存每回合完整事件日志，支持事后回溯查询（过滤、计数、聚合）。
3. 统一监听器：提供 listen / unlisten / unlisten_by_owner 统一 API，
   替代散落在 EventBus、Card.on()、effect_utils 中的多种注册方式。
   支持 once（只触发一次）、condition（条件过滤）、priority（优先级）。

设计原则：
- 架构清晰：TurnRecord 负责单回合快照，GameHistory 负责全局管理与查询。
- 按需查询：提供丰富的高层查询 API，避免卡牌效果直接遍历底层结构。
- 向后兼容：保留 Game._state_log 等旧机制，GameHistory 作为补充层存在。
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
    """调用监听器回调，自动适配 (event) 或 (event, game) 两种签名。"""
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
    """GameHistory 统一管理的监听器条目。"""

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
# 单回合快照
# =============================================================================

class TurnRecord:
    """单回合的历史快照。所有计数器按玩家隔离，默认值为 0。"""

    def __init__(self, turn: int):
        self.turn = turn

        # ── 出牌统计 ──
        self.cards_played: Dict["Player", int] = defaultdict(int)
        self.minions_deployed: Dict["Player", int] = defaultdict(int)
        self.strategies_played: Dict["Player", int] = defaultdict(int)
        self.total_strategies_played: int = 0  # 双方合计（血溅白练等需要）
        self.minerals_played: Dict["Player", int] = defaultdict(int)
        self.conspiracies_activated: Dict["Player", int] = defaultdict(int)

        # ── 资源与费用 ──
        self.sacrifices_made: Dict["Player", int] = defaultdict(int)
        self.blood_spent: Dict["Player", int] = defaultdict(int)
        self.developed_count: Dict["Player", int] = defaultdict(int)

        # ── 抽弃磨 ──
        self.cards_drawn: Dict["Player", int] = defaultdict(int)
        self.cards_discarded: Dict["Player", int] = defaultdict(int)
        self.cards_milled: Dict["Player", int] = defaultdict(int)

        # ── 战斗与生存 ──
        self.damage_dealt_to_players: Dict["Player", int] = defaultdict(int)
        self.damage_dealt_to_minions: Dict["Player", int] = defaultdict(int)
        self.healing_received: Dict["Player", int] = defaultdict(int)
        self.attacks_made: Dict["Player", int] = defaultdict(int)

        # ── 资源上限变化 ──
        self.t_max_lost: Dict["Player", int] = defaultdict(int)

        # ── 阶段级变量（在结算阶段开始时清空）──
        self.health_lost_this_phase: Dict["Player", int] = defaultdict(int)

        # ── 实体追踪（精确列表）──
        self.deployed_minions: List["Minion"] = []
        self.died_minions: List["Minion"] = []
        self.sacrificed_minions: List["Minion"] = []

        # ── v2.0：动态计数器（任意键名 -> 玩家 -> 数值）──
        self._custom_counters: Dict[str, Dict["Player", int]] = defaultdict(
            lambda: defaultdict(int)
        )

        # ── v2.0：事件流水（原始事件完整数据）──
        self._event_log: List[Dict[str, Any]] = []

    # ── 预定义计数器更新（保留现有逻辑）──

    def add_card_played(self, player: "Player", card_type: str) -> None:
        self.cards_played[player] += 1
        if card_type == "strategy":
            self.strategies_played[player] += 1
            self.total_strategies_played += 1
        elif card_type == "mineral":
            self.minerals_played[player] += 1
        elif card_type == "conspiracy":
            self.conspiracies_activated[player] += 1

    def add_minion_deployed(self, minion: "Minion", player: "Player") -> None:
        self.minions_deployed[player] += 1
        self.deployed_minions.append(minion)

    def add_sacrifice(self, player: "Player", minion: Optional["Minion"] = None,
                      blood: int = 0) -> None:
        self.sacrifices_made[player] += 1
        self.blood_spent[player] += blood
        if minion is not None:
            self.sacrificed_minions.append(minion)

    def add_draw(self, player: "Player") -> None:
        self.cards_drawn[player] += 1

    def add_discard(self, player: "Player") -> None:
        self.cards_discarded[player] += 1

    def add_mill(self, player: "Player") -> None:
        self.cards_milled[player] += 1

    def add_develop(self, player: "Player") -> None:
        self.developed_count[player] += 1

    def add_damage_to_player(self, dealer: "Player", amount: int) -> None:
        self.damage_dealt_to_players[dealer] += amount

    def add_damage_to_minion(self, dealer: "Player", amount: int) -> None:
        self.damage_dealt_to_minions[dealer] += amount

    def add_healing(self, player: "Player", amount: int) -> None:
        self.healing_received[player] += amount

    def add_attack(self, player: "Player") -> None:
        self.attacks_made[player] += 1

    def add_minion_death(self, minion: "Minion") -> None:
        self.died_minions.append(minion)

    # ── v2.0：动态计数器 ──

    def increment(self, key: str, player: "Player", delta: int = 1) -> None:
        """增加动态计数器。"""
        self._custom_counters[key][player] += delta

    def get(self, key: str, player: "Player") -> int:
        """获取动态计数器值。"""
        return self._custom_counters[key].get(player, 0)

    def set_custom(self, key: str, player: "Player", value: int) -> None:
        """直接覆盖动态计数器值。"""
        self._custom_counters[key][player] = value

    # ── v2.0：事件流水 ──

    def log_event(self, event_type: str, **kwargs) -> None:
        """记录一条原始事件到本回合流水。"""
        entry: Dict[str, Any] = {"event_type": event_type}
        # 浅拷贝 kwargs，避免后续修改影响已记录的事件
        for k, v in kwargs.items():
            entry[k] = v
        self._event_log.append(entry)

    def query_events(
        self,
        event_type: Optional[str] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """查询本回合事件流水。"""
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
# 全局管理器
# =============================================================================

class GameHistory:
    """
    全局机器日志。按回合存储 TurnRecord，并提供跨回合聚合查询与统一监听器管理。

    使用方式：
        game.history.cards_played_this_turn(player)
        game.history.total_sacrifices(player)
        game.history.damage_dealt_to_players(turn=3, player=p1)

    v2.0 新增：
        # 动态计数器
        game.history.increment("odd_cost_cards", player)
        game.history.get_custom("odd_cost_cards", player)
        game.history.total_custom("odd_cost_cards", player)

        # 事件流水回溯
        game.history.query_events(turn=2, event_type=EVENT_CARD_PLAYED,
                                  filter_fn=lambda e: e["card"].cost.total() % 2 == 1)

        # 统一监听器
        lid = game.history.listen(EVENT_TURN_START, my_callback, owner=minion)
        game.history.unlisten_by_owner(minion)   # 异象死亡时自动清理
    """

    def __init__(self, game: Any):
        self.game = game
        self._records: List[TurnRecord] = []
        self._current: TurnRecord = TurnRecord(0)

        # ── v2.0：统一监听器管理 ──
        self._listener_entries: Dict[int, ListenerEntry] = {}
        self._next_listener_id = 1
        self._owner_registry: Dict[int, List[int]] = {}  # id(owner) -> [listener_id, ...]

    # ------------------------------------------------------------------
    # 回合推进
    # ------------------------------------------------------------------

    def advance_turn(self, turn: int) -> None:
        """进入新回合。将当前快照归档，并创建新的 TurnRecord。"""
        if self._current.turn > 0:
            self._records.append(self._current)
        self._current = TurnRecord(turn)

    # ------------------------------------------------------------------
    # 事件处理（由 Game.emit_event 驱动）
    # ------------------------------------------------------------------

    def on_event(self, event_type: str, **kwargs) -> None:
        """根据事件类型自动更新当前回合记录，并写入事件流水。"""
        from .constants import (
            EVENT_CARD_PLAYED,
            EVENT_DEPLOYED,
            EVENT_SACRIFICE,
            EVENT_DRAW,
            EVENT_DISCARDED,
            EVENT_MILLED,
            EVENT_DEVELOPED,
            EVENT_PLAYER_DAMAGE,
            EVENT_DEATH,
            EVENT_HEALTH_CHANGED,
            EVENT_DAMAGED,
            EVENT_ATTACKED,
            EVENT_T_MAX_CHANGED,
            EVENT_PHASE_START,
        )

        player = kwargs.get("player")
        card = kwargs.get("card")
        minion = kwargs.get("minion")

        if event_type == EVENT_CARD_PLAYED and player is not None:
            ct = self._classify_card(card)
            self._current.add_card_played(player, ct)

        elif event_type == EVENT_DEPLOYED and minion is not None:
            owner = getattr(minion, "owner", None) or player
            if owner is not None:
                self._current.add_minion_deployed(minion, owner)

        elif event_type == EVENT_SACRIFICE and player is not None:
            blood = kwargs.get("blood", 0)
            self._current.add_sacrifice(player, minion, blood)

        elif event_type == EVENT_DRAW and player is not None:
            self._current.add_draw(player)

        elif event_type == EVENT_DISCARDED and player is not None:
            self._current.add_discard(player)

        elif event_type == EVENT_MILLED and player is not None:
            self._current.add_mill(player)

        elif event_type == EVENT_DEVELOPED and player is not None:
            self._current.add_develop(player)

        elif event_type == EVENT_PLAYER_DAMAGE:
            source = kwargs.get("source")
            damage = kwargs.get("damage", 0)
            dealer = None
            if damage:
                if hasattr(source, "side"):
                    dealer = source
                elif hasattr(source, "owner"):
                    dealer = source.owner
                if dealer is not None:
                    self._current.add_damage_to_player(dealer, damage)

        elif event_type == EVENT_DAMAGED and minion is not None:
            source_minion = kwargs.get("source_minion")
            actual = kwargs.get("actual", 0)
            if actual and source_minion is not None and source_minion.owner is not None:
                self._current.add_damage_to_minion(source_minion.owner, actual)

        elif event_type == EVENT_DEATH and minion is not None:
            self._current.add_minion_death(minion)

        elif event_type == EVENT_ATTACKED:
            attacker = kwargs.get("source") or minion
            if hasattr(attacker, "owner") and attacker.owner is not None:
                self._current.add_attack(attacker.owner)

        elif event_type == EVENT_T_MAX_CHANGED and player is not None:
            old = kwargs.get("old", 0)
            new = kwargs.get("new", 0)
            if new < old:
                self._current.t_max_lost[player] += old - new

        elif event_type == EVENT_HEALTH_CHANGED and player is not None:
            delta = kwargs.get("delta", 0)
            if delta > 0:
                self._current.add_healing(player, delta)
            elif delta < 0:
                self._current.health_lost_this_phase[player] += -delta

        elif event_type == EVENT_PHASE_START:
            phase = kwargs.get("phase")
            if phase == getattr(self.game, "PHASE_RESOLVE", None):
                self._current.health_lost_this_phase.clear()

        # ── v2.0：写入事件流水 ──
        self._current.log_event(event_type, **kwargs)

    @staticmethod
    def _classify_card(card: Any) -> str:
        from .cards import MinionCard, Strategy, MineralCard, Conspiracy
        if isinstance(card, MinionCard):
            return "minion"
        if isinstance(card, Strategy):
            return "strategy"
        if isinstance(card, MineralCard):
            return "mineral"
        if isinstance(card, Conspiracy):
            return "conspiracy"
        return "unknown"

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
    # v2.0：统一监听器管理
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
        """统一注册事件监听器。返回 listener_id 用于注销。

        Args:
            event_type: 事件类型常量（如 EVENT_TURN_START）。
            callback:   回调函数，签名 fn(event: GameEvent, game: Game) -> None。
            owner:      监听器所属对象（如 Minion）。死亡/离场时会自动清理。
            once:       是否只触发一次，触发后自动注销。
            condition:  额外条件过滤，签名 fn(event: GameEvent) -> bool。
            priority:   优先级，越小越先执行（负数可用于拦截）。

        Returns:
            listener_id: 正整数，后续可用 unlisten(lid) 注销。
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

        # 注册到底层 EventBus（Game 层封装）
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
        """注册只触发一次的监听器。触发后自动注销。"""
        return self.listen(event_type, callback, owner, once=True, condition=condition, priority=priority)

    def unlisten(self, listener_id: int) -> bool:
        """注销单个监听器。成功返回 True，不存在返回 False。"""
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
        """注销某 owner（如 Minion/Card）的所有监听器。返回注销数量。"""
        oid = id(owner)
        lids = list(self._owner_registry.pop(oid, []))
        count = 0
        for lid in lids:
            if self.unlisten(lid):
                count += 1
        return count

    def unlisten_all(self) -> int:
        """注销所有通过 GameHistory 注册的监听器。返回注销数量。"""
        lids = list(self._listener_entries.keys())
        count = 0
        for lid in lids:
            if self.unlisten(lid):
                count += 1
        return count

    def listener_count(self, owner: Optional[Any] = None) -> int:
        """返回监听器总数。若指定 owner，返回该 owner 的监听器数。"""
        if owner is None:
            return len(self._listener_entries)
        oid = id(owner)
        return len(self._owner_registry.get(oid, []))

    # =============================================================================
    # v2.0：动态计数器 API
    # =============================================================================

    def increment(self, key: str, player: "Player", delta: int = 1) -> None:
        """增加当前回合的动态计数器。"""
        self._current.increment(key, player, delta)

    def decrement(self, key: str, player: "Player", delta: int = 1) -> None:
        """减少当前回合的动态计数器。"""
        self._current.increment(key, player, -delta)

    def get_custom(self, key: str, player: "Player", turn: Optional[int] = None) -> int:
        """查询某回合的动态计数器值。turn=None 表示当前回合。"""
        return self._get_record(turn).get(key, player)

    def total_custom(self, key: str, player: "Player", up_to_turn: Optional[int] = None) -> int:
        """跨回合累计动态计数器值。"""
        total = 0
        for rec in self._records + [self._current]:
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            total += rec.get(key, player)
        return total

    def set_custom(self, key: str, player: "Player", value: int) -> None:
        """直接设置当前回合的动态计数器值（覆盖）。"""
        self._current.set_custom(key, player, value)

    # =============================================================================
    # v2.0：事件流水查询 API
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
        """计数事件流水中的匹配条目。"""
        return len(self.query_events(turn, event_type, filter_fn))

    def sum_events(
        self,
        turn: Optional[int] = None,
        event_type: Optional[str] = None,
        value_fn: Optional[Callable[[Dict[str, Any]], int]] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """对事件流水做聚合求和。

        Args:
            value_fn: 从事件 entry 中提取数值。
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
        """查询出牌事件的详细流水（快捷方法）。"""
        from .constants import EVENT_CARD_PLAYED
        return self.query_events(turn, EVENT_CARD_PLAYED, filter_fn)

    def count_cards_played(
        self,
        turn: Optional[int] = None,
        filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> int:
        """计数出牌事件（快捷方法）。"""
        return len(self.query_cards_played(turn, filter_fn))

    # =============================================================================
    # 单回合查询（保留现有 API）
    # =============================================================================

    def cards_played_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).cards_played[player]

    def minions_deployed_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).minions_deployed[player]

    def strategies_played_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).strategies_played[player]

    def total_strategies_played_this_turn(self, turn: Optional[int] = None) -> int:
        """本回合双方合计使用的策略卡数（血溅白练等需要）。"""
        return self._get_record(turn).total_strategies_played

    def minerals_played_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).minerals_played[player]

    def conspiracies_activated_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).conspiracies_activated[player]

    def sacrifices_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).sacrifices_made[player]

    def blood_spent_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).blood_spent[player]

    def developed_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).developed_count[player]

    def cards_drawn_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).cards_drawn[player]

    def cards_discarded_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).cards_discarded[player]

    def cards_milled_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).cards_milled[player]

    def damage_dealt_to_players_this_turn(self, dealer: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).damage_dealt_to_players[dealer]

    def damage_dealt_to_minions_this_turn(self, dealer: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).damage_dealt_to_minions[dealer]

    def healing_received_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).healing_received[player]

    def attacks_made_this_turn(self, player: "Player", turn: Optional[int] = None) -> int:
        return self._get_record(turn).attacks_made[player]

    def minions_deployed_list_this_turn(self, turn: Optional[int] = None) -> List["Minion"]:
        return list(self._get_record(turn).deployed_minions)

    def minions_died_list_this_turn(self, turn: Optional[int] = None) -> List["Minion"]:
        return list(self._get_record(turn).died_minions)

    def minions_sacrificed_list_this_turn(self, turn: Optional[int] = None) -> List["Minion"]:
        return list(self._get_record(turn).sacrificed_minions)

    # =============================================================================
    # 跨回合聚合查询（保留现有 API）
    # =============================================================================

    def total_cards_played(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("cards_played", player, up_to_turn)

    def total_minions_deployed(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("minions_deployed", player, up_to_turn)

    def total_strategies_played(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("strategies_played", player, up_to_turn)

    def total_sacrifices(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("sacrifices_made", player, up_to_turn)

    def total_blood_spent(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("blood_spent", player, up_to_turn)

    def total_developed(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("developed_count", player, up_to_turn)

    def total_cards_drawn(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("cards_drawn", player, up_to_turn)

    def total_cards_discarded(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("cards_discarded", player, up_to_turn)

    def total_cards_milled(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("cards_milled", player, up_to_turn)

    def total_damage_to_players(self, dealer: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("damage_dealt_to_players", dealer, up_to_turn)

    def total_damage_to_minions(self, dealer: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("damage_dealt_to_minions", dealer, up_to_turn)

    def total_healing_received(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("healing_received", player, up_to_turn)

    def total_attacks_made(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("attacks_made", player, up_to_turn)

    def total_t_max_lost(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return self._sum_player("t_max_lost", player, up_to_turn)

    def health_lost_this_phase(self, player: "Player") -> int:
        """本出牌阶段该玩家失去的HP总量（含伤害）。"""
        return self._current.health_lost_this_phase.get(player, 0)

    def total_minion_deaths(self, player: Optional["Player"] = None,
                            up_to_turn: Optional[int] = None) -> int:
        total = 0
        for rec in self._records + [self._current]:
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            if player is None:
                total += len(rec.died_minions)
            else:
                total += sum(1 for m in rec.died_minions if m.owner is player)
        return total

    def total_minions_killed(self, player: "Player", up_to_turn: Optional[int] = None) -> int:
        return 0

    # =============================================================================
    # 高级查询（保留现有 API）
    # =============================================================================

    def last_died_minion(self, player: Optional["Player"] = None,
                         up_to_turn: Optional[int] = None) -> Optional["Minion"]:
        """返回最近一只死亡的异象。若指定 player，则只统计该玩家拥有的异象。"""
        for rec in reversed(self._records + [self._current]):
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            if player is None:
                if rec.died_minions:
                    return rec.died_minions[-1]
            else:
                for m in reversed(rec.died_minions):
                    if m.owner is player:
                        return m
        return None

    def last_sacrificed_minion(self, player: Optional["Player"] = None,
                               up_to_turn: Optional[int] = None) -> Optional["Minion"]:
        """返回最近一只被献祭的异象。"""
        for rec in reversed(self._records + [self._current]):
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            if player is None:
                if rec.sacrificed_minions:
                    return rec.sacrificed_minions[-1]
            else:
                for m in reversed(rec.sacrificed_minions):
                    if m.owner is player:
                        return m
        return None

    def last_deployed_minion(self, player: Optional["Player"] = None,
                             up_to_turn: Optional[int] = None) -> Optional["Minion"]:
        """返回最近一只部署的异象。"""
        for rec in reversed(self._records + [self._current]):
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            if player is None:
                if rec.deployed_minions:
                    return rec.deployed_minions[-1]
            else:
                for m in reversed(rec.deployed_minions):
                    if m.owner is player:
                        return m
        return None

    def was_minion_deployed_this_turn(self, minion: "Minion") -> bool:
        """检查某异象是否在本回合部署。"""
        return minion in self._current.deployed_minions

    def player_deployed_any_minion_this_turn(self, player: "Player") -> bool:
        """检查某玩家本回合是否部署过任何异象。"""
        return self._current.minions_deployed.get(player, 0) > 0

    # =============================================================================
    # 内部辅助
    # =============================================================================

    def _sum_player(self, attr: str, player: "Player",
                    up_to_turn: Optional[int] = None) -> int:
        total = 0
        for rec in self._records + [self._current]:
            if up_to_turn is not None and rec.turn > up_to_turn:
                continue
            total += getattr(rec, attr).get(player, 0)
        return total

    def summary(self) -> Dict[str, Any]:
        return {
            "current_turn": self._current.turn,
            "archived_turns": [rec.turn for rec in self._records],
            "current": {
                "cards_played": {getattr(p, "name", str(p)): v for p, v in self._current.cards_played.items()},
                "minions_deployed": {getattr(p, "name", str(p)): v for p, v in self._current.minions_deployed.items()},
                "strategies_played": {getattr(p, "name", str(p)): v for p, v in self._current.strategies_played.items()},
                "sacrifices_made": {getattr(p, "name", str(p)): v for p, v in self._current.sacrifices_made.items()},
                "blood_spent": {getattr(p, "name", str(p)): v for p, v in self._current.blood_spent.items()},
                "developed": {getattr(p, "name", str(p)): v for p, v in self._current.developed_count.items()},
                "cards_drawn": {getattr(p, "name", str(p)): v for p, v in self._current.cards_drawn.items()},
                "damage_to_players": {getattr(p, "name", str(p)): v for p, v in self._current.damage_dealt_to_players.items()},
                "healing": {getattr(p, "name", str(p)): v for p, v in self._current.healing_received.items()},
                "t_max_lost": {getattr(p, "name", str(p)): v for p, v in self._current.t_max_lost.items()},
                "deaths": len(self._current.died_minions),
                "deployments": len(self._current.deployed_minions),
            },
        }
