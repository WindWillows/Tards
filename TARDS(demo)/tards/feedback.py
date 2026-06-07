"""反馈功能模块。

支持：
- 组装反馈数据（自动读取最新日志）
- 通过TCP发送反馈到指定服务器
- 发送失败时本地备份
"""

import json
import os
import socket
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional


FEEDBACK_DIR = "feedback"
FEEDBACK_LOCAL_BACKUP_DIR = "feedback_local"
FEEDBACK_CONFIG_FILE = "feedback_config.json"


@dataclass
class FeedbackEntry:
    """反馈条目。"""
    timestamp: str
    player_name: str
    description: str
    log_file: Optional[str]
    log_content: Optional[str]


def ensure_dir(path: str) -> None:
    """确保目录存在。"""
    os.makedirs(path, exist_ok=True)


def get_latest_log_file() -> Optional[str]:
    """查找 logs/ 目录下最新的 .log 文件。"""
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        return None
    files = [f for f in os.listdir(logs_dir) if f.endswith(".log")]
    if not files:
        return None
    # 按文件名排序（battle_YYYYMMDD_HHMMSS.log 格式）
    files.sort(reverse=True)
    return os.path.join(logs_dir, files[0])


def read_log_content(path: str, max_lines: int = 500) -> str:
    """读取日志文件尾部指定行数。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return "".join(lines)
    except Exception:
        return ""


def create_feedback(player_name: str, description: str) -> FeedbackEntry:
    """创建一条反馈条目（自动读取最新日志）。"""
    log_file = get_latest_log_file()
    log_content = read_log_content(log_file) if log_file else ""
    return FeedbackEntry(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        player_name=player_name,
        description=description,
        log_file=log_file,
        log_content=log_content,
    )


def save_feedback_local(entry: FeedbackEntry, suffix: str = "") -> str:
    """将反馈保存到本地备份目录，返回保存路径。"""
    ensure_dir(FEEDBACK_LOCAL_BACKUP_DIR)
    ts = entry.timestamp.replace(":", "-").replace(" ", "_")
    fname = f"feedback_{entry.player_name}_{ts}{suffix}.json"
    path = os.path.join(FEEDBACK_LOCAL_BACKUP_DIR, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(entry), f, ensure_ascii=False, indent=2)
    return path


def send_feedback(entry: FeedbackEntry, host: str, port: int, timeout: float = 5.0) -> bool:
    """通过TCP发送反馈到指定服务器，返回是否成功。"""
    data = json.dumps(asdict(entry), ensure_ascii=False).encode("utf-8") + b"\n"
    sock: Optional[socket.socket] = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))
        sock.sendall(data)
        # 接收服务器确认（可选）
        try:
            ack = sock.recv(1024)
            return b"OK" in ack or b"ok" in ack
        except socket.timeout:
            # 没收到确认也算成功（数据已发送）
            return True
    except Exception:
        return False
    finally:
        if sock:
            try:
                sock.close()
            except Exception:
                pass


def load_feedback_config() -> dict:
    """加载反馈配置（上次使用的服务器地址等）。"""
    if os.path.exists(FEEDBACK_CONFIG_FILE):
        try:
            with open(FEEDBACK_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_feedback_config(config: dict) -> None:
    """保存反馈配置。"""
    try:
        with open(FEEDBACK_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
