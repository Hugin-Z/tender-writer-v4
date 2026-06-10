# -*- coding: utf-8 -*-
"""
test_timing_hook.py · _timing_hook 单元测试(V3-3)

覆盖函数:
- stage_timer 上下文管理器 ★ happy path: case 1
  - 正常 with 块 → entry 写入,success=True
  - 异常 with 块 → entry 写入,success=False,异常 re-raise
  - SystemExit(0) → success=True;SystemExit(非 0) → success=False
  - project_dir=None → 不写,不抛异常
- _append_entry → 已存在文件 append 不丢旧 entries

运行:
    ./run_script.bat tests/test_timing_hook.py
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _timing_hook import stage_timer, _append_entry  # noqa: E402


def make_tmp_project_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="tender_writer_timing_test_"))


def read_entries(project_dir: Path) -> list[dict]:
    timing = project_dir / "output" / "_timing.json"
    if not timing.exists():
        return []
    return json.loads(timing.read_text(encoding="utf-8"))["entries"]


def main() -> int:
    fails = 0
    cases = 0
    print("_timing_hook 测试")
    print()

    # ---- case 1: 正常 with 块 (happy path) ----
    cases += 1
    tmp = make_tmp_project_dir()
    try:
        with stage_timer("test_normal", tmp):
            time.sleep(0.05)
        entries = read_entries(tmp)
        e = entries[0]
        ok = (
            len(entries) == 1
            and e["stage"] == "test_normal"
            and e["success"] is True
            and 0.04 < e["duration_seconds"] < 0.5  # 宽容时间漂移
            and "started_at" in e and "ended_at" in e
        )
        print(f"  [{'PASS' if ok else 'FAIL'}] case_1_normal_block (happy path)")
        if not ok:
            print(f"           entry: {e}")
            fails += 1
    finally:
        shutil.rmtree(tmp)

    # ---- case 2: 异常 with 块 → 记录 success=False + re-raise ----
    cases += 1
    tmp = make_tmp_project_dir()
    try:
        try:
            with stage_timer("test_fail", tmp):
                raise ValueError("boom")
        except ValueError:
            re_raised = True
        else:
            re_raised = False
        entries = read_entries(tmp)
        e = entries[0]
        ok = (
            re_raised
            and len(entries) == 1
            and e["success"] is False
            and "ValueError" in e["error"]
            and "boom" in e["error"]
        )
        print(f"  [{'PASS' if ok else 'FAIL'}] case_2_exception_records_failure_and_reraise")
        if not ok:
            print(f"           re_raised: {re_raised}, entry: {e}")
            fails += 1
    finally:
        shutil.rmtree(tmp)

    # ---- case 3: project_dir=None 静默不写 ----
    cases += 1
    try:
        with stage_timer("test_none", None):
            time.sleep(0.01)
        ok = True  # 走到这里说明不抛异常
        print(f"  [{'PASS' if ok else 'FAIL'}] case_3_none_project_dir_silent")
    except Exception as exc:
        print(f"  [FAIL] case_3_none_project_dir_silent: 抛了异常 {exc!r}")
        fails += 1

    # ---- case 4: _append_entry 已存在文件 append 不丢旧 entries ----
    cases += 1
    tmp = make_tmp_project_dir()
    try:
        # 先 append 2 条
        _append_entry(tmp, {"stage": "first", "duration_seconds": 1.0,
                            "success": True, "error": "",
                            "started_at": "2026-01-01T00:00:00",
                            "ended_at": "2026-01-01T00:00:01"})
        _append_entry(tmp, {"stage": "second", "duration_seconds": 2.0,
                            "success": True, "error": "",
                            "started_at": "2026-01-01T00:00:02",
                            "ended_at": "2026-01-01T00:00:04"})
        # 再 append 1 条
        _append_entry(tmp, {"stage": "third", "duration_seconds": 3.0,
                            "success": True, "error": "",
                            "started_at": "2026-01-01T00:00:05",
                            "ended_at": "2026-01-01T00:00:08"})
        entries = read_entries(tmp)
        ok = (
            len(entries) == 3
            and entries[0]["stage"] == "first"
            and entries[1]["stage"] == "second"
            and entries[2]["stage"] == "third"
        )
        print(f"  [{'PASS' if ok else 'FAIL'}] case_4_append_preserves_history")
        if not ok:
            print(f"           entries: {entries}")
            fails += 1
    finally:
        shutil.rmtree(tmp)

    # ---- case 5: SystemExit(0) → success=True ----
    cases += 1
    tmp = make_tmp_project_dir()
    try:
        try:
            with stage_timer("test_sysexit_0", tmp):
                raise SystemExit(0)
        except SystemExit:
            pass
        entries = read_entries(tmp)
        ok = len(entries) == 1 and entries[0]["success"] is True
        print(f"  [{'PASS' if ok else 'FAIL'}] case_5_sysexit_zero_treated_as_ok")
        if not ok:
            print(f"           entry: {entries}")
            fails += 1
    finally:
        shutil.rmtree(tmp)

    # ---- case 6: SystemExit(1) → success=False ----
    cases += 1
    tmp = make_tmp_project_dir()
    try:
        try:
            with stage_timer("test_sysexit_1", tmp):
                raise SystemExit(1)
        except SystemExit:
            pass
        entries = read_entries(tmp)
        e = entries[0]
        ok = (
            len(entries) == 1
            and e["success"] is False
            and "SystemExit(1)" in e["error"]
        )
        print(f"  [{'PASS' if ok else 'FAIL'}] case_6_sysexit_nonzero_records_failure")
        if not ok:
            print(f"           entry: {e}")
            fails += 1
    finally:
        shutil.rmtree(tmp)

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
