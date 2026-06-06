#!/usr/bin/env python3
"""零依赖测试运行器 — 自动发现并执行 tests/test_regression.py 中的 test_* 函数。"""

from __future__ import annotations

import importlib
import inspect
import sys
import traceback
from typing import Any, Callable, List, Tuple

# 确保项目根目录在 sys.path 中
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


def _discover_tests(module: Any, prefix: str = "test_") -> List[Tuple[str, Callable]]:
    """从模块中 discover 所有 test_* 函数。"""
    tests = []
    for name in dir(module):
        if name.startswith(prefix):
            obj = getattr(module, name)
            if callable(obj):
                tests.append((name, obj))
    tests.sort(key=lambda x: x[0])
    return tests


def _run_single(name: str, fn: Callable) -> Tuple[bool, str]:
    """执行单个测试，返回 (通过?, 错误信息)。"""
    try:
        fn()
        return True, ""
    except AssertionError as e:
        return False, f"AssertionError: {e}"
    except Exception as e:
        tb = traceback.format_exc()
        return False, f"{type(e).__name__}: {e}\n{tb}"


def main(argv: List[str]) -> int:
    # 导入测试模块
    import tests.test_regression as reg_mod

    # 如果需要重新加载（开发时反复运行）
    importlib.reload(reg_mod)

    tests = _discover_tests(reg_mod)

    # 名称过滤
    if argv:
        pattern = argv[0].lower()
        tests = [(n, f) for n, f in tests if pattern in n.lower()]
        if not tests:
            print(f"没有匹配 '{argv[0]}' 的测试")
            return 1

    total = len(tests)
    passed = 0
    failed: List[Tuple[str, str]] = []

    print(f"=" * 60)
    print(f"发现 {total} 个测试")
    print(f"=" * 60)

    for name, fn in tests:
        ok, err = _run_single(name, fn)
        if ok:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            failed.append((name, err))
            print(f"  [FAIL] {name}")

    print(f"=" * 60)
    print(f"结果: {passed}/{total} 通过")

    if failed:
        print()
        print("失败详情:")
        for name, err in failed:
            print(f"\n--- {name} ---")
            print(err)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
