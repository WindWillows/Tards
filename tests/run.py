#!/usr/bin/env python3
"""零依赖测试运行器 — 自动发现并执行 tests/test_*.py 中的 test_* 函数。"""

from __future__ import annotations

import glob
import importlib
import inspect
import os
import sys
import traceback
from typing import Any, Callable, List, Tuple

# 确保项目根目录和游戏源码目录在 sys.path 中
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_demo_root = os.path.join(_project_root, "TARDS(demo)")
for _path in (_project_root, _demo_root):
    if _path not in sys.path:
        sys.path.insert(0, _path)


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
    # 发现并导入所有 tests/test_*.py 模块
    test_files = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "test_*.py")))
    modules = []
    for path in test_files:
        mod_name = os.path.splitext(os.path.basename(path))[0]
        full_name = f"tests.{mod_name}"
        try:
            mod = importlib.import_module(full_name)
            importlib.reload(mod)
            modules.append(mod)
        except Exception as e:
            print(f"[FAIL] 导入 {full_name} 失败: {e}")
            return 1

    tests: List[Tuple[str, Callable]] = []
    for mod in modules:
        tests.extend(_discover_tests(mod))
    tests.sort(key=lambda x: x[0])

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
