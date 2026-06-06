"""命令行入口：交互式 REPL 和单次任务模式"""

import argparse
import io
import sys

# Windows 终端编码修复
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    except Exception:
        pass

from agent_team.config import load_config
from agent_team.agents import KimiManager, DeepSeekWorker
from agent_team.core.workflow import SequentialWorkflow, ReviewRetryWorkflow
from agent_team.tools import read_file, write_file, list_files, execute_python


def create_agents(cfg):
    """根据配置创建 Agent 实例"""
    manager = KimiManager(
        api_key=cfg.kimi_api_key,
        base_url=cfg.kimi_base_url,
        model=cfg.kimi_model,
        temperature=cfg.kimi_temperature,
        use_cli=cfg.kimi_use_cli,
        kimi_exe_path=cfg.kimi_exe_path or None,
        cli_timeout=cfg.kimi_cli_timeout,
    )
    worker = DeepSeekWorker(
        api_key=cfg.deepseek_api_key,
        base_url=cfg.deepseek_base_url,
        model=cfg.deepseek_model,
        temperature=cfg.deepseek_temperature,
    )
    # 给 Worker 注册工具
    worker.add_tools(read_file, write_file, list_files, execute_python)
    return manager, worker


def run_once(task: str, cfg, workflow_type: str = "sequential") -> str:
    """单次任务模式"""
    manager, worker = create_agents(cfg)

    if workflow_type == "sequential":
        wf = SequentialWorkflow(manager, worker, max_retries=cfg.max_retries)
        return wf.run(task)
    elif workflow_type == "review":
        wf = ReviewRetryWorkflow(manager, worker, max_retries=cfg.max_retries)
        return wf.run(task)
    else:
        raise ValueError(f"未知工作流类型: {workflow_type}")


def run_repl(cfg):
    """交互式 REPL 模式"""
    manager, worker = create_agents(cfg)
    wf = SequentialWorkflow(manager, worker, max_retries=cfg.max_retries)

    print("=" * 50)
    print("Agent Team 交互模式")
    print("Manager: Kimi  |  Worker: DeepSeek")
    print("输入任务描述，或输入 'quit' 退出")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        try:
            result = wf.run(user_input)
            print(f"\n团队: {result}")
        except Exception as e:
            print(f"\n[错误] {e}")


def main():
    parser = argparse.ArgumentParser(description="Agent Team CLI")
    parser.add_argument(
        "task", nargs="?", help="单次任务描述（省略则进入交互模式）"
    )
    parser.add_argument(
        "--config", "-c", help="配置文件路径（默认: agent_team_config.json）"
    )
    parser.add_argument(
        "--workflow",
        "-w",
        choices=["sequential", "review"],
        default="sequential",
        help="工作流类型: sequential（串行拆解）或 review（仅审查重试）",
    )
    args = parser.parse_args()

    # 加载配置
    try:
        cfg = load_config(args.config)
    except Exception as e:
        print(f"[错误] 配置加载失败: {e}")
        sys.exit(1)

    kimi_ready = cfg.kimi_use_cli or cfg.kimi_api_key
    if not kimi_ready or not cfg.deepseek_api_key:
        print("[错误] 缺少 API Key")
        if not kimi_ready:
            print("\n  Kimi (Moonshot) API Key 未配置")
            print("  方案1（推荐）: 申请 API Key")
            print("    - 前往 https://platform.moonshot.cn/ 注册并创建 API Key")
            print("    - 填入 agent_team_config.json 或设置环境变量 KIMI_API_KEY")
            print("  方案2（免 Key）: 复用 Kimi Code CLI")
            print("    - 在配置文件中设置 \"kimi_use_cli\": true")
            print("    - 确保 kimi 命令可用（已登录 Kimi Code CLI）")
        if not cfg.deepseek_api_key:
            print("\n  DeepSeek API Key 未配置")
            print("  - 请前往 https://platform.deepseek.com/ 注册并创建 API Key")
            print("  - 填入 agent_team_config.json 或设置环境变量 DEEPSEEK_API_KEY")
        print("\n  配置文件模板: agent_team_config.json.example")
        sys.exit(1)

    # 运行
    if args.task:
        print(f"[任务] {args.task}")
        print(f"[工作流] {args.workflow}")
        result = run_once(args.task, cfg, args.workflow)
        print(f"\n{result}")
    else:
        run_repl(cfg)


if __name__ == "__main__":
    main()
