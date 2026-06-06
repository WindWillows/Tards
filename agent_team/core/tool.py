"""工具注册框架：装饰器 + 自动 schema 生成"""

import inspect
import json
from typing import Any, Callable, get_type_hints


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: list[dict] = []

    def register(self, fn: Callable, description: str = "") -> Callable:
        """注册一个工具函数"""
        name = fn.__name__
        self._tools[name] = fn

        # 生成 JSON schema
        sig = inspect.signature(fn)
        hints = get_type_hints(fn)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            param_type = hints.get(param_name, str)
            json_type = self._python_type_to_json(param_type)
            properties[param_name] = {
                "type": json_type,
                "description": "",  # 可扩展
            }
            if param.default is inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description or fn.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }
        self._schemas.append(schema)
        return fn

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具并返回字符串结果"""
        if name not in self._tools:
            return json.dumps({"error": f"Tool '{name}' not found"}, ensure_ascii=False)

        fn = self._tools[name]
        try:
            result = fn(**arguments)
            if result is None:
                return ""
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    @property
    def schemas(self) -> list[dict]:
        """返回 OpenAI 格式的 tools 列表"""
        return self._schemas

    @property
    def names(self) -> list[str]:
        return list(self._tools.keys())

    @staticmethod
    def _python_type_to_json(py_type: type) -> str:
        """简单映射 Python 类型到 JSON schema 类型"""
        mapping = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return mapping.get(py_type, "string")


# 全局默认注册表
_default_registry = ToolRegistry()


def tool(description: str = ""):
    """工具装饰器

    用法:
        @tool(description="读取文件")
        def read_file(path: str) -> str:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        _default_registry.register(fn, description)
        return fn

    return decorator


def get_default_registry() -> ToolRegistry:
    return _default_registry
