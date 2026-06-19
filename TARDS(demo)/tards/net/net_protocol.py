import json
import queue
import socket
import threading
import time
from typing import Any, Dict, Optional


HEARTBEAT_INTERVAL = 15.0
HEARTBEAT_TIMEOUT = 45.0


class DesyncError(Exception):
    """状态同步失败，无法安全继续对局。"""


class GameConnection:
    """基于 TCP + JSON 的游戏连接封装。

    新增特性：
    - 应用层心跳（PING/PONG），及时发现半开连接；
    - 连接状态锁，避免 send/recv/close 之间的竞态；
    - 断线时向消息队列放入 DISCONNECT。
    """

    def __init__(self, sock: socket.socket, addr: str):
        self.sock = sock
        self.addr = addr
        # 读取超时，让 _recv_loop 有机会检查 _running
        self.sock.settimeout(1.0)
        self.msg_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._send_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._running = True
        self._recv_thread: Optional[threading.Thread] = None
        self._last_recv_time = time.time()
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None

    def is_running(self) -> bool:
        with self._state_lock:
            return self._running

    def _stop(self) -> None:
        with self._state_lock:
            self._running = False
        self._heartbeat_stop.set()

    def start_listening(self):
        """启动后台接收线程与心跳线程。"""
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _recv_loop(self):
        """持续接收以换行符分隔的 JSON 消息，放入 msg_queue。"""
        buffer = b""
        while self.is_running():
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                self._last_recv_time = time.time()
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[Net] 消息解析失败: {e} | raw={line[:100]}")
                        continue
                    mtype = msg.get("type")
                    # 心跳消息不进入业务队列
                    if mtype == "PING":
                        self.send(msg_pong())
                        continue
                    if mtype == "PONG":
                        continue
                    self.msg_queue.put(msg)
            except socket.timeout:
                continue
            except OSError:
                break
        self._stop()
        self.msg_queue.put(msg_disconnect())

    def _heartbeat_loop(self):
        """定期发送 PING，并检测是否长时间未收到任何数据。"""
        while not self._heartbeat_stop.wait(timeout=HEARTBEAT_INTERVAL):
            if not self.is_running():
                break
            if time.time() - self._last_recv_time > HEARTBEAT_TIMEOUT:
                print(f"[Net] 心跳超时，关闭连接 {self.addr}")
                self.close()
                break
            self.send(msg_ping())

    def send(self, msg: Dict[str, Any]):
        """发送一条 JSON 消息。"""
        if not self.is_running():
            return
        data = json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n"
        with self._send_lock:
            try:
                self.sock.sendall(data)
            except OSError:
                self._stop()

    def close(self):
        self._stop()
        with self._send_lock:
            try:
                self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass


def start_host(port: int = 9876, shutdown_event: Optional[threading.Event] = None) -> GameConnection:
    """启动服务端并阻塞等待一个客户端连接。

    支持通过 shutdown_event 取消等待，避免程序在关闭房间时无限挂起。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))
        s.listen(1)
        print(f"[Host] 等待连接于 0.0.0.0:{port} ...")
        s.settimeout(1.0)
        while shutdown_event is None or not shutdown_event.is_set():
            try:
                conn, addr = s.accept()
                print(f"[Host] 客户端已连接: {addr}")
                return GameConnection(conn, str(addr))
            except socket.timeout:
                continue
        raise OSError("等待连接被取消")
    finally:
        s.close()


def connect_to_host(ip: str, port: int = 9876, timeout: float = 10.0) -> GameConnection:
    """作为客户端连接到服务端，带连接超时。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((ip, port))
    # 业务层使用 1 秒读取超时，让 _recv_loop 有机会检查 _running
    s.settimeout(1.0)
    print(f"[Client] 已连接到 {ip}:{port}")
    return GameConnection(s, f"{ip}:{port}")


# ========== 消息辅助构造 ==========
def msg_hello(name: str, deck_list: list, immersion_points: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    return {"type": "HELLO", "name": name, "deck": deck_list, "immersion_points": immersion_points or {}}


def msg_start(first_player_name: str, seed: int) -> Dict[str, Any]:
    return {"type": "START", "first_player_name": first_player_name, "seed": seed}


def msg_action(action: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "ACTION", "action": _serialize_action(action)}


def msg_gameover(winner_name: str) -> Dict[str, Any]:
    return {"type": "GAMEOVER", "winner": winner_name}


def msg_sync_hash(turn: int, hash_val: str) -> Dict[str, Any]:
    return {"type": "SYNC_HASH", "turn": turn, "hash": hash_val}


def msg_chat(text: str) -> Dict[str, Any]:
    return {"type": "CHAT", "text": text}


def msg_discover(names: list, chosen: str) -> Dict[str, Any]:
    return {"type": "DISCOVER", "names": names, "chosen": chosen}


def msg_choice(options: list, chosen: str, title: str = "抉择") -> Dict[str, Any]:
    return {"type": "CHOICE", "options": options, "chosen": chosen, "title": title}


def msg_targeting(source_name: str, target: Any) -> Dict[str, Any]:
    """指向结果消息。"""
    return {"type": "TARGETING", "source_name": source_name, "target": _serialize_target(target)}


def msg_mulligan(indices: list) -> Dict[str, Any]:
    """开局手牌调整结果消息。indices 为要替换的牌在手牌中的索引列表。"""
    return {"type": "MULLIGAN", "indices": indices}


def msg_state(state_type: str) -> Dict[str, Any]:
    """对手决策状态消息（开发/抉择/指向/换牌中），用于改善等待体验。"""
    return {"type": "STATE", "state": state_type}


def msg_disconnect() -> Dict[str, Any]:
    """断开连接通知消息。"""
    return {"type": "DISCONNECT"}


def msg_ping() -> Dict[str, Any]:
    return {"type": "PING"}


def msg_pong() -> Dict[str, Any]:
    return {"type": "PONG"}


# ========== Action 序列化/反序列化 ==========
def _serialize_action(action: Dict[str, Any]) -> Dict[str, Any]:
    """将本地 action 转换为可网络传输的 dict。"""
    out = {"type": action["type"]}
    atype = action["type"]
    if atype == "play":
        out["serial"] = action["serial"]
        out["bluff"] = action.get("bluff", False)
        target = action["target"]
        out["target"] = _serialize_target(target)
        sacrifices = action.get("sacrifices", [])
        out["sacrifices"] = [_serialize_target(m) for m in sacrifices]
        extra = action.get("extra_targets")
        if extra:
            out["extra_targets"] = [_serialize_target(t) for t in extra]
    elif atype == "set_attack_targets":
        out["pos"] = list(action["pos"])
        out["targets"] = [_serialize_target(t) for t in action.get("targets", [])]
    elif atype == "set_effect_target":
        out["pos"] = list(action["pos"])
        out["target"] = _serialize_target(action.get("target"))
    elif atype in ("exchange", "exchange_squirrel"):
        out["card_name"] = action.get("card_name", "")
    return out


def _serialize_target(target: Any) -> Any:
    # 数字目标（自然数）
    if isinstance(target, int):
        return {"numeric": target}
    if isinstance(target, tuple) and len(target) == 2:
        return {"pos": [target[0], target[1]]}
    # Minion 用 sync_id + 当前位置双重标识
    if hasattr(target, "position"):
        out = {"pos": [target.position[0], target.position[1]]}
        sid = getattr(target, "_sync_id", None)
        if sid is not None:
            out["sync_id"] = sid
        return out
    if hasattr(target, "side"):
        return {"player_side": target.side}
    return None


def _is_int_pair(value) -> bool:
    return isinstance(value, (list, tuple)) and len(value) == 2 and all(isinstance(x, int) for x in value)


def deserialize_action(msg: Dict[str, Any], board) -> Optional[Dict[str, Any]]:
    """将网络消息还原为本地 action，对字段做基础类型校验。"""
    if msg.get("type") != "ACTION":
        return None
    action = msg.get("action")
    if not isinstance(action, dict):
        return None
    atype = action.get("type")
    if not isinstance(atype, str):
        return None
    out: Dict[str, Any] = {"type": atype}
    if atype == "play":
        serial = action.get("serial")
        if not isinstance(serial, int):
            print(f"[Net] 非法 ACTION/play.serial: {serial!r}")
            return None
        out["serial"] = serial
        out["bluff"] = bool(action.get("bluff", False))
        out["target"] = _deserialize_target(action.get("target"), board)
        sacrifices = action.get("sacrifices")
        if not isinstance(sacrifices, list):
            print("[Net] 非法 ACTION/play.sacrifices: 不是列表")
            return None
        out["sacrifices"] = [_deserialize_target(s, board) for s in sacrifices]
        extra = action.get("extra_targets")
        if extra is not None:
            if not isinstance(extra, list):
                print("[Net] 非法 ACTION/play.extra_targets: 不是列表")
                return None
            out["extra_targets"] = [_deserialize_target(t, board) for t in extra]
    elif atype == "set_attack_targets":
        pos = action.get("pos")
        if not _is_int_pair(pos):
            print(f"[Net] 非法 ACTION/set_attack_targets.pos: {pos!r}")
            return None
        out["pos"] = tuple(pos)
        targets = action.get("targets", [])
        if not isinstance(targets, list):
            print("[Net] 非法 ACTION/set_attack_targets.targets: 不是列表")
            return None
        out["targets"] = [_deserialize_target(t, board) for t in targets]
    elif atype == "set_effect_target":
        pos = action.get("pos")
        if not _is_int_pair(pos):
            print(f"[Net] 非法 ACTION/set_effect_target.pos: {pos!r}")
            return None
        out["pos"] = tuple(pos)
        out["target"] = _deserialize_target(action.get("target"), board)
    elif atype in ("exchange", "exchange_squirrel"):
        card_name = action.get("card_name")
        if not isinstance(card_name, str):
            print(f"[Net] 非法 ACTION/{atype}.card_name: {card_name!r}")
            return None
        out["card_name"] = card_name
    elif atype in ("bell", "brake"):
        # 拍铃/拉闸没有额外字段
        pass
    else:
        print(f"[Net] 未知 ACTION 类型: {atype}")
        return None
    return out


def _deserialize_target(data: Any, board) -> Any:
    """将网络目标反序列化为本地对象，对字段做基础类型校验。"""
    if data is None:
        return None
    if isinstance(data, dict):
        if "numeric" in data:
            val = data["numeric"]
            if isinstance(val, int):
                return val
            print(f"[Net] 非法 target.numeric: {val!r}")
            return None
        if "pos" in data:
            pos_data = data["pos"]
            if not _is_int_pair(pos_data):
                print(f"[Net] 非法 target.pos: {pos_data!r}")
                return None
            r, c = pos_data
            pos = (r, c)
            sid = data.get("sync_id")
            if sid is not None:
                if not isinstance(sid, int):
                    print(f"[Net] 非法 target.sync_id: {sid!r}")
                    return None
                m = board.get_minion_by_sync_id(sid)
                if m and m.is_alive():
                    return m
                # sync_id 已失效 => 状态不同步，直接终止对局
                if board.game_ref:
                    board.game_ref.game_over = True
                raise DesyncError(
                    f"目标 sync_id={sid} 已失效（位置 {pos}），双方状态不同步"
                )
            # 没有 sync_id 的旧式消息才允许按位置回退
            m = board.get_minion_at(pos)
            return m if m else pos
        if "player_side" in data:
            side = data["player_side"]
            if not isinstance(side, int) or side not in (0, 1):
                print(f"[Net] 非法 target.player_side: {side!r}")
                return None
            if board.game_ref:
                return board.game_ref.p1 if side == 0 else board.game_ref.p2
    return data
