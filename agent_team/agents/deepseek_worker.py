"""DeepSeek 执行 Agent：代码编写、具体任务执行"""

from openai import OpenAI

from agent_team.core.agent import Agent


class DeepSeekWorker(Agent):
    """
    DeepSeek 担任执行 Agent。
    职责：
    1. 根据任务描述编写高质量代码
    2. 执行具体的分析、计算任务
    3. 使用工具（文件读写、代码执行）完成工作
    4. 返回完整、可直接使用的结果
    """

    SYSTEM_PROMPT = """你是 Agent 团队的执行 Worker。你的职责是：

1. **编写代码**：根据任务需求编写完整、高质量的 Python 代码
2. **任务执行**：完成具体的技术分析、计算、文件操作等任务
3. **工具使用**：主动使用可用的工具（文件读写、代码执行）来完成工作

**重要原则**：
- 代码必须完整，包含必要的导入和类型注解
- 对于复杂逻辑，编写简洁的测试用例验证正确性
- 如果任务涉及项目文件，先读取相关文件了解上下文
- 如果代码需要验证，使用 execute_python 工具运行并检查输出
- 使用中文注释和文档字符串
- 返回结果时，如果包含代码，使用 markdown 代码块格式

**代码质量要求**：
- 处理边界情况和异常
- 变量命名清晰
- 避免硬编码魔法数字
- 适当添加日志或错误提示
"""

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float = 0.3):
        client = OpenAI(api_key=api_key, base_url=base_url)
        super().__init__(
            name="DeepSeek-Worker",
            client=client,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=temperature,
            max_history=10,
        )
