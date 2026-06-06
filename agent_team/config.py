"""配置管理：JSON 文件 + 环境变量"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class AgentConfig:
    """Agent 团队配置"""

    # Kimi API 模式
    kimi_api_key: str = ""
    kimi_base_url: str = "https://api.moonshot.cn/v1"
    kimi_model: str = "moonshot-v1-128k"
    kimi_temperature: float = 0.3

    # Kimi CLI 模式（复用 Kimi Code CLI 的认证）
    kimi_use_cli: bool = False
    kimi_exe_path: str = ""
    kimi_cli_timeout: int = 120

    # DeepSeek
    deepseek_api_key: str = "sk-c3faa8acb25f4007951166529ebd959b"
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_temperature: float = 0.3

    # 工作流
    max_retries: int = 2
    default_timeout: int = 120

    # 代码执行
    code_timeout: int = 30
    allowed_dirs: list[str] = field(default_factory=list)


def _get_project_root() -> Path:
    """获取项目根目录（agent_team 的父目录）"""
    return Path(__file__).parent.parent


def load_config(config_path: Optional[str] = None) -> AgentConfig:
    """
    加载配置，优先级：
    1. 传入的 config_path
    2. 项目根目录的 agent_team_config.json
    3. 环境变量
    """
    cfg = AgentConfig()

    # 尝试读取 JSON 配置文件
    if config_path:
        path = Path(config_path)
    else:
        path = _get_project_root() / "agent_team_config.json"

    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, value in data.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)

    # 环境变量覆盖
    env_map = {
        "kimi_api_key": "KIMI_API_KEY",
        "kimi_base_url": "KIMI_BASE_URL",
        "kimi_model": "KIMI_MODEL",
        "kimi_use_cli": "KIMI_USE_CLI",
        "kimi_exe_path": "KIMI_EXE_PATH",
        "kimi_cli_timeout": "KIMI_CLI_TIMEOUT",
        "deepseek_api_key": "DEEPSEEK_API_KEY",
        "deepseek_base_url": "DEEPSEEK_BASE_URL",
        "deepseek_model": "DEEPSEEK_MODEL",
    }
    for attr_name, env_name in env_map.items():
        val = os.getenv(env_name)
        if val is not None:
            # 布尔值转换
            if attr_name == "kimi_use_cli":
                setattr(cfg, attr_name, val.lower() in ("true", "1", "yes"))
            elif attr_name in ("kimi_cli_timeout",):
                setattr(cfg, attr_name, int(val))
            else:
                setattr(cfg, attr_name, val)

    # 默认允许目录为项目根目录
    if not cfg.allowed_dirs:
        cfg.allowed_dirs = [str(_get_project_root())]

    return cfg
