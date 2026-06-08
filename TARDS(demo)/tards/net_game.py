import queue
import random
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .board import Board
from .game import Game
from .net_protocol import (
    GameConnection,
    connect_to_host,
    deserialize_action,
    msg_action,
    msg_discover,
    msg_gameover,
    msg_hello,
    msg_start,
    msg_sync_hash,
    msg_targeting,
    start_host,
)
from .player import Player
from .card_db import DEFAULT_REGISTRY, Pack


class NetworkDuel:
    """网络对战控制器。

    负责 Host/Client 的握手、行动同步、以及为 Game 提供 action_provider。
    本地玩家和远端玩家各自维护一个 Game 实例，通过交换行动指令保持一致。
    """

    def __init__(
        self,
        local_player: Player,
        local_deck_list: list,
        is_host: bool,
        host_ip: Optional[str] = None,
        port: int = 9876,
    ):
        self.local_player = local_player
        self.local_deck_list = local_deck_list
        self.is_host = is_host
        self.host_ip = host_ip
        self.port = port
        self.resolve_step_callback = None

        self.conn: Optional[GameConnection] = None
        self.remote_name: Optional[str] = None
        self.remote_deck_list: Optional[list] = None
        self.remote_immersion_points: Dict[str, int] = {}
        self.first_player_name: Optional[str] = None
        self.seed: int = 0

        self.game: Optional[Game] = None
        self.local_turn_callback: Optional[Callable[[], None]] = None
        self.game_over_callback: Optional[Callable[[Optional[str]], None]] = None
        self.discover_request_callback: Optional[Callable[[list], None]] = None
        self.choice_request_callback: Optional[Callable[[list, str], None]] = None
        self.targeting_request_callback: Optional[Callable[[Any, list], None]] = None
        self.mulligan_request_callback: Optional[Callable[[Player], None]] = None

        # Mulligan 同步
        self._mulligan_result: Optional[List[int]] = None
        self._mulligan_event = threading.Event()

        # 本地玩家行动同步
        self._local_action: Optional[Dict[str, Any]] = None
        self._local_action_event = threading.Event()
        self._local_turn_event = threading.Event()

        # Discover 同步
        self._discover_names: Optional[list] = None
        self._discover_result: Optional[str] = None
        self._discover_event = threading.Event()

        # Choice 同步
        self._choice_options: Optional[list] = None
        self._choice_result: Optional[str] = None
        self._choice_event = threading.Event()
        self._choice_title: str = "抉择"

        # Targeting 同步
        self._targeting_request: Optional[Any] = None
        self._targeting_valid_targets: Optional[list] = None
        self._targeting_result: Optional[Any] = None
        self._targeting_event = threading.Event()

        # 同步校验
        self._sync_hashes: Dict[int, str] = {}
        self._sync_hash_thread: Optional[threading.Thread] = None

        # 消息暂存（解决非预期消息在当前回合被丢弃的问题）
        self._pending_messages: List[Dict[str, Any]] = []
        self._pending_lock = threading.Lock()

    # ========== 连接与握手 ==========
    def connect(self) -> bool:
        """建立连接。阻塞方法。"""
        if self.is_host:
            self.conn = start_host(self.port)
        else:
            if not self.host_ip:
                raise ValueError("Client 必须提供 host_ip")
            self.conn = connect_to_host(self.host_ip, self.port)

        # 发送 HELLO
        imm_dict = {p.value: pts for p, pts in self.local_player.immersion_points.items()}
        self.conn.send(msg_hello(self.local_player.name, self.local_deck_list, imm_dict))

        # 接收 HELLO
        hello = self._wait_for_msg("HELLO", timeout=30)
        if not hello:
            return False
        self.remote_name = hello["name"]
        self.remote_deck_list = hello.get("deck", [])
        raw_imm = hello.get("immersion_points", {})
        self.remote_immersion_points = {k: v for k, v in raw_imm.items()}

        if self.is_host:
            # Host 决定先手与随机种子
            self.first_player_name = self.local_player.name
            self.seed = random.randint(0, 2 ** 31)
            self.conn.send(msg_start(self.first_player_name, self.seed))
        else:
            # Client 等待 START
            start_msg = self._wait_for_msg("START", timeout=30)
            if not start_msg:
                return False
            self.first_player_name = start_msg["first_player_name"]
            self.seed = start_msg.get("seed", 0)

        return True

    def _wait_for_msg(self, msg_type: str, timeout: Optional[float] = 30) -> Optional[Dict[str, Any]]:
        """从消息队列中等待特定类型的消息。"""
        if not self.conn:
            return None
        deadline = time.time() + timeout if timeout else None
        while True:
            try:
                msg = self.conn.msg_queue.get(timeout=0.5)
                if msg.get("type") == msg_type:
                    return msg
                if msg.get("type") == "DISCONNECT":
                    return None
            except queue.Empty:
                pass
            if deadline and time.time() > deadline:
                return None

    # ========== 游戏运行 ==========
    def run_game(self, opponent: Player, action_provider: Optional[Callable] = None):
        """在后台线程中启动游戏。"""
        # 如果 Host 决定 Client 先手（未来可能扩展），需要调整 first/second
        # 目前简化：Host 固定 side=0 且先手
        if self.is_host:
            first = self.local_player
            second = opponent
        else:
            first = opponent
            second = self.local_player

        self.game = Game(
            first,
            second,
            action_provider=action_provider or self._make_action_provider(),
            discover_provider=self._make_discover_provider(),
            targeting_provider=self._make_targeting_provider(),
            mulligan_provider=self._make_mulligan_provider(),
        )
        self.game.choice_provider = self._make_choice_provider()
        self.game.resolve_step_callback = self.resolve_step_callback
        self.game.sync_hash_callback = self._on_sync_hash
        random.seed(self.seed)
        self._start_sync_hash_listener()

        # 重建双方卡组，确保随机种子生效后牌序一致
        # 关键：Host 和 Client 必须以**相同顺序**调用 _rebuild_deck，
        # 否则 random 状态会分叉，导致 develop_card 的候选列表不同步。
        def _rebuild_deck(player, names):
            cards = []
            for name in names:
                cd = DEFAULT_REGISTRY.get(name)
                if cd:
                    cards.append(cd.to_game_card(player))
            random.shuffle(cards)
            player.card_deck = cards

        # 统一顺序：总是先重建 Host 的卡组，再重建 Client 的卡组
        host_deck_list = self.local_deck_list if self.is_host else self.remote_deck_list
        client_deck_list = self.remote_deck_list if self.is_host else self.local_deck_list
        host_player = self.local_player if self.is_host else opponent
        client_player = opponent if self.is_host else self.local_player

        _rebuild_deck(host_player, host_deck_list)
        _rebuild_deck(client_player, client_deck_list)

        self.game.start_game()
        if self.game_over_callback and self.game.game_over:
            self.game_over_callback(self.game.winner.name if self.game.winner else None)

    def _start_sync_hash_listener(self):
        """启动后台线程监听对方的 SYNC_HASH 消息。"""
        def listener():
            while self.conn and self.conn._running and not getattr(self.game, "game_over", False):
                try:
                    msg = self.conn.msg_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                mtype = msg.get("type")
                if mtype == "SYNC_HASH":
                    turn = msg.get("turn", 0)
                    remote_hash = msg.get("hash", "")
                    local_hash = self._sync_hashes.get(turn)
                    if local_hash is not None and local_hash != remote_hash:
                        print(f"[DESYNC] 回合 {turn} 状态不一致！本地={local_hash} 远端={remote_hash}")
                    else:
                        print(f"[Sync] 回合 {turn} hash 一致 ({remote_hash})")
                elif mtype == "DISCONNECT":
                    break
                else:
                    # 将非 SYNC_HASH 消息暂存，避免被当前线程丢弃
                    # 导致 Discover/Choice/Mulligan 等 provider 收不到消息
                    with self._pending_lock:
                        self._pending_messages.append(msg)
        self._sync_hash_thread = threading.Thread(target=listener, daemon=True)
        self._sync_hash_thread.start()

    def _on_sync_hash(self, turn: int, hash_val: str):
        """Game 回合结束时调用：记录本地 hash 并发送给远端。"""
        self._sync_hashes[turn] = hash_val
        if self.conn:
            self.conn.send(msg_sync_hash(turn, hash_val))

    def _pop_pending(self, msg_type: str) -> Optional[Dict[str, Any]]:
        """从暂存消息队列中取出第一条匹配类型的消息。"""
        with self._pending_lock:
            for i, msg in enumerate(self._pending_messages):
                if msg.get("type") == msg_type:
                    return self._pending_messages.pop(i)
        return None

    def _make_action_provider(self):
        def provider(game, active, opponent):
            if active == self.local_player:
                # 通知 GUI
                if self.local_turn_callback:
                    self.local_turn_callback()
                # 阻塞等待本地玩家提交 action
                self._local_turn_event.set()
                self._local_action_event.wait()
                self._local_action_event.clear()
                self._local_turn_event.clear()
                action = self._local_action
                self._local_action = None
                if action and self.conn:
                    self.conn.send(msg_action(action))
                return action
            else:
                # 远端玩家：阻塞等待网络消息
                # 先检查暂存队列（后台线程可能已取走消息）
                pending_action = self._pop_pending("ACTION")
                if pending_action:
                    return deserialize_action(pending_action, game.board)
                while True:
                    try:
                        msg = self.conn.msg_queue.get(timeout=0.2)
                    except queue.Empty:
                        if self.game.game_over:
                            return {"type": "brake"}
                        continue

                    mtype = msg.get("type")
                    if mtype == "ACTION":
                        return deserialize_action(msg, game.board)
                    if mtype == "GAMEOVER":
                        game.game_over = True
                        return {"type": "brake"}
                    if mtype == "DISCONNECT":
                        print("[Net] 对手断开连接")
                        game.game_over = True
                        return {"type": "brake"}
                    # 暂存非预期消息，供其他 provider 后续读取
                    with self._pending_lock:
                        self._pending_messages.append(msg)
        return provider

    def _make_discover_provider(self):
        def provider(game, player, candidates, count):
            import random
            names = [getattr(d, "name", str(d)) for d in candidates]
            if player == self.local_player:
                self._discover_names = names
                self._discover_result = None
                self._discover_event.clear()
                if self.discover_request_callback:
                    self.discover_request_callback(names)
                self._discover_event.wait()
                chosen_name = self._discover_result if self._discover_result is not None else names[0]
                if self.conn:
                    self.conn.send(msg_discover(names, chosen_name))
                for d in candidates:
                    if getattr(d, "name", str(d)) == chosen_name:
                        return d
                return candidates[0] if candidates else None
            else:
                # 先检查暂存消息
                pending = self._pop_pending("DISCOVER")
                if pending:
                    chosen_name = pending["chosen"]
                    remote_names = pending.get("names", [])
                    remote_candidates = [DEFAULT_REGISTRY.get(n) for n in remote_names]
                    remote_candidates = [c for c in remote_candidates if c is not None]
                    search_pool = remote_candidates if remote_candidates else candidates
                    for d in search_pool:
                        if getattr(d, "name", str(d)) == chosen_name:
                            return d
                    return search_pool[0] if search_pool else None
                while True:
                    try:
                        msg = self.conn.msg_queue.get(timeout=0.2)
                    except queue.Empty:
                        if game.game_over:
                            return candidates[0] if candidates else None
                        continue
                    mtype = msg.get("type")
                    if mtype == "DISCOVER":
                        chosen_name = msg["chosen"]
                        remote_names = msg.get("names", [])
                        remote_candidates = [DEFAULT_REGISTRY.get(n) for n in remote_names]
                        remote_candidates = [c for c in remote_candidates if c is not None]
                        search_pool = remote_candidates if remote_candidates else candidates
                        for d in search_pool:
                            if getattr(d, "name", str(d)) == chosen_name:
                                return d
                        return search_pool[0] if search_pool else None
                    if mtype == "GAMEOVER":
                        game.game_over = True
                        return candidates[0] if candidates else None
                    if mtype == "DISCONNECT":
                        print("[Net] 对手断开连接")
                        game.game_over = True
                        return candidates[0] if candidates else None
                    with self._pending_lock:
                        self._pending_messages.append(msg)
        return provider

    def submit_local_discover(self, chosen: str):
        """GUI 调用：提交本地玩家的开发选择。"""
        self._discover_result = chosen
        self._discover_event.set()

    def _make_choice_provider(self):
        def provider(game, player, options, title):
            if player == self.local_player:
                self._choice_options = options
                self._choice_result = None
                self._choice_title = title
                self._choice_event.clear()
                if self.choice_request_callback:
                    self.choice_request_callback(options, title)
                self._choice_event.wait()
                chosen = self._choice_result if self._choice_result in options else options[0]
                if self.conn:
                    from .net_protocol import msg_choice
                    self.conn.send(msg_choice(options, chosen, title))
                return chosen
            else:
                pending = self._pop_pending("CHOICE")
                if pending:
                    chosen = pending["chosen"]
                    return chosen if chosen in options else options[0]
                while True:
                    try:
                        msg = self.conn.msg_queue.get(timeout=0.2)
                    except queue.Empty:
                        if game.game_over:
                            return options[0] if options else None
                        continue
                    mtype = msg.get("type")
                    if mtype == "CHOICE":
                        chosen = msg["chosen"]
                        return chosen if chosen in options else options[0]
                    if mtype == "GAMEOVER":
                        game.game_over = True
                        return options[0] if options else None
                    if mtype == "DISCONNECT":
                        print("[Net] 对手断开连接")
                        game.game_over = True
                        return options[0] if options else None
                    with self._pending_lock:
                        self._pending_messages.append(msg)
        return provider

    def submit_local_choice(self, chosen: str):
        """GUI 调用：提交本地玩家的抉择选择。"""
        self._choice_result = chosen
        self._choice_event.set()

    def _make_targeting_provider(self):
        def provider(game, request, valid_targets):
            if request.deciding_player == self.local_player:
                self._targeting_request = request
                self._targeting_valid_targets = valid_targets
                self._targeting_result = None
                self._targeting_event.clear()
                if self.targeting_request_callback:
                    self.targeting_request_callback(request, valid_targets)
                self._targeting_event.wait()
                result = self._targeting_result
                if self.conn:
                    from .net_protocol import _serialize_target
                    self.conn.send(msg_targeting(
                        getattr(request.source, "name", str(request.source)),
                        result,
                    ))
                return result
            else:
                pending = self._pop_pending("TARGETING")
                if pending:
                    return _deserialize_target(pending.get("target"), game.board)
                while True:
                    try:
                        msg = self.conn.msg_queue.get(timeout=0.2)
                    except queue.Empty:
                        if game.game_over:
                            return None
                        continue
                    mtype = msg.get("type")
                    if mtype == "TARGETING":
                        return _deserialize_target(msg.get("target"), game.board)
                    if mtype == "GAMEOVER":
                        game.game_over = True
                        return None
                    if mtype == "DISCONNECT":
                        print("[Net] 对手断开连接")
                        game.game_over = True
                        return None
                    with self._pending_lock:
                        self._pending_messages.append(msg)
        return provider

    def submit_local_targeting(self, target: Any):
        """GUI 调用：提交本地玩家的指向选择。"""
        self._targeting_result = target
        self._targeting_event.set()

    def submit_local_mulligan(self, indices: List[int]):
        """GUI 调用：提交本地玩家的开局手牌调整选择。"""
        self._mulligan_result = indices
        self._mulligan_event.set()

    def submit_local_action(self, action: Dict[str, Any]):
        """GUI 调用：提交本地玩家的行动。"""
        self._local_action = action
        self._local_action_event.set()

    def is_local_turn(self) -> bool:
        return self._local_turn_event.is_set()

    def _make_mulligan_provider(self):
        def provider(game, players):
            # 1. 本地玩家选择要替换的牌
            self._mulligan_result = None
            self._mulligan_event.clear()
            if self.mulligan_request_callback:
                self.mulligan_request_callback(self.local_player)
            self._mulligan_event.wait()
            local_indices = self._mulligan_result or []

            # 2. 发送本地结果给对方
            if self.conn:
                from .net_protocol import msg_mulligan
                self.conn.send(msg_mulligan(local_indices))

            # 3. 等待对方 mulligan 结果
            remote_indices = []
            pending = self._pop_pending("MULLIGAN")
            if pending:
                remote_indices = pending.get("indices", [])
            else:
                while True:
                    # 先检查暂存队列（后台线程可能已取走消息）
                    pending = self._pop_pending("MULLIGAN")
                    if pending:
                        remote_indices = pending.get("indices", [])
                        break
                    try:
                        msg = self.conn.msg_queue.get(timeout=0.2)
                    except queue.Empty:
                        if game.game_over:
                            break
                        continue
                    if msg.get("type") == "MULLIGAN":
                        remote_indices = msg.get("indices", [])
                        break
                    if msg.get("type") in ("GAMEOVER", "DISCONNECT"):
                        break
                    # 非目标消息暂存，供其他 provider 使用
                    with self._pending_lock:
                        self._pending_messages.append(msg)

            # 4. 按 players 列表顺序执行 mulligan（保证双方 random 状态一致）
            for player in players:
                if player == self.local_player:
                    indices = local_indices
                else:
                    indices = remote_indices
                cards = [player.card_hand[i] for i in indices
                         if 0 <= i < len(player.card_hand)]
                player.mulligan(cards, game=game)
        return provider

    # ========== 结束 ==========
    def notify_gameover(self, winner_name: str):
        """通知远端游戏结束。"""
        if self.conn:
            self.conn.send(msg_gameover(winner_name))

    def close(self):
        if self.conn:
            self.conn.close()
        self._local_action_event.set()
        self._discover_event.set()
        self._choice_event.set()
        self._mulligan_event.set()
        self._targeting_event.set()
