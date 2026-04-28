from typing import Any, Callable, Dict, List, Optional
from .board import Board
from .cards import MineralCard, Minion, MinionCard, Strategy, Conspiracy
from .card_db import DEFAULT_REGISTRY, CardType, Pack
from .constants import (
    EVENT_BELL,
    EVENT_CARD_PLAYED,
    EVENT_DEATH,
    EVENT_DEPLOY,
    EVENT_DRAW,
    EVENT_PHASE_END,
    EVENT_PHASE_START,
    EVENT_PLAYER_DAMAGE,
    EVENT_SACRIFICE,
    EVENT_TURN_END,
    EVENT_TURN_START,
)
from .effect_queue import EffectQueue
from .events import EventBus, GameEvent
from .player import Player


class Game:
    PHASE_START = "start"
    PHASE_DRAW = "draw"
    PHASE_ACTION = "action"
    PHASE_RESOLVE = "resolve"
    PHASE_END = "end"

    def __init__(
        self,
        player1: Player,
        player2: Player,
        action_provider: Optional[Callable[["Game", Player, Player], Optional[Dict[str, Any]]]] = None,
        discover_provider: Optional[Callable[["Game", Player, List[Any], int], Optional[Any]]] = None,
    ):
        self.p1 = player1
        self.p2 = player2
        self.players = [player1, player2]
        self.board = Board()
        self.current_turn = 0
        self.current_phase = self.PHASE_START
        self.current_player: Optional[Player] = None
        self.first_player: Optional[Player] = None
        self.game_over = False
        self.winner: Optional[Player] = None
        self.action_provider = action_provider
        self.discover_provider = discover_provider
        self.choice_provider: Optional[Callable[["Game", "Player", List[str], str], Optional[str]]] = None
        self.effect_queue = EffectQueue(self)
        self.event_bus = EventBus(self)
        self.resolve_step_callback = None

        # 雕像拼装待处理队列
        self._pending_statues: List[Dict[str, Any]] = []

        # 部署光环/钩子（全局监听新异象部署）
        self.deploy_hooks: List[Callable[["Minion"], None]] = []

        # 延迟效果队列（下回合开始时/回合结束时触发）
        self._delayed_effects: List[Dict[str, Any]] = []

        # 全局部署限制（如疣猪"双方无法部署花费≤4T的异象"）
        self._global_deploy_restrictions: List[Callable[["Player", Any], bool]] = []

        # 伤害替换效果（用于"取消该伤害"等机制）
        self._damage_replacements: List[Dict[str, Any]] = []
        # 指向保护效果（用于"取消该指向"等机制）
        self._target_protections: List[Dict[str, Any]] = []

        # 本回合部署追踪（跳蛛/鼯鼱/蟒等需要判断部署顺序）
        self._deployed_this_turn: Dict["Player", List["Minion"]] = {}
        # 本回合对玩家造成的伤害累计（木鹊等需要查询）
        self._damage_dealt_to_players_this_turn: Dict["Player", int] = {}

        # 绑定引用
        self.board.game_ref = self
        for p in self.players:
            p.board_ref = self.board

    # -------------------------------------------------------------------
    # 事件总线 API
    # -------------------------------------------------------------------

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

    # -------------------------------------------------------------------
    # emit_event：新版事件总线（阴谋已通过 EventBus 通配符监听器触发）
    # -------------------------------------------------------------------

    def emit_event(self, event_type: str, source: Optional[Any] = None, **kwargs) -> Optional[GameEvent]:
        if self.game_over:
            return None

        # === 新版事件总线（含通配符监听器，阴谋在此触发） ===
        event = self.event_bus.emit(event_type, source=source, **kwargs)

        # === 自动化时间节点效果（回合开始/结束等） ===
        event_data = dict(event_type=event_type, **kwargs)
        if event_type in (EVENT_TURN_START, EVENT_TURN_END, EVENT_PHASE_START,
                          EVENT_PHASE_END, EVENT_DEPLOY, EVENT_DEATH,
                          EVENT_CARD_PLAYED, EVENT_DRAW, EVENT_SACRIFICE,
                          EVENT_BELL, EVENT_PLAYER_DAMAGE):
            self._trigger_auto_effects(event_type, event_data)

            # 雕像拼装检测
            if event_type == EVENT_DEPLOY:
                self._check_statue_pair(event_data)
            if event_type == EVENT_PHASE_END and event_data.get("phase") == self.PHASE_RESOLVE:
                self._resolve_statue_fusions()
            if event_type == EVENT_TURN_END:
                self._resolve_statue_fusions()

        # 部署计数（用于跳蛛/鼯鼱/蟒等判断部署顺序）
        from .constants import EVENT_DEPLOYED
        if event_type == EVENT_DEPLOYED:
            minion = kwargs.get("minion")
            if minion and hasattr(minion, "owner"):
                self._deployed_this_turn.setdefault(minion.owner, []).append(minion)

        # 每回合对玩家伤害累计（用于木鹊等）
        if event_type == EVENT_PLAYER_DAMAGE:
            target_player = kwargs.get("player")
            damage = kwargs.get("damage", 0)
            if target_player and damage:
                self._damage_dealt_to_players_this_turn[target_player] = (
                    self._damage_dealt_to_players_this_turn.get(target_player, 0) + damage
                )

        if not self.effect_queue.is_resolving():
            self.refresh_all_auras()

        return event

    # -------------------------------------------------------------------
    # 阴谋注册/注销（通过 EventBus 通配符监听器实现）
    # -------------------------------------------------------------------

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
            # condition_fn 旧签名：(game, event_data_dict, player)
            if conspiracy.condition_fn(self, event.data, player):
                # 满足条件：移出活跃区，注销监听器，推入 EffectQueue 执行
                player.active_conspiracies.remove(conspiracy)
                self.unregister_listeners_by_owner(owner_id)

                def make_trigger(c=conspiracy, p=player, ev=event):
                    def trigger():
                        print(f"  阴谋 [{c.name}] 被触发！")
                        c.effect_fn(self, ev.data, p)
                        p.card_dis.append(c)
                    return trigger
                self.effect_queue.queue(f"阴谋 [{conspiracy.name}]", make_trigger())

        self.event_bus.register("*", listener, priority=50, owner_id=owner_id)
        return owner_id

    def unregister_conspiracy(self, conspiracy: "Conspiracy") -> None:
        """注销阴谋的事件监听器。"""
        owner_id = getattr(conspiracy, "_listener_owner_id", None)
        if owner_id:
            self.unregister_listeners_by_owner(owner_id)
            conspiracy._listener_owner_id = None

    _EVENT_ATTR_MAP = {
        EVENT_PHASE_START: "on_phase_start",
        EVENT_PHASE_END: "on_phase_end",
        EVENT_DRAW: "on_drawn",
    }

    # 某些事件只作用于 event_data 中明确的特定目标，而非遍历全部候选
    _EVENT_SPECIFIC_TARGET = {EVENT_DRAW}

    def _trigger_auto_effects(self, event_type: str, event_data: Dict[str, Any]):
        """触发场上异象、手牌、玩家的自动化时间节点效果。

        规则："回合开始/结束" 等价于 "结算阶段开始/结束"（PHASE_RESOLVE）。
        """
        attrs_to_trigger = []
        trigger_injected_start = False
        trigger_injected_end = False

        normal_attr = self._EVENT_ATTR_MAP.get(event_type)
        if normal_attr:
            attrs_to_trigger.append(normal_attr)

        # 结算阶段开始 = 回合开始
        if event_type == EVENT_PHASE_START and event_data.get("phase") == self.PHASE_RESOLVE:
            attrs_to_trigger.append("on_turn_start")
            trigger_injected_start = True
        # 结算阶段结束 = 回合结束
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
                    for inj_fn in list(getattr(m, "_injected_turn_start", [])):
                        self.effect_queue.queue(
                            f"{m.name} 的注入回合开始效果",
                            lambda m=m, inj_fn=inj_fn: inj_fn(m, m.owner, self),
                        )
                elif trigger_injected_end and attr_name == "on_turn_end":
                    for inj_fn in list(getattr(m, "_injected_turn_end", [])):
                        self.effect_queue.queue(
                            f"{m.name} 的注入回合结束效果",
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

    def refresh_all_auras(self):
        """刷新全场异象的临时光环（具有）效果。"""
        for m in list(self.board.minion_place.values()):
            if m.is_alive():
                m.recalculate()

    def transform_minion(self, old_minion: "Minion", new_card_def, preserve_summon_turn: bool = True) -> Optional["Minion"]:
        """通用异象变化/替换框架：将 old_minion 替换为 new_card_def 定义的新异象，位置不变。"""
        from .card_db import CardType
        if new_card_def.card_type != CardType.MINION:
            print(f"  错误：{new_card_def.name} 不是异象类型，无法替换")
            return None
        next_card = new_card_def.to_game_card(old_minion.owner)
        new_minion = Minion(
            name=next_card.name,
            owner=old_minion.owner,
            position=old_minion.position,
            attack=next_card.attack,
            health=next_card.health,
            source_card=next_card,
            board=self.board,
            keywords=next_card.keywords.copy(),
            on_turn_start=getattr(next_card, 'on_turn_start', None),
            on_turn_end=getattr(next_card, 'on_turn_end', None),
            on_phase_start=getattr(next_card, 'on_phase_start', None),
            on_phase_end=getattr(next_card, 'on_phase_end', None),
            statue_top=getattr(next_card, 'statue_top', False),
            statue_bottom=getattr(next_card, 'statue_bottom', False),
            statue_pair=getattr(next_card, 'statue_pair', None),
            on_statue_activate=getattr(next_card, 'on_statue_activate', None),
            on_statue_fuse=getattr(next_card, 'on_statue_fuse', None),
        )
        if preserve_summon_turn:
            new_minion.summon_turn = old_minion.summon_turn
        if self.board.replace_minion(old_minion.position, new_minion):
            on_evolve = getattr(next_card, 'on_evolve_fn', None)
            if on_evolve:
                on_evolve(new_minion, old_minion.owner, self)
            return new_minion
        return None

    def move_minion(self, minion: "Minion", new_pos: Any) -> bool:
        """安全移动异象到新的空格子。"""
        if not minion or not minion.is_alive():
            return False
        return self.board.move_minion(minion, new_pos)

    def swap_minions(self, m1: "Minion", m2: "Minion") -> bool:
        """安全交换两个异象的位置。"""
        if not m1 or not m2:
            return False
        return self.board.swap_minions(m1, m2)

    def _check_statue_pair(self, event_data: Dict[str, Any]):
        """在部署事件后检查是否形成了新的雕像对。"""
        minion = event_data.get("minion")
        if not minion or not getattr(minion, "is_alive", lambda: True)():
            return
        player = event_data.get("player")
        if not player:
            return

        is_top = getattr(minion, "statue_top", False)
        is_bottom = getattr(minion, "statue_bottom", False)
        if not (is_top or is_bottom):
            return

        # 寻找配对对象
        for m in self.board.get_minions_of_player(player):
            if m is minion:
                continue
            if not m.is_alive():
                continue
            if is_top and getattr(m, "statue_bottom", False):
                top, bottom = minion, m
            elif is_bottom and getattr(m, "statue_top", False):
                top, bottom = m, minion
            else:
                continue

            # 检查是否已在 pending 中
            already_pending = any(
                (pend["top"] is top and pend["bottom"] is bottom)
                for pend in self._pending_statues
            )
            if already_pending:
                continue

            matched = (getattr(top, "statue_pair", None) == getattr(bottom, "statue_pair", None))
            fuse_at = self.current_turn if matched else self.current_turn + 1
            self._pending_statues.append({
                "top": top,
                "bottom": bottom,
                "fuse_at_turn": fuse_at,
                "owner": player,
            })
            print(f"  雕像拼装开始：{top.name} + {bottom.name}，{'配对' if matched else '未配对'}，将于第 {fuse_at} 回合结束时生效")

    def _resolve_statue_fusions(self):
        """结算待处理的雕像融合（在结算阶段结束或回合结束时调用）。"""
        resolved = []
        for pend in self._pending_statues:
            top = pend["top"]
            bottom = pend["bottom"]
            if not (top.is_alive() and bottom.is_alive()):
                resolved.append(pend)
                continue
            if self.current_turn < pend["fuse_at_turn"]:
                continue

            # 执行融合
            print(f"  雕像 [{top.name} + {bottom.name}] 拼装完成！")
            activate_fn = getattr(top, "on_statue_activate", None)
            fuse_fn = getattr(bottom, "on_statue_fuse", None)
            if activate_fn:
                self.effect_queue.queue(
                    f"{top.name} 激活",
                    lambda t=top, fn=activate_fn: fn(self, t),
                )
            if fuse_fn:
                self.effect_queue.queue(
                    f"{bottom.name} 融合",
                    lambda b=bottom, t=top, fn=fuse_fn: fn(self, b, t),
                )
            # 移除组件（不触发亡语）
            self.effect_queue.queue(
                f"移除雕像组件",
                lambda t=top, b=bottom: (
                    self.board.remove_minion(t.position) if t.is_alive() else None,
                    self.board.remove_minion(b.position) if b.is_alive() else None,
                ),
            )
            resolved.append(pend)

        for pend in resolved:
            self._pending_statues.remove(pend)

    def start_game(self):
        import random
        print("=" * 40)
        print("Tards 对战开始！")
        print("=" * 40)
        self.first_player = self.p1
        for p in self.players:
            p.health = 30
            p.health_max = 30
            p.t_point_max = 0
            p.t_point = 0
            p.c_point = 0
            p.c_point_max = 0
            p.b_point = 0
            p.s_point = 0

            # 应用沉浸度开局增益
            discrete_pts = p.immersion_points.get(Pack.DISCRETE, 0)
            if discrete_pts >= 1:
                p.card_hand_max += 1
                print(f"  {p.name} 离散沉浸度 {discrete_pts}：手牌上限+1")
            if discrete_pts >= 2:
                p.c_point_max = 4
                print(f"  {p.name} 离散沉浸度 {discrete_pts}：C槽上限设为4")

            underworld_pts = p.immersion_points.get(Pack.UNDERWORLD, 0)
            if underworld_pts >= 1:
                squirrel_def = DEFAULT_REGISTRY.get("松鼠")
                if squirrel_def:
                    p.squirrel_deck = [squirrel_def.to_game_card(p) for _ in range(6)]
                    if p.squirrel_deck:
                        p.card_hand.append(p.squirrel_deck.pop())
                        print(f"  {p.name} 冥刻沉浸度 {underworld_pts}：获得松鼠牌堆(6张)及手牌中1张松鼠")

            blood_pts = p.immersion_points.get(Pack.BLOOD, 0)
            if blood_pts >= 3:
                moment_def = DEFAULT_REGISTRY.get("时刻")
                if moment_def:
                    moments = [moment_def.to_game_card(p) for _ in range(6)]
                    p.card_deck.extend(moments)
                    random.shuffle(p.card_deck)
                    print(f"  {p.name} 血契沉浸度 {blood_pts}：将6张时刻洗入卡组")

            p.draw_card(4, game=self)
        self.current_turn = 1
        while not self.game_over:
            self.run_turn()
            self.current_turn += 1
            if self.current_turn > 30:
                print("\n回合数达到上限，强制结束游戏。")
                break
        self.print_result()

    def run_turn(self):
        first = self.p1 if self.current_turn % 2 == 1 else self.p2
        second = self.p2 if first == self.p1 else self.p1
        print(f"\n========== 回合 {self.current_turn} | 先手: {first.name} ==========")
        self.emit_event(EVENT_TURN_START, turn=self.current_turn, first=first, second=second)
        self._process_delayed_effects("turn_start")
        if self.check_game_over():
            return
        self.draw_phase(first, second)
        if self.check_game_over():
            return
        self.action_phase(first, second)
        if self.check_game_over():
            return
        self.resolve_phase(first, second)
        self.check_game_over()
        if not self.game_over:
            self.emit_event(EVENT_TURN_END, turn=self.current_turn, first=first, second=second)
            self._process_delayed_effects("turn_end")
        # 批量清理状态追踪器中本回合的临时键（track_per_turn 等工具的兜底清理）
        if hasattr(self, "_state_tracker"):
            turn_suffix = f"_turn_{self.current_turn}"
            keys_to_remove = [k for k in self._state_tracker if k.endswith(turn_suffix)]
            for k in keys_to_remove:
                del self._state_tracker[k]
        self.clear_protections()
        from card_pools.effect_utils import clear_attack_restrictions
        clear_attack_restrictions(self)

    def draw_phase(self, first: Player, second: Player):
        self.current_phase = self.PHASE_DRAW
        self.current_player = first
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_DRAW, first=first, second=second)
        print("[抽牌阶段]")
        for p in [second, first]:
            if self.current_turn == 1 and p == first:
                continue  # 第一回合先手不抽牌
            if p._skip_next_draw:
                p._skip_next_draw = False
                print(f"  {p.name} 跳过抽牌")
            else:
                p.draw_card(1, game=self)

        for p in [first, second]:
            # 血契1级：抽牌阶段-1HP，+1S（流失生命值，不触发'受到伤害时'效果）
            blood_pts = p.immersion_points.get(Pack.BLOOD, 0)
            if blood_pts >= 1:
                p.lose_hp(1)
                p.s_point += 1
                print(f"  {p.name} 血契沉浸度触发：失去1HP，获得1S")

            # T槽自然增长
            discrete_pts = p.immersion_points.get(Pack.DISCRETE, 0)
            max_t = 8 if discrete_pts >= 2 else 10
            old_t_max = p.t_point_max
            if p.t_point_max < max_t:
                p.t_point_max += 1

            p.t_point = p.t_point_max
            print(f"  {p.name} T槽={p.t_point_max}，获得 {p.t_point} T点")

            # C点回满到上限（木镐等卡牌增加的额外C槽在回合开始时生效）
            p.c_point = p.c_point_max
            if p.c_point_max > 0:
                print(f"  {p.name} C槽={p.c_point_max}，获得 {p.c_point} C点")

            # 发射通用 T槽上限变化事件（信标、火把等卡牌通过监听此事件触发）
            if p.t_point_max > old_t_max:
                from .constants import EVENT_T_MAX_CHANGED
                self.emit_event(
                    EVENT_T_MAX_CHANGED,
                    player=p,
                    old=old_t_max,
                    new=p.t_point_max,
                )

            # 重置冥刻2级松鼠兑换标记
            p.squirrel_exchanged_this_turn = False

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_DRAW, first=first, second=second)

    def action_phase(self, first: Player, second: Player):
        self.current_phase = self.PHASE_ACTION
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_ACTION, first=first, second=second)
        print("[出牌阶段]")
        for p in self.players:
            p.reset_turn_flags()
            # 回合结束清空鲜血
            p.b_point = 0
            for m in self.board.get_minions_of_player(p):
                m.clear_temp_effects()

        active = first
        opponent = second
        turn_count = 0
        while not self.game_over:
            turn_count += 1
            if turn_count > 40:
                print("  出牌阶段回合数过多，强制结束")
                break

            # 双方都拉闸，出牌阶段结束
            if active.braked and opponent.braked:
                break

            # 当前玩家已拉闸，切换到对方
            if active.braked:
                active, opponent = opponent, active
                continue

            self.current_player = active
            print(f"\n  >>> {active.name} 的回合 (T点:{active.t_point}, HP:{active.health})")
            self.show_hand(active)
            active.bell = False

            if self.action_provider:
                action = self.action_provider(self, active, opponent)
            else:
                action = None

            if action is None:
                # 没有行动提供者或返回空，默认拉闸
                print(f"  {active.name} 没有可执行的行动，结束出牌阶段")
                active.braked = True
                active, opponent = opponent, active
                if active.braked:
                    break
                continue

            act_type = action.get("type")
            if act_type == "brake":
                active.braked = True
                print(f"  {active.name} 拉闸")
                active, opponent = opponent, active
                if active.braked:
                    print("  双方均已拉闸，出牌阶段结束")
                    break
                continue
            elif act_type == "bell":
                active.bell = True
                self.emit_event(EVENT_BELL, player=active)
                if not active.t_changed_this_round:
                    print(f"  {active.name} 未改变T点即拍铃，失去 1 T点")
                    active.t_point_change(-1)
                active, opponent = opponent, active
                continue
            elif act_type == "exchange":
                discrete_pts = active.immersion_points.get(Pack.DISCRETE, 0)
                if discrete_pts < 1:
                    print(f"  {active.name} 没有离散沉浸度，无法兑换矿物")
                else:
                    card_name = action.get("card_name")
                    card_def = DEFAULT_REGISTRY.get(card_name)
                    if not card_def or card_def.card_type != CardType.MINERAL:
                        print(f"  非法兑换请求，跳过")
                    else:
                        mineral_card = card_def.to_game_card(active)
                        print(f"  {active.name} 尝试兑换 {card_name}")
                        ok = active.exchange_mineral(mineral_card, self)
                        if not ok:
                            print(f"  兑换失败")
            elif act_type == "exchange_squirrel":
                underworld_pts = active.immersion_points.get(Pack.UNDERWORLD, 0)
                if underworld_pts < 2:
                    print(f"  {active.name} 冥刻沉浸度不足，无法兑换松鼠")
                elif active.squirrel_exchanged_this_turn:
                    print(f"  {active.name} 本回合已兑换过松鼠")
                elif not active.squirrel_deck:
                    print(f"  {active.name} 松鼠牌堆已空")
                elif active.t_point < 1:
                    print(f"  {active.name} T点不足，无法兑换松鼠")
                else:
                    active.t_point_change(-1)
                    card = active.squirrel_deck.pop()
                    if len(active.card_hand) < active.card_hand_max:
                        active.card_hand.append(card)
                        print(f"  {active.name} 消耗1T兑换了松鼠")
                    else:
                        active.card_dis.append(card)
                        print(f"  {active.name} 手牌已满，兑换的松鼠被弃置")
                    active.squirrel_exchanged_this_turn = True
            elif act_type == "play":
                serial = action.get("serial")
                target = action.get("target")
                bluff = action.get("bluff", False)
                sacrifices = action.get("sacrifices", [])
                extra_targets = action.get("extra_targets")
                # 过滤掉因不同步而丢失的牺牲目标（只剩 tuple 位置），以及献祭次数已耗尽的异象
                valid_sacs = [m for m in sacrifices if hasattr(m, "keywords") and getattr(m, "is_alive", lambda: True)() and getattr(m, '_sacrifice_remaining', 0) > 0]
                temp_b = 0
                if valid_sacs:
                    temp_b = sum(m.keywords.get("丰饶", 1) for m in valid_sacs)
                    active.b_point += temp_b
                old_chooser = active.sacrifice_chooser
                if valid_sacs:
                    active.sacrifice_chooser = lambda req, v=valid_sacs: v
                try:
                    can_play, reason = active.card_can_play(serial, target)
                    if can_play:
                        card = active.card_hand[serial - 1]
                        # 全局部署限制检查（仅随从卡）
                        if isinstance(card, MinionCard):
                            blocked = False
                            for restriction in self._global_deploy_restrictions:
                                if not restriction(active, card):
                                    print(f"  全局部署限制阻止了 {card.name} 的部署")
                                    blocked = True
                                    break
                            if blocked:
                                continue
                        print(f"  {active.name} 尝试打出 {card.name} (目标: {self._fmt_target(target)})")
                        ok = active.play_card(serial, target, self, bluff=bluff, extra_targets=extra_targets)
                        if not ok:
                            print(f"  出牌失败")
                    else:
                        print(f"  非法出牌请求：{reason}")
                finally:
                    active.sacrifice_chooser = old_chooser
            elif act_type == "set_vision":
                pos = action.get("pos")
                col = action.get("col")
                m = self.board.get_minion_at(pos)
                if m and m.owner == active:
                    if self.set_vision_target(m, col):
                        targets = action.get("targets")
                        if targets:
                            m._pending_attack_targets = targets
                            print(f"  {active.name} 设置 {m.name} 的视野目标列为 {col}，攻击目标 {len(targets)} 个")
                        else:
                            print(f"  {active.name} 设置 {m.name} 的视野目标列为 {col}")
                    else:
                        print(f"  非法的视野目标设置")
                else:
                    print(f"  非法的视野目标设置")
            elif act_type == "set_attack_targets":
                pos = action.get("pos")
                targets = action.get("targets", [])
                m = self.board.get_minion_at(pos)
                if m and m.owner == active:
                    m._pending_attack_targets = targets
                    print(f"  {active.name} 设置 {m.name} 的攻击目标")
                else:
                    print(f"  非法的攻击目标设置")
            else:
                print(f"  未知的行动类型: {act_type}")

            if self.check_game_over():
                break

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_ACTION, first=first, second=second)

    def request_choice(self, player: "Player", options: List[str], title: str = "抉择") -> Optional[str]:
        """请求玩家从多个选项中选择一个。无 provider 时随机选择。"""
        if not options:
            return None
        if len(options) == 1:
            return options[0]
        if self.choice_provider:
            result = self.choice_provider(self, player, options, title)
            return result if result in options else options[0]
        import random
        return random.choice(options)

    def show_hand(self, player: Player):
        if not player.card_hand:
            print(f"    手牌: (空)")
            return
        parts = []
        for i, c in enumerate(player.card_hand, 1):
            if isinstance(c, MinionCard):
                parts.append(f"[{i}]{c.name}({c.cost} {c.attack}/{c.health})")
            else:
                parts.append(f"[{i}]{c.name}({c.cost})")
        print(f"    手牌: {' | '.join(parts)}")
        # 活跃阴谋对对手隐藏，这里仅打印自己的
        if player.active_conspiracies:
            print(f"    活跃阴谋: {', '.join(c.name for c in player.active_conspiracies)}")

    def _fmt_target(self, target: Any) -> str:
        if isinstance(target, tuple):
            r, c = target
            col_name = Board.COL_NAMES[c] if 0 <= c < 5 else str(c)
            return f"({r},{col_name})"
        if isinstance(target, Minion):
            return target.name
        if isinstance(target, Player):
            return target.name
        return str(target)

    def resolve_phase(self, first: Player, second: Player):
        # 清空本回合状态追踪（"回合"等价于结算阶段）
        self._deployed_this_turn.clear()
        self._damage_dealt_to_players_this_turn.clear()
        self.p1._cards_played_this_phase = 0
        self.p2._cards_played_this_phase = 0

        self.current_phase = self.PHASE_RESOLVE
        self.current_player = first
        self.emit_event(EVENT_PHASE_START, phase=self.PHASE_RESOLVE, first=first, second=second)
        print("[结算阶段]")
        print(self.board)

        # 高频攻击次数状态：按 Minion 对象引用存储，支持结算阶段中途加入的异象
        attacker_swings: dict[Minion, int] = {}
        # 记录因高频而临时改变的先攻值，结算阶段结束后恢复
        original_first_strike: dict[Minion, int] = {}

        # 对战顺序：水路(4) -> 河岸(3) -> 中路(2) -> 山脊(1) -> 高地(0)
        for col in range(4, -1, -1):
            col_name = self.board.COL_NAMES[col]

            # 找出以本列为 base_col 的攻击者（横扫异象只在 base_col 发起攻击）
            attackers = []
            for m in self.board.minion_place.values():
                if m.position[1] != col:
                    continue
                if not m.can_attack_this_turn(self.current_turn):
                    continue
                from card_pools.effect_utils import can_minion_attack
                if not can_minion_attack(m, self):
                    continue
                if getattr(m, "_skip_resolve_attack", False):
                    continue

                if m not in attacker_swings:
                    swings = m.keywords.get("高频", 1)
                    if m.keywords.get("三重打击", False):
                        swings = 3
                    if swings is True:
                        swings = 1
                    elif not isinstance(swings, int) or swings <= 0:
                        swings = 1
                    attacker_swings[m] = swings

                if attacker_swings[m] > 0:
                    attackers.append(m)

            if not attackers:
                continue

            # 排序：先攻等级降序 -> 距离中线升序 -> side
            attackers.sort(key=lambda m: (
                -m.keywords.get("先攻", 0),
                abs(m.position[0] - 2),
                m.owner.side,
            ))

            print(f"  {col_name}列发生战斗")

            while True:
                # 动态刷新：找出仍存活且还有攻击次数的 base_col == col 的异象
                active = [m for m in self.board.minion_place.values()
                          if m.position[1] == col and m.is_alive()
                          and m.can_attack_this_turn(self.current_turn)
                          and attacker_swings.get(m, 0) > 0]
                from card_pools.effect_utils import can_minion_attack
                active = [m for m in active if can_minion_attack(m, self)]
                if not active:
                    break

                active.sort(key=lambda m: (
                    -m.keywords.get("先攻", 0),
                    abs(m.position[0] - 2),
                    m.owner.side,
                ))

                # 只取当前先攻最高的一批异象作为本轮攻击者
                highest_fs = active[0].keywords.get("先攻", 0)
                group = [m for m in active if m.keywords.get("先攻", 0) == highest_fs]

                def do_round():
                    for m in group:
                        # 同先攻组内不检查 _pending_death，保证同先攻异象都能出手
                        if not m.is_alive() or attacker_swings.get(m, 0) <= 0:
                            continue

                        # 防空：本列敌方异象失去串击/穿刺/穿透
                        has_enemy_anti_air = any(
                            enemy.keywords.get("防空", False)
                            for enemy in self.board.get_enemy_minions_in_column(base_col, m.owner)
                        )
                        can_pierce = not has_enemy_anti_air and (
                            m.keywords.get("串击", False) or m.keywords.get("穿刺", False) or m.keywords.get("穿透", False)
                        )

                        sweep = m.keywords.get("横扫", 0)
                        if not isinstance(sweep, int):
                            sweep = 0

                        # 视野：预设攻击目标列
                        attack_col = base_col
                        vision_range = m.keywords.get("视野", 0)
                        if vision_range > 0 and hasattr(m, "_resolve_target_col") and m._resolve_target_col is not None:
                            attack_col = m._resolve_target_col

                        if sweep > 0:
                            # 横扫：按对战顺序依次对所有覆盖列造成伤害
                            affected_cols = {base_col}
                            for offset in range(1, sweep + 1):
                                if base_col - offset >= 0:
                                    affected_cols.add(base_col - offset)
                                if base_col + offset < 5:
                                    affected_cols.add(base_col + offset)

                            hero_hit = False
                            for scol in sorted(affected_cols, reverse=True):
                                target = self.board.get_front_minion(scol, m.owner, attacker=m)
                                if target and target.is_alive():
                                    pass
                                else:
                                    target = self.p2 if m.owner == self.p1 else self.p1

                                is_sweep_col = (scol != base_col)
                                if is_sweep_col and isinstance(target, Player) and hero_hit:
                                    continue

                                if is_sweep_col:
                                    print(f"  {m.name} 横扫 {self.board.COL_NAMES[scol]}列")
                                    if isinstance(target, Minion):
                                        target.take_damage(m.attack)
                                        if target.is_alive():
                                            spike = target.keywords.get("尖刺", 0)
                                            if spike > 0:
                                                print(f"  {target.name} 的尖刺反弹 {spike} 点伤害")
                                                m.take_damage(spike)
                                    else:
                                        print(f"  {m.name} 横扫直接攻击 {target.name}，造成 {m.attack} 点伤害")
                                        target.health_change(-m.attack)
                                        hero_hit = True
                                else:
                                    # 本列正常攻击
                                    if target and target.is_alive():
                                        from card_pools.effect_utils import is_untargetable_by_minions
                                        if is_untargetable_by_minions(target):
                                            print(f"  {m.name} 攻击 {target.name}，但目标无法被异象选中，攻击落空")
                                            enemy = self.p2 if m.owner == self.p1 else self.p1
                                            m.attack_target(enemy)
                                        else:
                                            m.attack_target(target)
                                    else:
                                        enemy = self.p2 if m.owner == self.p1 else self.p1
                                        m.attack_target(enemy)
                        # 预设攻击目标（视野+高频等异象在行动阶段选择的直接目标）
                        pending = getattr(m, "_pending_attack_targets", None)
                        if pending and isinstance(pending, list) and len(pending) > 0:
                            # 按顺序消耗预设目标：第1次攻击取第0个，第2次取第1个...
                            total_swings = m.keywords.get("高频", 1)
                            if total_swings is True:
                                total_swings = 1
                            remaining = attacker_swings.get(m, total_swings)
                            target_idx = total_swings - remaining
                            if 0 <= target_idx < len(pending):
                                target = pending[target_idx]
                                # 结算阶段：潜水/潜行异象无法被选中，攻击落空
                                if hasattr(target, "keywords") and (target.keywords.get("潜水", False) or target.keywords.get("潜行", False)):
                                    print(f"  {m.name} 攻击 {target.name}，但目标处于潜水/潜行状态，攻击落空")
                                elif target and hasattr(target, "is_alive") and target.is_alive():
                                    m.attack_target(target)
                                elif hasattr(target, "health_change"):
                                    # 目标是玩家
                                    print(f"  {m.name} 直接攻击 {target.name}")
                                    target.health_change(-m.current_attack)
                                else:
                                    print(f"  {m.name} 的攻击目标已消失，攻击落空")
                            else:
                                # 预设目标耗尽，攻击英雄
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)
                        elif can_pierce:
                            # 串击/穿刺/穿透：攻击同列所有敌方异象
                            enemies = [e for e in self.board.get_enemy_minions_in_column(attack_col, m.owner) if e.is_alive()]
                            # 潜水/潜行始终不可见
                            enemies = [e for e in enemies if not e.keywords.get("潜水", False) and not e.keywords.get("潜行", False)]
                            if enemies:
                                print(f"  {m.name} 串击 {self.board.COL_NAMES[attack_col]}列所有敌方异象")
                                for enemy in enemies:
                                    m.attack_target(enemy)
                            else:
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)
                        else:
                            # 普通攻击（含视野偏移）
                            target = self.board.get_front_minion(attack_col, m.owner, attacker=m)
                            if target and target.is_alive():
                                m.attack_target(target)
                            else:
                                enemy = self.p2 if m.owner == self.p1 else self.p1
                                m.attack_target(enemy)

                        attacker_swings[m] -= 1
                        if self.resolve_step_callback:
                            self.resolve_step_callback()
                        if m.keywords.get("高频", 0) > 0:
                            if m not in original_first_strike:
                                original_first_strike[m] = m.keywords.get("先攻", 0)
                            current = m.keywords.get("先攻", 0)
                            if isinstance(current, int) and current > 0:
                                m.keywords["先攻"] = current - 1

                        if self.check_game_over():
                            return

                base_col = col
                self.effect_queue.resolve(f"{col_name}列发生战斗", do_round)

        # 结算阶段结束：恢复因高频临时降低的先攻等级
        for m, original in original_first_strike.items():
            if m.is_alive():
                m.keywords["先攻"] = original

        # 结算阶段结束：清理全场异象的临时效果，并递减状态层数
        for m in list(self.board.minion_place.values()):
            if not m.is_alive():
                continue
            m.temp_attack_bonus = 0
            m.temp_health_bonus = 0
            m.temp_max_health_bonus = 0
            m.temp_keywords.clear()
            # 清理行动阶段预设的攻击目标和视野列
            if hasattr(m, "_pending_attack_targets"):
                m._pending_attack_targets = None
            if hasattr(m, "_resolve_target_col"):
                m._resolve_target_col = None
            # 随时间削减层数的状态关键词（修改源头以确保 recalculate 不会还原）
            for kw in ["冰冻", "眩晕", "休眠"]:
                for source in (m.base_keywords, m.perm_keywords, m.temp_keywords):
                    val = source.get(kw)
                    if isinstance(val, int) and val > 0:
                        val -= 1
                        if val <= 0:
                            source.pop(kw, None)
                        else:
                            source[kw] = val
            m.recalculate()

        # 结算阶段结束：处理成长
        for m in list(self.board.minion_place.values()):
            if not m.is_alive():
                continue
            grow = m.keywords.get("成长")
            if isinstance(grow, int) and grow > 0:
                grow -= 1
                if grow <= 0:
                    m.keywords.pop("成长", None)
                    m.evolve(self)
                else:
                    m.keywords["成长"] = grow
            elif grow == 0:
                m.keywords.pop("成长", None)
                m.evolve(self)

        self.emit_event(EVENT_PHASE_END, phase=self.PHASE_RESOLVE, first=first, second=second)

    def is_immune(self, target: Any, source_player: Player, effect_type: str = "strategy") -> bool:
        """检查目标是否免疫某类效果（用于绝缘等机制）。"""
        if effect_type == "strategy" and isinstance(target, Minion):
            if target.keywords.get("绝缘", False) and target.owner != source_player:
                print(f"  {target.name} 绝缘，免疫策略效果")
                return True
        return False

    # ------------------------------------------------------------------
    # 轻量"取消"机制：伤害替换 & 指向保护
    # ------------------------------------------------------------------

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
        """清理所有持续保护效果（回合结束/开始时调用）。"""
        self._target_protections.clear()
        # 移除所有 once=False 的伤害替换（持续型）
        self._damage_replacements = [
            r for r in self._damage_replacements if r.get("once", True)
        ]

    def _process_delayed_effects(self, trigger: str):
        """处理延迟效果队列中匹配当前触发时机的回调。"""
        if not hasattr(self, "_delayed_effects"):
            return
        to_run = []
        remaining = []
        for entry in self._delayed_effects:
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

    def set_vision_target(self, minion: "Minion", col: int) -> bool:
        """为具有视野的异象预设攻击目标列（出牌阶段调用）。"""
        vision_range = minion.keywords.get("视野", 0)
        if vision_range <= 0:
            return False
        base_col = minion.position[1]
        if abs(col - base_col) > vision_range:
            return False
        if col < 0 or col >= self.board.SIZE:
            return False
        minion._resolve_target_col = col
        return True

    def check_game_over(self) -> bool:
        if self.game_over:
            return True
        p1_dead = self.p1.health <= 0
        p2_dead = self.p2.health <= 0
        if p1_dead and p2_dead:
            print("\n双方同时倒下，平局！")
            self.game_over = True
            return True
        elif p1_dead:
            print(f"\n{self.p2.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p2
            return True
        elif p2_dead:
            print(f"\n{self.p1.name} 获得胜利！")
            self.game_over = True
            self.winner = self.p1
            return True
        return False

    def develop_card(
        self,
        player: Player,
        pool_defs: List[Any],
        count: int = 3,
        modify_fn=None,
        overflow_to_discard: bool = True,
        return_card: bool = False,
    ):
        """开发机制：从 pool_defs 的副本中随机抽取 count 张不同候选，让玩家选择一张生成到手牌。

        若设置了 discover_provider，则将已生成的候选列表交给 provider 处理选择，
        以便网络对战时同步候选列表。

        规则：
        - 候选数量固定为 count 张（默认 3），不重复。
        - 开发不会减少源池中的牌数量（使用副本）。
        - 手牌满时按爆牌处理（移入弃牌堆），除非 overflow_to_discard=False（洗入卡组）。
        - 离散3级沉浸度：开发时 +1HP。

        Args:
            modify_fn: 可选回调，接收生成的 Card 对象，可在加入手牌前修改其属性。
            overflow_to_discard: 手牌满时的处理方式。True=弃置（默认），False=洗入卡组。
            return_card: 为 True 时返回生成的 Card 对象（失败返回 None）；默认返回 bool。
        """
        import random
        if not pool_defs:
            return None if return_card else False
        pool_copy = list(pool_defs)
        n = min(count, len(pool_copy))
        if n <= 0:
            return None if return_card else False
        candidates = random.sample(pool_copy, n)

        if self.discover_provider:
            result = self.discover_provider(self, player, candidates, count)
        else:
            # AI 默认策略：随机选一张
            result = random.choice(candidates)

        if result:
            card = result.to_game_card(player)
            if modify_fn:
                modify_fn(card)
            if len(player.card_hand) < player.card_hand_max:
                player.card_hand.append(card)
                print(f"  {player.name} 开发：获得 [{card.name}]")
            else:
                if overflow_to_discard:
                    player.card_dis.append(card)
                    print(f"  {player.name} 开发但手牌已满：{card.name} 被弃置")
                else:
                    player.card_deck.append(card)
                    random.shuffle(player.card_deck)
                    print(f"  {player.name} 开发但手牌已满：{card.name} 洗入卡组")

            # 离散3级：开发一张牌时，+1HP
            if player.immersion_points.get(Pack.DISCRETE, 0) >= 3:
                player.health_change(1)

            # 调用通用开发回调（由附魔台等卡牌通过 effect_fn 注册）
            for cb in list(player._on_develop_callbacks):
                try:
                    cb(player, self)
                except Exception as e:
                    print(f"  [开发回调错误] {e}")

            # 发射通用开发事件
            from .constants import EVENT_DEVELOPED
            self.emit_event(EVENT_DEVELOPED, player=player, card=card)

            return card if return_card else True

        return None if return_card else False

    def print_result(self):
        if self.winner:
            print(f"\n>>> 最终胜者: {self.winner.name} <<<")
        elif self.game_over:
            print("\n>>> 游戏结束：平局 <<<")
        else:
            print("\n>>> 游戏中断 <<<")
