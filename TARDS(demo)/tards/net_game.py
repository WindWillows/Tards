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
    msg_disconnect,
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
    支持 pyngrok 内网穿透，实现跨网络联机。
    """

    def __init__(
        self,
        local_player: Player,
        local_deck_list: list,
        is_host: bool,
        host_ip: Optional[str] = None,
        port: int = 9876,
        use_ngrok: bool = False,
        ngrok_token: Optional[str] = None,
    ):
        self.local_player = local_player
        self.local_deck_list = local_deck_list
        self.is_host = is_host
        self.host_ip = host_ip
        self.port = port
        self.use_ngrok = use_ngrok
        self.ngrok_token = ngrok_token
        self.resolve_step_callback = None
        self._ngrok_tunnel = None

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

    # ========== ngrok 内网穿透 ==========
    def _start_ngrok_tunnel(self) -> Optional[str]:
        """启动 ngrok TCP 隧道，返回公网地址（如 tcp://0.tcp.ngrok.io:12345）。"""
        try:
            from pyngrok import ngrok
        except ImportError:
            print("[Net] pyngrok 未安装，无法使用内网穿透。请运行: pip install pyngrok")
            return None
        try:
            if self.ngrok_token:
                ngrok.set_auth_token(self.ngrok_token)
            tunnel = ngrok.connect(self.port, "tcp")
            self._ngrok_tunnel = tunnel
            print(f"[Net] ngrok 隧道已启动: {tunnel.public_url}")
            return tunnel.public_url
        except Exception as e:
            print(f"[Net] 启动 ngrok 隧道失败: {e}")
            return None

    def _stop_ngrok_tunnel(self) -> None:
        """关闭 ngrok 隧道。"""
        if self._ngrok_tunnel:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(self._ngrok_tunnel.public_url)
                print("[Net] ngrok 隧道已关闭")
            except Exception as e:
                print(f"[Net] 关闭 ngrok 隧道时出错: {e}")
            self._ngrok_tunnel = None

    def get_ngrok_url(self) -> Optional[str]:
        """获取当前 ngrok 公网地址。"""
        if self._ngrok_tunnel:
            return self._ngrok_tunnel.public_url
        return None

    # ========== 连接与握手 ==========
    def connect(self) -> bool:
        """建立连接。阻塞方法。"""
        if self.is_host:
            if self.use_ngrok:
                url = self._start_ngrok_tunnel()
                if not url:
                    return False
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
                    # 连接已断开但队列为空：将 DISCONNECT 放入 pending，供 provider 处理
                    if self.conn and not self.conn._running:
                        with self._pending_lock:
                            self._pending_messages.append(msg_disconnect())
                        if self.game:
                            self.game.game_over = True
                        break
                    continue
                mtype = msg.get("type")
                if mtype == "SYNC_HASH":
                    self._handle_sync_hash_msg(msg)
                elif mtype == "DISCONNECT":
                    if self.game:
                        self.game.game_over = True
                    # 把 DISCONNECT 也放入 pending，确保 provider 能收到
                    with self._pending_lock:
                        self._pending_messages.append(msg)
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

    def _handle_sync_hash_msg(self, msg: Dict[str, Any]):
        """处理收到的 SYNC_HASH 消息（可被任意接收线程调用）。"""
        turn = msg.get("turn", 0)
        remote_hash = msg.get("hash", "")
        local_hash = self._sync_hashes.get(turn)
        if local_hash is not None and local_hash != remote_hash:
            print(f"[DESYNC] 回合 {turn} 状态不一致！本地={local_hash} 远端={remote_hash}")
        else:
            print(f"[Sync] 回合 {turn} hash 一致 ({remote_hash})")

    def _pop_pending(self, msg_type: str) -> Optional[Dict[str, Any]]:
        """从暂存消息队列中取出第一条匹配类型的消息。"""
        with self._pending_lock:
            for i, msg in enumerate(self._pending_messages):
                if msg.get("type") == msg_type:
                    return self._pending_messages.pop(i)
        return None

    def _recv_or_pending(self, msg_type: str, timeout: float = 0.2) -> Optional[Dict[str, Any]]:
        """接收指定类型的网络消息，同时维护 pending 队列。

        行为：
        1. 先检查 pending 队列；
        2. 再从 msg_queue 取消息；
        3. 若为目标类型（或 GAMEOVER/DISCONNECT）直接返回；
        4. 若是 SYNC_HASH，当场处理并继续等待；
        5. 连接断开时返回 DISCONNECT；
        6. 其他消息暂存到 pending 队列并返回 None。

        返回 None 表示本次未收到目标消息，调用方应继续循环。
        """
        if not self.conn:
            return None

        pending = self._pop_pending(msg_type)
        if pending:
            return pending

        # 连接已断开：直接返回 DISCONNECT，避免无限轮询
        if not self.conn._running:
            if self.game:
                self.game.game_over = True
            return msg_disconnect()

        try:
            msg = self.conn.msg_queue.get(timeout=timeout)
        except queue.Empty:
            # 超时后再检查一次连接状态
            if self.conn and not self.conn._running:
                if self.game:
                    self.game.game_over = True
                return msg_disconnect()
            return None

        mtype = msg.get("type")
        if mtype == msg_type:
            return msg
        if mtype == "SYNC_HASH":
            self._handle_sync_hash_msg(msg)
            return None
        if mtype in ("GAMEOVER", "DISCONNECT"):
            return msg

        with self._pending_lock:
            self._pending_messages.append(msg)
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
                # 远端玩家：统一使用 _recv_or_pending，避免与 SYNC_HASH 线程竞争
                while True:
                    msg = self._recv_or_pending("ACTION")
                    if msg:
                        mtype = msg.get("type")
                        if mtype == "ACTION":
                            return deserialize_action(msg, game.board)
                        if mtype == "DISCONNECT":
                            print("[Net] 对手断开连接")
                        if mtype in ("GAMEOVER", "DISCONNECT"):
                            game.game_over = True
                            return {"type": "brake"}
                    if self.game.game_over:
                        return {"type": "brake"}
        return provider

    def _make_discover_provider(self):
        def _resolve_discover(msg, candidates):
            chosen_name = msg["chosen"]
            remote_names = msg.get("names", [])
            remote_candidates = [DEFAULT_REGISTRY.get(n) for n in remote_names]
            remote_candidates = [c for c in remote_candidates if c is not None]
            search_pool = remote_candidates if remote_candidates else candidates
            for d in search_pool:
                if getattr(d, "name", str(d)) == chosen_name:
                    return d
            return search_pool[0] if search_pool else None

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
                while True:
                    msg = self._recv_or_pending("DISCOVER")
                    if msg:
                        mtype = msg.get("type")
                        if mtype == "DISCOVER":
                            return _resolve_discover(msg, candidates)
                        if mtype == "DISCONNECT":
                            print("[Net] 对手断开连接")
                        if mtype in ("GAMEOVER", "DISCONNECT"):
                            game.game_over = True
                            return candidates[0] if candidates else None
                    if game.game_over:
                        return candidates[0] if candidates else None
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
                while True:
                    msg = self._recv_or_pending("CHOICE")
                    if msg:
                        mtype = msg.get("type")
                        if mtype == "CHOICE":
                            chosen = msg["chosen"]
                            return chosen if chosen in options else options[0]
                        if mtype == "DISCONNECT":
                            print("[Net] 对手断开连接")
                        if mtype in ("GAMEOVER", "DISCONNECT"):
                            game.game_over = True
                            return options[0] if options else None
                    if game.game_over:
                        return options[0] if options else None
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
                while True:
                    msg = self._recv_or_pending("TARGETING")
                    if msg:
                        mtype = msg.get("type")
                        if mtype == "TARGETING":
                            return _deserialize_target(msg.get("target"), game.board)
                        if mtype == "DISCONNECT":
                            print("[Net] 对手断开连接")
                        if mtype in ("GAMEOVER", "DISCONNECT"):
                            game.game_over = True
                            return None
                    if game.game_over:
                        return None
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

            # 3. 等待对方 mulligan 结果（统一走 _recv_or_pending 避免竞争）
            remote_indices = []
            while True:
                msg = self._recv_or_pending("MULLIGAN")
                if msg:
                    mtype = msg.get("type")
                    if mtype == "MULLIGAN":
                        remote_indices = msg.get("indices", [])
                        break
                    if mtype in ("GAMEOVER", "DISCONNECT"):
                        break
                if game.game_over:
                    break

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
            # 先发送 DISCONNECT 通知对方，再关闭连接
            try:
                self.conn.send(msg_disconnect())
            except Exception:
                pass
            self.conn.close()
        if self.game:
            self.game.game_over = True
        self._local_action_event.set()
        # 关闭 ngrok 隧道
        self._stop_ngrok_tunnel()
        self._discover_event.set()
        self._choice_event.set()
        self._mulligan_event.set()
        self._targeting_event.set()
