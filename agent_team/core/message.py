"""Agent 间消息结构"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ToolCall:
    """LLM 请求调用工具"""

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ToolResult:
    """工具执行结果"""

    call_id: str
    name: str
    content: str
    is_error: bool = False


@dataclass
class ReviewVerdict:
    """Kimi 对 DeepSeek 结果的审查结论"""

    verdict: str  # "PASS", "RETRY", "STOP"
    reason: str = ""
    suggestions: str = ""  # RETRY 时的修改意见

    def __post_init__(self):
        if self.verdict not in ("PASS", "RETRY", "STOP"):
            self.verdict = "RETRY"


@dataclass
class AgentResponse:
    """Agent.run() 的返回结构"""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None  # 原始 LLM 响应对象

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0
