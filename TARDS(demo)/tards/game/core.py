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

class CoreMixin:
    PHASE_START = "start"
    PHASE_DRAW = "draw"
    PHASE_ACTION = "action"
    PHASE_RESOLVE = "resolve"
    PHASE_END = "end"

    _EVENT_ATTR_MAP = {
        EVENT_PHASE_START: "on_phase_start",
        EVENT_PHASE_END: "on_phase_end",
        EVENT_DRAW: "on_drawn",
    }

    # 某些事件只作用于 event_data 中明确的特定目标，而非遍历全部候选
    _EVENT_SPECIFIC_TARGET = {EVENT_DRAW}

    def __init__(
        self,
        player1: Player,
        player2: Player,
        action_provider: Optional[Callable[["Game", Player, Player], Optional[Dict[str, Any]]]] = None,
        discover_provider: Optional[Callable[["Game", Player, List[Any], int], Optional[Any]]] = None,
        targeting_provider: Optional[Callable[["Game", TargetingRequest, List[Any]], Optional[Any]]] = None,
        mulligan_provider: Optional[Callable[["Game", List[Player]], None]] = None,
        logger: Optional[GameLogger] = None,
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
        self.targeting_provider = targeting_provider
        self.mulligan_provider = mulligan_provider
        self.choice_provider: Optional[Callable[["Game", "Player", List[str], str], Optional[str]]] = None
        self.logger = logger or GameLogger.create_for_battle()
        self.effect_queue = EffectQueue(self)
        self.event_bus = EventBus(self, logger=self.logger)
        self.targeting_system = TargetingSystem(self)
        self.resolve_step_callback = None
        self.resolve_column_delay = 0.0  # 结算阶段每列结算完后的停顿时间（秒）
        self._next_sync_id = 1
        self.sync_hash_callback = None

        # 机器日志（按回合索引的历史变量，供卡牌监听器查询）
        self.history = GameHistory(self)

        # 异象融合系统（雕像是第一类使用者）
        self.fusion_system = FusionSystem(self)
        self.fusion_graph = self.fusion_system.graph
        self._pending_fusions = self.fusion_system.pending
        self._pending_statues = self._pending_fusions

        # 部署光环/钩子（全局监听新异象部署）
        self.deploy_hooks: List[Callable[["Minion"], None]] = []

        # 延迟效果队列（下结算阶段开始时/结算阶段结束时触发）
        self._delayed_effects: List[Dict[str, Any]] = []

        # 全局部署限制（如疣猪"双方无法部署花费≤4T的异象"）
        self._global_deploy_restrictions: List[Callable[["Player", Any], bool]] = []

        # 伤害替换效果（用于"取消该伤害"等机制）
        self._damage_replacements: List[Dict[str, Any]] = []
        # 指向保护效果（用于"取消该指向"等机制）
        self._target_protections: List[Dict[str, Any]] = []

        # 结构化状态日志（机器可读，用于全局统计如失去T槽数、出牌数等）
        self._state_log: List[Dict[str, Any]] = []

        # 监听器生命周期管理器
        from ..core.lifecycle import ListenerLifetimeManager
        self.lifecycle = ListenerLifetimeManager(self)

        # 绑定引用
        self.board.game_ref = self
        for p in self.players:
            p.board_ref = self.board

    def allocate_sync_id(self) -> int:
        """分配一个全局唯一的异象同步ID。"""
        sid = self._next_sync_id
        self._next_sync_id += 1
        return sid

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
                p.extra_hand_max = 2
                print(f"  {p.name} 离散沉浸度 {discrete_pts}：获得2个矿物手牌上限")
            # 离散沉浸度2级：第5和第10回合抽牌阶段获得2C（取代1T），C槽上限4
            # 具体实现在抽牌阶段

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
                    from card_pools.effect_utils import clear_shown_in_deck
                    clear_shown_in_deck(p)
                    print(f"  {p.name} 血契沉浸度 {blood_pts}：将6张时刻洗入卡组")

            p.draw_card(4, game=self)

        # === 对局开始时效果（如血渍怀表置入卡组顶等）===
        game_start_cards = []
        for p in self.players:
            for card in p.card_deck:
                if getattr(card, "on_game_start", None):
                    game_start_cards.append((p, card))
        import random
        random.shuffle(game_start_cards)
        for player, card in game_start_cards:
            try:
                card.on_game_start(player, self, card)
            except Exception as e:
                print(f"  [对局开始时效果错误] {card.name}: {e}")

        # === 开局手牌调整（Mulligan）===
        if self.mulligan_provider:
            print("\n[开局手牌调整]")
            self.mulligan_provider(self, self.players)

        self.current_turn = 1
        while not self.game_over:
            self.run_turn()
            self.current_turn += 1
            if self.current_turn > 1000:
                print("\n回合数达到上限，强制结束游戏。")
                break
        self.print_result()

    def run_turn(self):
        first = self.p1 if self.current_turn % 2 == 1 else self.p2
        second = self.p2 if first == self.p1 else self.p1
        print(f"\n========== 回合 {self.current_turn} | 先手: {first.name} ==========")
        self.history.advance_turn(self.current_turn)
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
        if self.sync_hash_callback:
            self.sync_hash_callback(self.current_turn, self.compute_sync_hash())

