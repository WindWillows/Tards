"""对局日志管理模块。

职责：
  - 管理日志目录（绝对路径，避免随运行目录变化）
  - 按时间戳创建对局日志文件
  - 提供同时写入文件和控制台的日志写入器
"""

import os
import sys
from datetime import datetime
from typing import Optional, TextIO

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


class BattleLogWriter:
    """同时写入文件和控制台的日志写入器。

    用法：
        old_stdout = sys.stdout
        writer = BattleLogWriter.create_for_battle()
        sys.stdout = writer
        try:
            ...  # 游戏逻辑
        finally:
            sys.stdout = old_stdout
            writer.close()
    """

    def __init__(self, file_obj: TextIO, console_stdout=sys.stdout):
        self.file_obj = file_obj
        self.console_stdout = console_stdout

    @classmethod
    def create_for_battle(cls, console_stdout=sys.stdout) -> "BattleLogWriter":
        """创建一局对战的日志写入器，自动按时间戳生成文件。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOGS_DIR, f"battle_{timestamp}.log")
        file_obj = open(log_path, "w", encoding="utf-8")
        console_stdout.write(f"[系统] 对局日志已保存到: {log_path}\n")
        return cls(file_obj, console_stdout)

    def write(self, s: str) -> None:
        if s.strip():
            msg = s.strip()
            self.file_obj.write(msg + "\n")
            self.file_obj.flush()
            self.console_stdout.write(msg + "\n")
            self.console_stdout.flush()

    def flush(self) -> None:
        self.file_obj.flush()
        self.console_stdout.flush()

    def close(self) -> None:
        self.file_obj.close()
