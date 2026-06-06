"""Agent 基类：封装 LLM 调用、历史管理、工具调用"""

import json
from typing import Any, Optional

from openai import OpenAI

from .message import AgentResponse, ToolCall, ToolResult
from .tool import ToolRegistry


class Agent:
    """
    Agent 基类。封装与 LLM 的交互，支持：
    - 多轮对话历史
    - 工具注册与自动调用
    - OpenAI 兼容格式的 API 调用
    """

    def __init__(
        self,
        name: str,
        client: OpenAI,
        model: str,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_history: int = 20,
    ):
        self.name = name
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_history = max_history
        self.history: list[dict] = []
        self.registry = ToolRegistry()

    def add_tool(self, fn: Any) -> "Agent":
        """注册一个工具函数到当前 Agent"""
        # 如果 fn 已经被 @tool 装饰过，它已经有注册信息
        # 这里我们重新注册到当前 Agent 的 registry
        from .tool import get_default_registry

        default_reg = get_default_registry()
        if fn.__name__ in default_reg.names:
            # 从默认注册表复制 schema
            for schema in default_reg.schemas:
                if schema["function"]["name"] == fn.__name__:
                    self.registry._tools[fn.__name__] = fn
                    self.registry._schemas.append(schema)
                    break
        return self

    def add_tools(self, *fns: Any) -> "Agent":
        for fn in fns:
            self.add_tool(fn)
        return self

    def run(
        self, user_input: str, tools: Optional[list[str]] = None
    ) -> AgentResponse:
        """
        执行一次 Agent 调用。

        Args:
            user_input: 用户输入或上层 Agent 的指令
            tools: 指定允许使用的工具名称列表，None 表示全部
        """
        messages = self._build_messages(user_input)

        # 准备工具 schema
        tool_schemas = self._filter_tools(tools)
        kwargs = {}
        if tool_schemas:
            kwargs["tools"] = tool_schemas
            kwargs["tool_choice"] = "auto"

        # 调用 LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            **kwargs,
        )

        msg = response.choices[0].message
        content = msg.content or ""

        # 解析 tool_calls
        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        # 更新历史
        self._update_history(user_input, content, tool_calls)

        return AgentResponse(
            content=content,
            tool_calls=tool_calls,
            raw=response,
        )

    def run_with_tool_results(
        self, user_input: str, tool_results: list[ToolResult]
    ) -> AgentResponse:
        """
        携带工具执行结果再次调用 LLM。
        用于处理 LLM 请求工具调用后的第二轮对话。
        """
        # history 中已包含 user_input + assistant(with tool_calls)
        # 只需要追加 tool results
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history)

        # 添加 tool 结果
        for tr in tool_results:
            messages.append({
                "role": "tool",
                "tool_call_id": tr.call_id,
                "content": tr.content,
            })

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )

        msg = response.choices[0].message
        content = msg.content or ""

        for tr in tool_results:
            self.history.append({
                "role": "tool",
                "tool_call_id": tr.call_id,
                "content": tr.content,
            })
        self.history.append({"role": "assistant", "content": content})
        self._trim_history()

        return AgentResponse(content=content, raw=response)

    def clear_history(self):
        """清空对话历史"""
        self.history = []

    def _build_messages(self, user_input: str) -> list[dict]:
        """构建发送给 LLM 的 messages"""
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_input})
        return messages

    def _update_history(
        self, user_input: str, assistant_content: str, tool_calls: list[ToolCall]
    ):
        """更新内部历史"""
        self.history.append({"role": "user", "content": user_input})
        if tool_calls:
            self.history.append({
                "role": "assistant",
                "content": assistant_content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in tool_calls
                ],
            })
        else:
            self.history.append({
                "role": "assistant",
                "content": assistant_content,
            })
        self._trim_history()

    def _trim_history(self):
        """限制历史长度，保留 system prompt 语义"""
        if len(self.history) > self.max_history * 2:
            # 保留最近 max_history 轮
            self.history = self.history[-self.max_history * 2 :]

    def _filter_tools(self, names: Optional[list[str]]) -> list[dict]:
        """过滤工具 schema"""
        if not self.registry.schemas:
            return []
        if names is None:
            return self.registry.schemas
        return [
            s for s in self.registry.schemas if s["function"]["name"] in names
        ]

    def execute_tools(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
        """执行工具调用列表"""
        results = []
        for tc in tool_calls:
            output = self.registry.execute(tc.name, tc.arguments)
            is_error = output.startswith("[错误]") or (output.strip().startswith("{") and '"error"' in output)
            results.append(
                ToolResult(
                    call_id=tc.id,
                    name=tc.name,
                    content=output,
                    is_error=is_error,
                )
            )
        return results
