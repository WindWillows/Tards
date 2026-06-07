#!/usr/bin/env python3
"""效果函数格式校验与运行时保护装饰器。

提供两种装饰器：
  - @special : 用于 MinionCard.special_fn（部署/回合触发效果）
  - @strategy: 用于 Strategy.effect_fn（策略卡效果）

设计原则：
  1. 模块导入时（游戏启动时）进行严格的签名校验与文档检查，
     不通过直接抛异常，防止运行时才暴露格式问题。
  2. 运行时自动检查目标存活，死亡异象的效果自动跳过。
  3. 异常安全：效果函数内部抛异常不会中断 EffectQueue，仅打印错误日志。
  4. 触发日志自动打印，方便调试。

扩展方式：
  若未来需要新增装饰器（如 @conspiracy），只需调用 _make_decorator() 并传入
  所需的参数即可，无需重复编写包装逻辑。
"""

import inspect
import warnings
import traceback
from functools import wraps
from typing import Callable, Optional, Set


# =============================================================================
# 通用校验与包装逻辑（内部 API，供扩展使用）
# =============================================================================

def _validate_signature(
    fn: Callable,
    decorator_name: str,
    required_params: Set[str],
    default_param: Optional[str] = None,
) -> None:
    """校验函数签名是否包含必要的参数，以及 default_param 是否有默认值。"""
    sig = inspect.signature(fn)
    params = set(sig.parameters.keys())

    missing = required_params - params
    if missing:
        raise TypeError(
            f"【{decorator_name} 格式错误】{fn.__name__} 缺少必要参数: {missing}\n"
            f"  正确签名示例：\n"
            f"  def {fn.__name__}({', '.join(required_params)}):\n"
            f"  请检查参数名拼写。"
        )

    if default_param:
        p = sig.parameters.get(default_param)
        if p and p.default is inspect.Parameter.empty:
            raise TypeError(
                f"【{decorator_name} 格式错误】{fn.__name__} 的 {default_param} "
                f"参数必须有默认值\n"
                f"  正确写法：...{default_param}=None)"
            )


def _validate_docstring(fn: Callable, decorator_name: str) -> None:
    """检查函数是否有非空的文档字符串。"""
    if not fn.__doc__ or not fn.__doc__.strip():
        warnings.warn(
            f"【{decorator_name} 警告】{fn.__name__} 缺少文档字符串。"
            f"请添加三重引号注释描述卡牌效果。",
            stacklevel=3,
        )
    elif "TODO" in fn.__doc__:
        warnings.warn(
            f"【{decorator_name} 提醒】{fn.__name__} 的文档字符串仍包含 TODO，"
            f"实现尚未完成。",
            stacklevel=3,
        )


def _make_wrapper(
    fn: Callable,
    *,
    target_param: Optional[str] = None,
    log_prefix: str = "效果触发",
) -> Callable:
    """构造运行时包装器。

    Args:
        fn: 被装饰的原始函数。
        target_param: 需要检查存活性的参数名（如 "minion" 或 "target"）。
        log_prefix: 日志前缀。
    """

    @wraps(fn)
    def wrapper(*args, **kwargs):
        # 尝试绑定参数以获取命名参数值
        try:
            sig = inspect.signature(fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
        except TypeError:
            bound = None

        # 1. 检查目标存活
        if target_param and bound:
            target = bound.arguments.get(target_param)
            if target is not None and hasattr(target, "is_alive"):
                if not target.is_alive():
                    print(
                        f"  [{log_prefix}] {fn.__name__} 尝试操作已死亡的 "
                        f"{getattr(target, 'name', target)}，已跳过"
                    )
                    return None

        # 2. 打印触发日志
        target_name = ""
        if target_param and bound:
            target = bound.arguments.get(target_param)
            if target is not None and hasattr(target, "name"):
                target_name = f" ({target.name})"
        print(f"  [{log_prefix}] {fn.__name__}{target_name}")

        # 3. 异常安全执行
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            target_str = ""
            if target_param and bound:
                target = bound.arguments.get(target_param)
                target_str = f" 目标={getattr(target, 'name', target)}"
            tb_line = traceback.format_exc().strip().splitlines()[-1]
            print(
                f"  [效果错误] {fn.__name__}{target_str}: {exc}\n"
                f"    {tb_line}"
            )
            return None

    wrapper._is_effect_wrapped = True
    wrapper._wrapped_fn = fn
    return wrapper


# =============================================================================
# 公共装饰器
# =============================================================================

def special(fn: Callable) -> Callable:
    """装饰 MinionCard.special_fn。

    签名要求：def xxx(minion, player, game, extras=None)
    运行时自动检查 minion.is_alive()，死亡时跳过。
    """
    _validate_signature(fn, "special", {"minion", "player", "game", "extras"}, "extras")
    _validate_docstring(fn, "special")
    return _make_wrapper(fn, target_param="minion", log_prefix="效果触发")


def strategy(fn: Callable) -> Callable:
    """装饰 Strategy.effect_fn。

    签名要求：def xxx(player, target, game, extras=None)
    运行时自动检查 target.is_alive()（若 target 支持）。
    """
    _validate_signature(
        fn, "strategy", {"player", "target", "game", "extras"}, "extras"
    )
    _validate_docstring(fn, "strategy")
    return _make_wrapper(fn, target_param="target", log_prefix="策略触发")
