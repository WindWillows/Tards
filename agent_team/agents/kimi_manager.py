"""Kimi 主控 Agent：任务拆解、审查、整合"""

from typing import Optional

from openai import OpenAI

from agent_team.core.agent import Agent
from agent_team.adapters.kimi_cli import KimiCliAdapter


class KimiManager(Agent):
    """
    Kimi 担任主控 Agent。
    职责：
    1. 将复杂需求拆解为可执行的步骤
    2. 审查 DeepSeek 的执行结果
    3. 整合各步骤结果，输出最终答案
    4. 不直接编写代码，只做规划和判断

    支持两种模式：
    - API 模式：使用 Moonshot 开放平台的 API Key（推荐，速度快）
    - CLI 模式：复用 Kimi Code CLI 的认证（无需额外 API Key，但每次调用启动较慢）
    """

    SYSTEM_PROMPT = """你是 Agent 团队的主控 Manager。你的职责是：

1. **任务拆解**：将复杂用户需求拆解为清晰、可独立执行的步骤列表
2. **质量审查**：严格审查执行 Agent 返回的结果，判断是否符合要求
3. **整合输出**：将多个步骤的结果整合为完整、连贯的最终答案

**重要原则**：
- 你自己不编写具体代码，只负责规划、审查和整合
- 审查时要关注：代码正确性、完整性、边界情况处理
- 如果执行结果有缺陷，明确指出问题并给出修改方向
- 使用中文进行思考和输出

**审查标准**：
- PASS：结果完整、逻辑正确、可直接使用
- RETRY：有缺陷但可以修正，给出具体修改意见
- STOP：方向完全错误或无意义，建议中止
"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        use_cli: bool = False,
        kimi_exe_path: Optional[str] = None,
        cli_timeout: int = 120,
    ):
        if use_cli:
            # CLI 模式：通过 subprocess 调用 kimi
            client = KimiCliAdapter(
                kimi_exe_path=kimi_exe_path,
                timeout=cli_timeout,
            )
            model = model or "kimi-for-coding"
        else:
            # API 模式：使用 OpenAI 兼容接口
            client = OpenAI(
                api_key=api_key or "",
                base_url=base_url or "https://api.moonshot.cn/v1",
            )
            model = model or "moonshot-v1-128k"

        super().__init__(
            name="Kimi-Manager",
            client=client,
            model=model,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=temperature,
            max_history=10,
        )
