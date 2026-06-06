"""
Kimi CLI Adapter - 通过 subprocess 调用 kimi 命令行工具

完全复用 Kimi Code CLI 的认证，无需单独的 Moonshot API Key。
通过 `kimi --print` 非交互模式获取 LLM 响应。

注意事项：
- 每次调用都会启动一个完整的 kimi 进程，启动时间约 2-5 秒
- kimi 在 print 模式下会自动启用 yolo（自动批准所有工具调用）
- 这意味着 Kimi Manager 可能会主动读取文件、执行命令
- 如果需要严格限制 Kimi Manager 只"思考"不"操作"，建议使用 API 模式
"""

import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class FakeChoice:
    """模拟 OpenAI 响应结构"""

    message: "FakeMessage"


@dataclass
class FakeMessage:
    """模拟 OpenAI message 结构"""

    content: Optional[str]
    role: str = "assistant"
    tool_calls: Optional[list] = None


@dataclass
class FakeCompletion:
    """模拟 OpenAI completion 结构"""

    choices: list[FakeChoice]


class KimiCliAdapter:
    """
    模拟 OpenAI client 接口，底层通过 subprocess 调用 kimi CLI。

    使用方式与 OpenAI client 相同：
        client = KimiCliAdapter(kimi_exe_path="...")
        resp = client.chat.completions.create(model="kimi-for-coding", messages=[...])
    """

    def __init__(
        self,
        kimi_exe_path: Optional[str] = None,
        work_dir: Optional[str] = None,
        timeout: int = 120,
    ):
        self.kimi_exe = self._find_kimi_exe(kimi_exe_path)
        self.work_dir = work_dir or os.getcwd()
        self.timeout = timeout

    @staticmethod
    def _find_kimi_exe(explicit_path: Optional[str]) -> str:
        """查找 kimi 可执行文件"""
        if explicit_path and Path(explicit_path).exists():
            return str(Path(explicit_path).resolve())

        # 常见安装位置
        candidates = [
            # Windows VS Code 扩展
            Path.home()
            / "AppData/Roaming/Code/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi.exe",
            # 其他位置
            Path("kimi.exe"),
            Path("kimi"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate.resolve())

        raise FileNotFoundError(
            "找不到 kimi 可执行文件。请通过环境变量 KIMI_EXE_PATH 指定路径，"
            "或确保 kimi 在 PATH 中。"
        )

    class _CompletionsProxy:
        """模拟 client.chat.completions"""

        def __init__(self, adapter: "KimiCliAdapter"):
            self.adapter = adapter

        def create(
            self,
            model: str,
            messages: list[dict],
            temperature: Optional[float] = None,
            tools: Optional[list] = None,
            tool_choice: Optional[str] = None,
            **kwargs: Any,
        ) -> FakeCompletion:
            """通过 kimi --print 获取响应"""
            return self.adapter._call_kimi(model, messages, temperature)

    @property
    def chat(self) -> "_ChatProxy":
        return self._ChatProxy(self)

    class _ChatProxy:
        def __init__(self, adapter: "KimiCliAdapter"):
            self.adapter = adapter

        @property
        def completions(self) -> "KimiCliAdapter._CompletionsProxy":
            return KimiCliAdapter._CompletionsProxy(self.adapter)

    def _call_kimi(
        self, model: str, messages: list[dict], temperature: Optional[float]
    ) -> FakeCompletion:
        """调用 kimi CLI 并解析响应"""
        # 提取 system prompt 和 user input
        system_prompt = ""
        user_inputs = []
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
            elif msg.get("role") == "user":
                user_inputs.append(msg.get("content", ""))
            elif msg.get("role") == "assistant":
                # 历史对话中的 assistant 消息
                user_inputs.append(f"[Assistant]: {msg.get('content', '')}")
            elif msg.get("role") == "tool":
                user_inputs.append(f"[Tool Result]: {msg.get('content', '')}")

        full_prompt = self._build_prompt(system_prompt, user_inputs)

        # 构建命令
        cmd = [
            self.kimi_exe,
            "--print",
            "-p",
            full_prompt,
            "--output-format=stream-json",
            "--final-message-only",
            "--work-dir",
            self.work_dir,
        ]

        # 如果有 temperature，通过环境变量或参数传递
        # kimi CLI 可能没有直接的 temperature 参数，但可以通过模型选择间接控制

        # 执行
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"kimi CLI 调用超时（超过 {self.timeout} 秒）")

        elapsed = time.time() - start_time

        # 解析输出
        content = self._parse_output(result.stdout)

        if result.returncode != 0 and not content:
            stderr = result.stderr.strip()
            raise RuntimeError(
                f"kimi CLI 调用失败 (exit {result.returncode}): {stderr[:200]}"
            )

        return FakeCompletion(
            choices=[FakeChoice(message=FakeMessage(content=content))]
        )

    def _build_prompt(self, system_prompt: str, user_inputs: list[str]) -> str:
        """构建发送给 kimi 的完整 prompt"""
        parts = []
        if system_prompt:
            parts.append(f"[System Instructions]\n{system_prompt}\n")
        for i, user_input in enumerate(user_inputs):
            if i == len(user_inputs) - 1:
                parts.append(f"[User]\n{user_input}")
            else:
                parts.append(f"[History]\n{user_input}\n")
        return "\n".join(parts)

    def _parse_output(self, stdout: str) -> Optional[str]:
        """解析 kimi --output-format=stream-json 的输出"""
        # 过滤出 JSON 行
        json_lines = []
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                json_lines.append(line)

        if not json_lines:
            # 如果没有 JSON 行，返回原始输出（过滤掉 session 提示）
            lines = [
                l
                for l in stdout.strip().split("\n")
                if not l.startswith("To resume this session")
            ]
            return "\n".join(lines) if lines else None

        # 解析最后一行 assistant 消息
        for line in reversed(json_lines):
            try:
                data = json.loads(line)
                if data.get("role") == "assistant":
                    return data.get("content", "")
            except json.JSONDecodeError:
                continue

        # 回退：返回最后一行的内容
        try:
            data = json.loads(json_lines[-1])
            return data.get("content", "")
        except json.JSONDecodeError:
            return json_lines[-1]
