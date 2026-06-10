# -*- coding: utf-8 -*-
"""
run_all.py · tests 一键跑全部

发现 scripts/tests/test_*.py,逐个 import 并调用其 main(),汇总退出码。

运行:
    ./run_script.bat tests/run_all.py

退出码:
    0 = 全部测试通过
    1 = 至少 1 个测试失败
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent


def discover_tests() -> list[Path]:
    return sorted(TESTS_DIR.glob("test_*.py"))


def run_one(test_path: Path) -> int:
    spec = importlib.util.spec_from_file_location(test_path.stem, test_path)
    if spec is None or spec.loader is None:
        print(f"[错误] 无法加载 {test_path.name}", file=sys.stderr)
        return 1
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"[错误] {test_path.name} 加载时抛异常: {exc!r}", file=sys.stderr)
        return 1
    main_fn = getattr(mod, "main", None)
    if main_fn is None:
        print(f"[错误] {test_path.name} 缺 main() 函数", file=sys.stderr)
        return 1
    try:
        rc = main_fn()
        return int(rc) if rc is not None else 0
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    except Exception as exc:
        print(f"[错误] {test_path.name} main() 抛异常: {exc!r}", file=sys.stderr)
        return 1


def main() -> int:
    tests = discover_tests()
    if not tests:
        print("[警告] 未发现任何 test_*.py")
        return 0

    print(f"发现 {len(tests)} 个测试文件:")
    for tp in tests:
        print(f"  - {tp.name}")
    print()

    results: list[tuple[str, int]] = []
    for tp in tests:
        print("=" * 60)
        print(f"运行: {tp.name}")
        print("=" * 60)
        rc = run_one(tp)
        results.append((tp.name, rc))
        print()

    print("=" * 60)
    print("总览")
    print("=" * 60)
    fails = sum(1 for _, rc in results if rc != 0)
    for name, rc in results:
        icon = "PASS" if rc == 0 else "FAIL"
        print(f"  [{icon}] {name}")
    print()
    print(f"汇总:{len(results) - fails} 通过 / {fails} 失败")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
