"""工作流引擎：串行工作流 + 审查重试机制"""

import json
from typing import Optional

from .message import AgentResponse, ReviewVerdict, ToolResult


class SequentialWorkflow:
    """
    串行工作流：
    1. Kimi 将用户需求拆解为步骤列表
    2. 对每个步骤：DeepSeek 执行 → Kimi 审查
    3. 审查通过则继续，不通过则 ReviewRetryWorkflow 处理
    4. Kimi 整合所有结果输出最终答案
    """

    def __init__(self, manager, worker, max_retries: int = 2):
        self.manager = manager
        self.worker = worker
        self.max_retries = max_retries

    def run(self, user_input: str) -> str:
        """运行完整工作流"""
        print("\n[Manager] 正在拆解任务...")
        steps = self._decompose(user_input)
        print(f"[Manager] 拆解完成，共 {len(steps)} 个步骤")

        results = []
        for i, step in enumerate(steps, 1):
            print(f"\n[Workflow] ===== 步骤 {i}/{len(steps)}: {step[:60]}... =====")
            result = self._execute_step(step, i, len(steps))
            if result is None:
                return f"[Workflow] 步骤 {i} 执行失败，工作流中止。"
            results.append(result)

        print("\n[Manager] 正在整合最终结果...")
        final = self._summarize(user_input, steps, results)
        return final

    def _decompose(self, user_input: str) -> list[str]:
        """让 Kimi 拆解任务为步骤列表"""
        prompt = f"""请将以下用户需求拆解为可逐步执行的步骤列表。
要求：
1. 每个步骤必须具体、可独立执行
2. 只输出步骤列表，不要额外解释
3. 使用 JSON 数组格式输出，例如：["步骤1描述", "步骤2描述"]

用户需求：{user_input}
"""
        resp = self.manager.run(prompt)
        content = resp.content.strip()

        # 尝试解析 JSON
        try:
            # 处理 markdown 代码块
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            steps = json.loads(content)
            if isinstance(steps, list):
                return [str(s) for s in steps]
        except Exception:
            pass

        # 回退：按行分割
        lines = [l.strip("- *• \")").strip() for l in content.split("\n") if l.strip()]
        return lines if lines else [user_input]

    def _execute_step(
        self, step: str, current: int, total: int
    ) -> Optional[str]:
        """执行单个步骤，含审查重试"""
        retry = ReviewRetryWorkflow(
            self.manager, self.worker, max_retries=self.max_retries
        )
        context = f"这是第 {current}/{total} 步，请完成此步骤任务。"
        result = retry.run(step, context)
        return result

    def _summarize(self, user_input: str, steps: list[str], results: list[str]) -> str:
        """让 Kimi 整合所有步骤结果"""
        prompt = f"""请根据以下步骤执行结果，给用户一个完整、连贯的最终回答。

原始需求：{user_input}

各步骤结果：
"""
        for i, (step, result) in enumerate(zip(steps, results), 1):
            prompt += f"\n步骤 {i}: {step}\n结果:\n{result}\n"

        prompt += "\n请整合以上信息，输出最终答案（使用中文）："
        resp = self.manager.run(prompt)
        return resp.content


class ReviewRetryWorkflow:
    """
    审查重试工作流：
    1. DeepSeek 执行任务
    2. Kimi 审查结果（PASS / RETRY / STOP）
    3. 如 RETRY 且未超限：携带修改意见，DeepSeek 重做
    4. 如 PASS 或超限：返回结果
    """

    def __init__(self, manager, worker, max_retries: int = 2):
        self.manager = manager
        self.worker = worker
        self.max_retries = max_retries

    def run(self, task: str, context: str = "") -> Optional[str]:
        """
        运行审查重试循环。

        Args:
            task: 具体任务描述
            context: 额外上下文（如步骤位置信息）
        """
        full_task = task
        if context:
            full_task = f"【上下文】{context}\n【任务】{task}"

        last_result = ""
        for attempt in range(self.max_retries + 1):
            print(f"  [Worker] 执行中... (尝试 {attempt + 1}/{self.max_retries + 1})")

            # DeepSeek 执行
            self.worker.clear_history()
            resp = self.worker.run(full_task)

            # 处理工具调用
            if resp.has_tool_calls:
                tool_results = self.worker.execute_tools(resp.tool_calls)
                resp = self.worker.run_with_tool_results(full_task, tool_results)

            last_result = resp.content

            # Kimi 审查
            print(f"  [Manager] 审查结果...")
            verdict = self._review(task, last_result)
            print(f"  [Manager] 审查结论: {verdict.verdict}")

            if verdict.verdict == "PASS":
                return last_result
            elif verdict.verdict == "STOP":
                print(f"  [Manager] 审查未通过，中止: {verdict.reason}")
                return None
            elif verdict.verdict == "RETRY":
                if attempt < self.max_retries:
                    print(f"  [Manager] 需要重做: {verdict.suggestions[:100]}...")
                    full_task = (
                        f"【任务】{task}\n"
                        f"【上次结果】{last_result[:500]}\n"
                        f"【修改意见】{verdict.suggestions}\n"
                        f"请根据修改意见重做此任务。"
                    )
                else:
                    print(f"  [Manager] 已达最大重试次数，返回最后一次结果")
                    return last_result + f"\n\n[警告] 经过 {self.max_retries + 1} 次尝试仍未通过审查"

        return last_result

    def _review(self, task: str, result: str) -> ReviewVerdict:
        """让 Kimi 审查 DeepSeek 的结果"""
        prompt = f"""你是一位严格的代码审查员。请审查以下任务执行结果。

【原始任务】
{task}

【执行结果】
{result[:2000]}

请给出审查结论，必须严格使用以下 JSON 格式（不要输出其他内容）：
{{
  "verdict": "PASS" 或 "RETRY" 或 "STOP",
  "reason": "简要说明理由",
  "suggestions": "如果是 RETRY，请给出具体的修改意见；PASS 或 STOP 可留空"
}}

审查标准：
- PASS：结果完整、正确，可以直接使用
- RETRY：结果有缺陷但可以修正，需要重做
- STOP：任务方向错误或无意义，应该中止
"""
        self.manager.clear_history()
        resp = self.manager.run(prompt)
        content = resp.content.strip()

        # 解析 JSON
        try:
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            data = json.loads(content)
            return ReviewVerdict(
                verdict=data.get("verdict", "RETRY"),
                reason=data.get("reason", ""),
                suggestions=data.get("suggestions", ""),
            )
        except Exception:
            # 回退：根据关键词判断
            if "PASS" in content:
                return ReviewVerdict("PASS", reason="关键词匹配通过")
            elif "STOP" in content:
                return ReviewVerdict("STOP", reason="关键词匹配中止")
            else:
                return ReviewVerdict("RETRY", reason="无法解析审查结果", suggestions=content[:200])
