"""对局日志轮转回归测试 — 保留最近 10 份 battle_*.log。"""

from __future__ import annotations

import os
import tempfile
import time

from tards.core import game_logger as gl


def _make_fake_log_file(logs_dir: str, timestamp_offset: float) -> str:
    """在 logs_dir 下创建一个带时间戳的假 battle_*.log 文件。"""
    path = os.path.join(logs_dir, f"battle_{int(timestamp_offset * 1000)}.log")
    with open(path, "w", encoding="utf-8") as f:
        f.write("dummy")
    # 通过修改访问/修改时间模拟不同创建时间
    os.utime(path, (timestamp_offset, timestamp_offset))
    return path


def test_game_logger_keeps_recent_10_battle_logs():
    """创建 13 份日志后，应仅保留修改时间最新的 10 份。"""
    original_logs_dir = gl.LOGS_DIR
    with tempfile.TemporaryDirectory() as tmpdir:
        gl.LOGS_DIR = tmpdir
        try:
            paths = []
            for i in range(13):
                paths.append(_make_fake_log_file(tmpdir, time.time() + i))
                # 保证 mtime 严格递增
                time.sleep(0.001)

            gl.GameLogger._rotate_battle_logs(keep=10)

            remaining = sorted(
                [
                    os.path.join(tmpdir, name)
                    for name in os.listdir(tmpdir)
                    if name.startswith("battle_") and name.endswith(".log")
                ],
                key=lambda p: os.path.getmtime(p),
            )
            assert len(remaining) == 10, f"期望保留 10 份，实际 {len(remaining)} 份"
            # 最旧的 3 份应被删除
            for old in paths[:3]:
                assert not os.path.exists(old), f"旧日志应被删除: {old}"
            # 最新的 10 份应保留
            for new in paths[3:]:
                assert os.path.exists(new), f"新日志应被保留: {new}"
        finally:
            gl.LOGS_DIR = original_logs_dir


def test_game_logger_create_for_battle_rotates_automatically():
    """create_for_battle 创建新日志后会自动清理到最近 10 份。"""
    original_logs_dir = gl.LOGS_DIR
    with tempfile.TemporaryDirectory() as tmpdir:
        gl.LOGS_DIR = tmpdir
        try:
            for i in range(12):
                logger = gl.GameLogger.create_for_battle()
                logger.close()
                time.sleep(0.001)

            remaining = [
                name
                for name in os.listdir(tmpdir)
                if name.startswith("battle_") and name.endswith(".log")
            ]
            assert len(remaining) == 10, f"期望保留 10 份，实际 {len(remaining)} 份"
        finally:
            gl.LOGS_DIR = original_logs_dir
