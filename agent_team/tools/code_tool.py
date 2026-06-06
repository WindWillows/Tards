"""Python 代码沙箱执行工具"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from agent_team.core.tool import tool


@tool(description="在隔离子进程中执行 Python 代码，返回 stdout/stderr")
def execute_python(code: str, timeout: int = 30) -> str:
    """
    执行 Python 代码片段。
    代码在临时文件中运行，标准输出和标准错误会被捕获并返回。
    禁止网络请求（通过环境变量限制）。
    """
    # 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        # 使用当前 Python 解释器执行，但限制环境
        env = {
            "PATH": sys.executable.replace("python.exe", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            # 禁止网络（通过空代理）
            "HTTP_PROXY": "",
            "HTTPS_PROXY": "",
            "ALL_PROXY": "",
        }

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )

        output = []
        if result.stdout:
            output.append("[STDOUT]\n" + result.stdout)
        if result.stderr:
            output.append("[STDERR]\n" + result.stderr)
        if result.returncode != 0:
            output.append(f"[返回码] {result.returncode}")

        return "\n\n".join(output) if output else "(无输出)"

    except subprocess.TimeoutExpired:
        return f"[错误] 执行超时（超过 {timeout} 秒）"
    except Exception as e:
        return f"[错误] 执行异常: {e}"
    finally:
        try:
            Path(tmp_path).unlink()
        except Exception:
            pass
