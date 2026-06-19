"""网络协议与联机基础测试。"""

from __future__ import annotations

import socket
import threading
import time
from typing import Optional, Tuple

# 副作用：注册所有卡包，确保 DEFAULT_REGISTRY 已填充
import card_pools.blood
import card_pools.discrete
import card_pools.general
import card_pools.underworld

from tards.data.card_db import DEFAULT_REGISTRY
from tards.cards import Minion
from tards.data.deck_io import list_saved_decks, load_deck
from tards.net.net_game import NetworkDuel
from tards.net.net_protocol import (
    DesyncError,
    GameConnection,
    _deserialize_target,
    _serialize_target,
    deserialize_action,
    msg_action,
    msg_chat,
    msg_disconnect,
)
from tards.core.player import Player


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _loopback_connection(timeout: float = 5.0) -> Tuple[GameConnection, GameConnection]:
    """创建一对已连接的 GameConnection（loopback）。"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    host_conn: list[Optional[GameConnection]] = [None]

    def accept() -> None:
        conn, _ = server.accept()
        host_conn[0] = GameConnection(conn, "host")
        host_conn[0].start_listening()

    t = threading.Thread(target=accept, daemon=True)
    t.start()

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.connect(("127.0.0.1", port))
    client_gc = GameConnection(client_sock, "client")
    client_gc.start_listening()

    t.join(timeout=timeout)
    server.close()
    assert host_conn[0] is not None, "loopback 连接建立失败"
    return host_conn[0], client_gc


class _FakeMinion:
    def __init__(self, position: Tuple[int, int], sync_id: int):
        self.position = position
        self._sync_id = sync_id

    def is_alive(self) -> bool:
        return True


class _FakeBoard:
    def __init__(self, minions=None, dead_sync_ids=None):
        self._minions = {m._sync_id: m for m in (minions or [])}
        self._dead_sync_ids = set(dead_sync_ids or [])
        self.game_ref = None

    def get_minion_by_sync_id(self, sid: int):
        return self._minions.get(sid)

    def get_minion_at(self, pos: Tuple[int, int]):
        for m in self._minions.values():
            if m.position == pos:
                return m
        return None


class _FakePlayer:
    side = 0


# ---------------------------------------------------------------------------
# 测试
# ---------------------------------------------------------------------------
def test_connection_roundtrip() -> None:
    host, client = _loopback_connection()
    host.send(msg_chat("hello"))

    deadline = time.time() + 3.0
    msg = None
    while time.time() < deadline:
        try:
            msg = client.msg_queue.get(timeout=0.2)
            break
        except Exception:
            continue

    assert msg is not None, "未收到对端消息"
    assert msg.get("type") == "CHAT"
    assert msg.get("text") == "hello"

    host.close()
    client.close()


def test_disconnect_detection() -> None:
    host, client = _loopback_connection()
    host.close()

    deadline = time.time() + 3.0
    msg = None
    while time.time() < deadline:
        try:
            msg = client.msg_queue.get(timeout=0.2)
            if msg.get("type") == "DISCONNECT":
                break
        except Exception:
            continue

    assert msg is not None and msg.get("type") == "DISCONNECT", "断开后未收到 DISCONNECT"
    assert not client.is_running()


def test_heartbeat_keeps_connection_alive() -> None:
    host, client = _loopback_connection()
    # 等待一个心跳周期，确保连接未被误关闭
    time.sleep(1.0)
    assert host.is_running()
    assert client.is_running()
    host.close()
    client.close()


def test_ping_not_queued() -> None:
    host, client = _loopback_connection()
    # 直接发送 PING，内部会回复 PONG，但不应进入业务队列
    host.send({"type": "PING"})
    time.sleep(0.5)
    assert client.msg_queue.empty()
    host.close()
    client.close()


def test_serialize_deserialize_minion() -> None:
    m = _FakeMinion((2, 3), 42)
    data = _serialize_target(m)
    assert data == {"pos": [2, 3], "sync_id": 42}

    board = _FakeBoard([m])
    restored = _deserialize_target(data, board)
    assert restored is m


def test_deserialize_dead_sync_id_raises() -> None:
    m = _FakeMinion((2, 3), 42)
    board = _FakeBoard([], dead_sync_ids=[42])
    try:
        _deserialize_target({"pos": [2, 3], "sync_id": 42}, board)
    except DesyncError:
        return
    raise AssertionError("预期 DesyncError 未被抛出")


def test_deserialize_missing_sync_id_fallback_to_position() -> None:
    m = _FakeMinion((2, 3), 42)
    board = _FakeBoard([m])
    # 无 sync_id 时按位置回退
    restored = _deserialize_target({"pos": [2, 3]}, board)
    assert restored is m


def test_deserialize_player_target() -> None:
    board = _FakeBoard()
    board.game_ref = type("G", (), {"p1": _FakePlayer(), "p2": _FakePlayer()})()
    board.game_ref.p2.side = 1
    restored = _deserialize_target({"player_side": 1}, board)
    assert restored is board.game_ref.p2


def test_action_roundtrip() -> None:
    m = _FakeMinion((1, 1), 7)
    board = _FakeBoard([m])
    action = {
        "type": "play",
        "serial": 3,
        "bluff": False,
        "target": m,
        "sacrifices": [m],
    }
    msg = msg_action(action)
    restored = deserialize_action(msg, board)
    assert restored is not None
    assert restored["type"] == "play"
    assert restored["serial"] == 3
    assert restored["target"] is m
    assert restored["sacrifices"] == [m]


def test_bell_brake_action_roundtrip() -> None:
    """拍铃/拉闸的 ACTION 消息应能正确序列化与反序列化。"""
    board = _FakeBoard([])
    for atype in ("bell", "brake"):
        msg = msg_action({"type": atype})
        restored = deserialize_action(msg, board)
        assert restored is not None, f"{atype} 反序列化不应返回 None"
        assert restored["type"] == atype


def test_validate_deck_list_valid() -> None:
    names = list_saved_decks()
    assert names, "没有可用卡组做校验测试"
    deck = load_deck(names[0], DEFAULT_REGISTRY)
    deck_list = []
    for name, count in deck.card_entries.items():
        deck_list.extend([name] * count)

    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    # 联机校验使用包名（Pack.value）作为沉浸点键
    imm = {p.value: pts for p, pts in deck.immersion_points.items()}
    err = duel._validate_deck_list(deck_list, imm)
    assert err is None, f"合法卡组不应报错: {err}"


def test_validate_deck_list_invalid() -> None:
    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    err = duel._validate_deck_list(["不存在的卡牌"], {})
    assert err is not None, "未知卡牌应被判为非法"


def test_validate_deck_list_wrong_size() -> None:
    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    err = duel._validate_deck_list(["火把"] * 5, {})
    assert err is not None, "牌数不足应被判为非法"


def test_submit_local_action_queues_target_actions() -> None:
    """目标设置类 action 可以批量入队，按顺序取出。"""
    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    duel.submit_local_action({"type": "set_attack_targets", "pos": (4, 0), "targets": []})
    duel.submit_local_action({"type": "set_effect_target", "pos": (4, 1), "target": (3, 1)})
    duel.submit_local_action({"type": "set_attack_targets", "pos": (4, 2), "targets": []})

    assert duel._local_action_queue.qsize() == 3
    assert duel._local_action_event.is_set()

    assert duel._local_action_queue.get()["pos"] == (4, 0)
    assert duel._local_action_queue.get()["target"] == (3, 1)
    assert duel._local_action_queue.get()["pos"] == (4, 2)


def test_submit_local_action_replaces_stale_primary_actions() -> None:
    """高频输入时，新主行动应替换旧主行动；目标设置类行动保留。"""
    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    duel.submit_local_action({"type": "bell"})
    duel.submit_local_action({"type": "brake"})
    duel.submit_local_action({"type": "play", "serial": 1})
    duel.submit_local_action({"type": "play", "serial": 2})
    duel.submit_local_action({"type": "set_attack_targets", "pos": (4, 0), "targets": []})
    duel.submit_local_action({"type": "set_attack_targets", "pos": (4, 1), "targets": []})
    duel.submit_local_action({"type": "exchange", "card_name": "青金石"})

    # 目标设置保留 2 个，主行动只保留最新的 1 个
    actions = []
    while not duel._local_action_queue.empty():
        actions.append(duel._local_action_queue.get())

    target_actions = [a for a in actions if a["type"] == "set_attack_targets"]
    primary_actions = [a for a in actions if a["type"] != "set_attack_targets"]

    assert len(target_actions) == 2
    assert len(primary_actions) == 1
    assert primary_actions[0]["type"] == "exchange"
    assert primary_actions[0]["card_name"] == "青金石"


def test_close_does_not_renotify_disconnect() -> None:
    """本地主动 close() 后，disconnect_callback 不应被再次触发。"""
    duel = NetworkDuel(
        Player(0, "p", "Net", []),
        [],
        is_host=True,
    )
    calls = []
    duel.disconnect_callback = lambda: calls.append(1)

    duel.close()
    assert duel._disconnect_notified is True

    # 模拟 _recv_loop 再次尝试通知（已被去重）
    duel._notify_disconnect()
    duel._notify_disconnect()
    assert len(calls) == 0, "本地主动关闭后不应再触发 disconnect_callback"
