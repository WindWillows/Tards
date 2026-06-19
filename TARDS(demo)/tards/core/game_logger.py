"""对局日志管理模块。

职责：
  - 管理日志目录（绝对路径，避免随运行目录变化）
  - 按时间戳创建对局日志文件
  - 提供结构化日志记录器（GameLogger），支持文件、控制台、UI 回调
  - 保留 BattleLogWriter 作为兼容层（旧代码 stdout 重定向方式）
"""

import os
import sys
import traceback
from datetime import datetime
from typing import Any, Callable, Optional, TextIO

# game_logger 现位于 tards/core/，需向上回溯到 TARDS(demo)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOGS_DIR = os.path.join(_PROJECT_ROOT, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)


class GameLogger:
    """结构化对局日志记录器。

    支持同时输出到：
      - 日志文件（按时间戳创建，UTF-8）
      - 控制台（默认 sys.stdout）
      - UI 回调（用于同步到 GUI 日志框）

    用法：
        logger = GameLogger.create_for_battle()
        logger.log_phase("draw", player="玩家1")
        logger.log_event("card_played", source=card, data={"cost": 3})
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        console: Optional[TextIO] = None,
        ui_callback: Optional[Callable[[str], None]] = None,
    ):
        self.file_path = file_path
        self.file_obj: Optional[TextIO] = None
        if file_path:
            self.file_obj = open(file_path, "w", encoding="utf-8")
        self.console = console or sys.stdout
        self.ui_callback = ui_callback

    @classmethod
    def create_for_battle(
        cls,
        console: Optional[TextIO] = None,
        ui_callback: Optional[Callable[[str], None]] = None,
    ) -> "GameLogger":
        """创建一局对战的日志记录器，自动按时间戳生成文件，并保留最近 10 份。

        若项目目录（或打包后的临时目录）不可写，则退化为仅控制台输出，
        避免日志文件创建失败导致游戏线程在创建 Game 对象前崩溃。
        """
        file_path: Optional[str] = None
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = os.path.join(LOGS_DIR, f"battle_{timestamp}.log")
            # 避免同一秒内多个进程冲突，追加序号
            counter = 1
            base_path = log_path
            while os.path.exists(log_path):
                log_path = f"{base_path[:-4]}_{counter}.log"
                counter += 1
            # 先尝试创建文件，确认目录可写
            with open(log_path, "w", encoding="utf-8"):
                pass
            file_path = log_path
        except Exception as e:
            if console:
                console.write(f"[系统] 无法创建对局日志文件: {e}，将仅输出到控制台\n")
                console.flush()

        logger = cls(file_path, console=console, ui_callback=ui_callback)
        if file_path:
            cls._rotate_battle_logs()
            if console:
                console.write(f"[系统] 对局日志已保存到: {file_path}\n")
                console.flush()
        return logger

    @classmethod
    def _rotate_battle_logs(cls, keep: int = 10) -> None:
        """仅保留 LOGS_DIR 下最近的 keep 份 battle_*.log 文件。"""
        try:
            entries = [
                os.path.join(LOGS_DIR, name)
                for name in os.listdir(LOGS_DIR)
                if name.startswith("battle_") and name.endswith(".log")
            ]
        except Exception:
            return
        if len(entries) <= keep:
            return
        entries.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        for old_path in entries[keep:]:
            try:
                os.remove(old_path)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 内部写入
    # ------------------------------------------------------------------
    def _write(self, level: str, msg: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{level}] {msg}"
        if self.file_obj:
            try:
                self.file_obj.write(line + "\n")
                self.file_obj.flush()
            except Exception:
                pass
        try:
            self.console.write(line + "\n")
            self.console.flush()
        except Exception:
            pass
        if self.ui_callback:
            try:
                self.ui_callback(line)
            except Exception:
                pass

    @staticmethod
    def _fmt_obj(obj: Any) -> str:
        if obj is None:
            return "None"
        if hasattr(obj, "name"):
            return f"{type(obj).__name__}:{getattr(obj, 'name', '?')}"
        return type(obj).__name__

    @staticmethod
    def _fmt_data(data: dict) -> str:
        """格式化事件数据，避免过长。"""
        if not data:
            return "{}"
        parts = []
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                parts.append(f"{k}={v}")
            else:
                parts.append(f"{k}={GameLogger._fmt_obj(v)}")
        return "{" + ", ".join(parts) + "}"

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------
    def log_event(
        self,
        event_type: str,
        source: Optional[Any] = None,
        data: Optional[dict] = None,
        listener_count: int = 0,
    ) -> None:
        """记录一次事件的发射。"""
        self._write(
            "EVENT",
            f"type={event_type} | source={self._fmt_obj(source)} | "
            f"listeners={listener_count} | data={self._fmt_data(data or {})}",
        )

    def log_response(
        self,
        event_type: str,
        listener_name: str,
        before_state: dict,
        after_state: dict,
        exception: Optional[Exception] = None,
    ) -> None:
        """记录一个监听器对事件的响应结果。"""
        if exception:
            status = f"ERROR:{exception}"
        elif after_state.get("cancelled") and not before_state.get("cancelled"):
            status = "CANCELLED"
        elif after_state.get("prevent_default") and not before_state.get("prevent_default"):
            status = "PREVENT_DEFAULT"
        else:
            status = "OK"

        changes = []
        for key in ("cancelled", "prevent_default"):
            b = before_state.get(key)
            a = after_state.get(key)
            if b != a:
                changes.append(f"{key}:{b}->{a}")
        if not changes:
            changes.append("no_state_change")

        self._write(
            "RESPONSE",
            f"{event_type} -> {listener_name} | "
            f"status={status} | changes=[{', '.join(changes)}]",
        )
        if exception:
            for line in traceback.format_exception_only(type(exception), exception):
                self._write("RESPONSE", f"  {line.rstrip()}")

    def log_phase(self, phase: str, player: Optional[Any] = None) -> None:
        """记录阶段切换。"""
        player_str = f" | player={self._fmt_obj(player)}" if player else ""
        self._write("PHASE", f"进入阶段: {phase}{player_str}")

    def log_action(self, msg: str) -> None:
        """记录玩家或系统动作。"""
        self._write("ACTION", msg)

    def log_info(self, msg: str) -> None:
        """记录普通信息。"""
        self._write("INFO", msg)

    def log_error(self, msg: str) -> None:
        """记录错误信息。"""
        self._write("ERROR", msg)

    def close(self) -> None:
        if self.file_obj:
            try:
                self.file_obj.close()
            except Exception:
                pass


class BattleLogWriter:
    """同时写入文件和控制台的日志写入器（兼容旧版 stdout 重定向）。

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
        self.log_path = getattr(file_obj, "name", None)

    @classmethod
    def create_for_battle(cls, console_stdout=sys.stdout) -> "BattleLogWriter":
        """创建一局对战的日志写入器，自动按时间戳生成文件。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOGS_DIR, f"battle_{timestamp}.log")
        # 避免同一秒内多个进程冲突，追加序号
        counter = 1
        base_path = log_path
        while os.path.exists(log_path):
            log_path = f"{base_path[:-4]}_{counter}.log"
            counter += 1
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
