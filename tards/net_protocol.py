import json
import queue
import socket
import threading
from typing import Any, Dict, Optional


class GameConnection:
    """基于 TCP + JSON 的游戏连接封装。"""

    def __init__(self, sock: socket.socket, addr: str):
        self.sock = sock
        self.addr = addr
        self.msg_queue: queue.Queue[Dict[str, Any]] = queue.Queue()
        self._lock = threading.Lock()
        self._running = True
        self._recv_thread: Optional[threading.Thread] = None

    def start_listening(self):
        """启动后台接收线程。"""
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

    def _recv_loop(self):
        """持续接收以换行符分隔的 JSON 消息，放入 msg_queue。"""
        buffer = b""
        while self._running:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line.decode("utf-8"))
                        self.msg_queue.put(msg)
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[Net] 消息解析失败: {e} | raw={line[:100]}")
            except OSError:
                break
        self._running = False
        self.msg_queue.put({"type": "DISCONNECT"})

    def send(self, msg: Dict[str, Any]):
        """发送一条 JSON 消息。"""
        if not self._running:
            return
        data = json.dumps(msg, ensure_ascii=False).encode("utf-8") + b"\n"
        with self._lock:
            try:
                self.sock.sendall(data)
            except OSError:
                self._running = False

    def close(self):
        self._running = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


def start_host(port: int = 9876) -> GameConnection:
    """启动服务端并阻塞等待一个客户端连接。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(1)
    print(f"[Host] 等待连接于 0.0.0.0:{port} ...")
    conn, addr = s.accept()
    print(f"[Host] 客户端已连接: {addr}")
    s.close()
    gc = GameConnection(conn, str(addr))
    gc.start_listening()
    return gc


def connect_to_host(ip: str, port: int = 9876) -> GameConnection:
    """作为客户端连接到服务端。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    print(f"[Client] 已连接到 {ip}:{port}")
    gc = GameConnection(s, f"{ip}:{port}")
    gc.start_listening()
    return gc


# ========== 消息辅助构造 ==========
def msg_hello(name: str, deck_list: list, immersion_points: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    return {"type": "HELLO", "name": name, "deck": deck_list, "immersion_points": immersion_points or {}}


def msg_start(first_player_name: str, seed: int) -> Dict[str, Any]:
    return {"type": "START", "first_player_name": first_player_name, "seed": seed}


def msg_action(action: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "ACTION", "action": _serialize_action(action)}


def msg_gameover(winner_name: str) -> Dict[str, Any]:
    return {"type": "GAMEOVER", "winner": winner_name}


def msg_chat(text: str) -> Dict[str, Any]:
    return {"type": "CHAT", "text": text}


def msg_discover(names: list, chosen: str) -> Dict[str, Any]:
    return {"type": "DISCOVER", "names": names, "chosen": chosen}


def msg_choice(options: list, chosen: str, title: str = "抉择") -> Dict[str, Any]:
    return {"type": "CHOICE", "options": options, "chosen": chosen, "title": title}


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
    elif atype in ("exchange", "exchange_squirrel"):
        out["card_name"] = action.get("card_name", "")
    return out


def _serialize_target(target: Any) -> Any:
    if isinstance(target, tuple) and len(target) == 2:
        return {"pos": [target[0], target[1]]}
    # Minion 用其当前位置标识
    if hasattr(target, "position"):
        return {"pos": [target.position[0], target.position[1]]}
    if hasattr(target, "side"):
        return {"player_side": target.side}
    return None


def deserialize_action(msg: Dict[str, Any], board) -> Optional[Dict[str, Any]]:
    """将网络消息还原为本地 action。"""
    if msg.get("type") != "ACTION":
        return None
    action = msg["action"]
    atype = action["type"]
    out = {"type": atype}
    if atype == "play":
        out["serial"] = action["serial"]
        out["bluff"] = action.get("bluff", False)
        out["target"] = _deserialize_target(action.get("target"), board)
        sacrifices = action.get("sacrifices", [])
        out["sacrifices"] = [_deserialize_target(s, board) for s in sacrifices]
        extra = action.get("extra_targets")
        if extra:
            out["extra_targets"] = [_deserialize_target(t, board) for t in extra]
    elif atype == "set_attack_targets":
        out["pos"] = tuple(action["pos"])
        out["targets"] = [_deserialize_target(t, board) for t in action.get("targets", [])]
    elif atype in ("exchange", "exchange_squirrel"):
        out["card_name"] = action.get("card_name", "")
    return out


def _deserialize_target(data: Any, board) -> Any:
    if data is None:
        return None
    if isinstance(data, dict):
        if "pos" in data:
            r, c = data["pos"]
            pos = (r, c)
            # 如果该位置有异象，返回异象；否则返回位置
            m = board.get_minion_at(pos)
            return m if m else pos
        if "player_side" in data:
            side = data["player_side"]
            if board.game_ref:
                return board.game_ref.p1 if side == 0 else board.game_ref.p2
    return data
