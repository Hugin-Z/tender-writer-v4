# -*- coding: utf-8 -*-
"""V3-13: demo_reset 回归测试。

3 个轻量 case(unit test git wrapper 价值低,只测路径白名单 + dry-run 输出):
- case_1_ensure_repo_root_rejects_non_repo: 在临时目录跑 → 友好报错退出
- case_2_list_tracked_returns_43_files:    在仓库根跑 → 返回 ≥40 个文件
- case_3_dry_run_main_outputs_preview:     dry-run 模式 main → 含"DRY-RUN"

运行:
    ./run_script.bat tests/test_demo_reset.py
"""
from __future__ import annotations

import io
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from demo_reset import (  # noqa: E402
    ensure_repo_root,
    list_tracked,
    main,
)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main_test() -> int:
    fails = 0
    cases = 0
    print("demo_reset 测试")
    print()

    # ---- case 1: ensure_repo_root 在非仓库根抛 SystemExit ----
    cases += 1
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        stderr_buf = io.StringIO()
        try:
            with redirect_stderr(stderr_buf):
                ensure_repo_root(cwd=tmp_path)
            print(f"  [FAIL] case_1_ensure_repo_root_rejects_non_repo")
            print(f"           expected SystemExit, got normal return")
            fails += 1
        except SystemExit as e:
            err = stderr_buf.getvalue()
            ok = e.code == 1 and "必须在仓库根" in err
            print(f"  [{'PASS' if ok else 'FAIL'}] case_1_ensure_repo_root_rejects_non_repo")
            if not ok:
                print(f"           exit_code={e.code}, stderr={err!r}")
                fails += 1

    # ---- case 2: list_tracked 在仓库根返回 ≥40 文件 ----
    cases += 1
    files = list_tracked(REPO_ROOT)
    ok = len(files) >= 40 and any("tender_brief.json" in f for f in files)
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_list_tracked_returns_files")
    if not ok:
        print(f"           len(files)={len(files)}, sample={files[:3]}")
        fails += 1

    # ---- case 3: dry-run 模式 main 输出含 "DRY-RUN" ----
    cases += 1
    # 模拟 sys.argv = []  (默认行为 = dry-run)
    saved_argv = sys.argv
    sys.argv = ["demo_reset.py"]
    saved_cwd = Path.cwd()
    import os
    os.chdir(REPO_ROOT)
    stdout_buf = io.StringIO()
    try:
        with redirect_stdout(stdout_buf):
            main()
        out = stdout_buf.getvalue()
        ok = False
        print(f"  [FAIL] case_3_dry_run_main_outputs_preview")
        print(f"           expected SystemExit, got normal return")
        fails += 1
    except SystemExit as e:
        out = stdout_buf.getvalue()
        ok = e.code == 0 and "DRY-RUN" in out and "没有执行任何变更" in out
        print(f"  [{'PASS' if ok else 'FAIL'}] case_3_dry_run_main_outputs_preview")
        if not ok:
            print(f"           exit_code={e.code}")
            print(f"           stdout snippet: {out[:200]!r}")
            fails += 1
    finally:
        sys.argv = saved_argv
        os.chdir(saved_cwd)

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main_test())
