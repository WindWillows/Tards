"""文件操作工具：限制在项目目录内"""

import json
import os
from pathlib import Path

from agent_team.core.tool import tool


def _resolve_path(path: str, allowed_dirs: list[str]) -> Path:
    """解析并校验路径，必须在 allowed_dirs 内"""
    target = Path(path).resolve()
    for allowed in allowed_dirs:
        allowed_path = Path(allowed).resolve()
        try:
            target.relative_to(allowed_path)
            return target
        except ValueError:
            continue
    raise PermissionError(f"路径 '{path}' 不在允许的目录范围内")


@tool(description="读取文本文件内容")
def read_file(path: str, allowed_dirs: list[str] = None) -> str:
    """读取指定路径的文本文件，返回内容字符串"""
    if allowed_dirs is None:
        allowed_dirs = [str(Path(__file__).parent.parent.parent)]

    target = _resolve_path(path, allowed_dirs)
    if not target.exists():
        return f"[错误] 文件不存在: {path}"
    try:
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[错误] 读取失败: {e}"


@tool(description="写入文本文件")
def write_file(path: str, content: str, allowed_dirs: list[str] = None) -> str:
    """将内容写入指定路径的文件，目录不存在会自动创建"""
    if allowed_dirs is None:
        allowed_dirs = [str(Path(__file__).parent.parent.parent)]

    target = _resolve_path(path, allowed_dirs)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return f"[成功] 已写入: {path} (大小: {len(content)} 字符)"
    except Exception as e:
        return f"[错误] 写入失败: {e}"


@tool(description="列出目录下的文件和子目录")
def list_files(path: str = ".", allowed_dirs: list[str] = None) -> str:
    """列出指定目录下的文件和子目录名称"""
    if allowed_dirs is None:
        allowed_dirs = [str(Path(__file__).parent.parent.parent)]

    target = _resolve_path(path, allowed_dirs)
    if not target.exists():
        return f"[错误] 目录不存在: {path}"
    if not target.is_dir():
        return f"[错误] 不是目录: {path}"

    try:
        entries = []
        for entry in sorted(target.iterdir()):
            prefix = "[D]" if entry.is_dir() else "[F]"
            entries.append(f"{prefix} {entry.name}")
        return "\n".join(entries) if entries else "(空目录)"
    except Exception as e:
        return f"[错误] 列出失败: {e}"
