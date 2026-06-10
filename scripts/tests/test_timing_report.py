# -*- coding: utf-8 -*-
"""
test_timing_report.py · timing_report 单元测试(V3-3)

覆盖函数:
- render_report(entries) ★ happy path: case 1
  - 单一 stage 多次调用 → 聚合 avg/min/max 正确
  - 多 stage 混合 → 表格按 stage 名字典序排序
  - 含失败 entry → 失败次数列 ≥1 + 最近 N 次详单含 FAIL 行
  - 空 entries → 输出"无 entry"提示
  - >10 entries → 最近 10 次详单只显示后 10 条

运行:
    ./run_script.bat tests/test_timing_report.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from timing_report import render_report  # noqa: E402


def main() -> int:
    fails = 0
    cases = 0
    print("timing_report 测试")
    print()

    # ---- case 1: 单一 stage 多次调用,聚合正确 (happy path) ----
    cases += 1
    entries = [
        {"stage": "parse_tender", "duration_seconds": 1.0, "success": True,
         "started_at": "2026-04-27T10:00:00"},
        {"stage": "parse_tender", "duration_seconds": 2.0, "success": True,
         "started_at": "2026-04-27T11:00:00"},
        {"stage": "parse_tender", "duration_seconds": 3.0, "success": True,
         "started_at": "2026-04-27T12:00:00"},
    ]
    out = render_report(entries)
    # 期望:parse_tender 行调用次数=3, 最近=3.00, 平均=2.00, 最小=1.00, 最大=3.00
    ok = (
        "parse_tender" in out
        and "| 3 | 3.00 | 2.00 | 1.00 | 3.00 | 0 |" in out
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_single_stage_aggregation (happy path)")
    if not ok:
        print(f"           output:\n{out}")
        fails += 1

    # ---- case 2: 多 stage 混合,按 stage 名排序 ----
    cases += 1
    entries = [
        {"stage": "parse_tender", "duration_seconds": 1.0, "success": True,
         "started_at": "2026-04-27T10:00:00"},
        {"stage": "compliance_check", "duration_seconds": 0.5, "success": True,
         "started_at": "2026-04-27T11:00:00"},
        {"stage": "v45_merge", "duration_seconds": 2.0, "success": True,
         "started_at": "2026-04-27T12:00:00"},
        {"stage": "compliance_check", "duration_seconds": 0.6, "success": True,
         "started_at": "2026-04-27T13:00:00"},
        {"stage": "parse_tender", "duration_seconds": 1.5, "success": True,
         "started_at": "2026-04-27T14:00:00"},
    ]
    out = render_report(entries)
    # 期望:3 个不同 stage,字典序 compliance_check < parse_tender < v45_merge
    cc_pos = out.find("| compliance_check |")
    pt_pos = out.find("| parse_tender |")
    vm_pos = out.find("| v45_merge |")
    ok = (
        cc_pos > 0 < pt_pos < vm_pos
        and cc_pos < pt_pos < vm_pos  # 字典序
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_multi_stage_sorted_lex")
    if not ok:
        print(f"           positions: cc={cc_pos}, pt={pt_pos}, vm={vm_pos}")
        fails += 1

    # ---- case 3: 含失败 entry → 失败次数 + FAIL 详单 ----
    cases += 1
    entries = [
        {"stage": "parse_tender", "duration_seconds": 1.0, "success": True,
         "started_at": "2026-04-27T10:00:00"},
        {"stage": "parse_tender", "duration_seconds": 0.5, "success": False,
         "error": "ValueError(boom)",
         "started_at": "2026-04-27T11:00:00"},
    ]
    out = render_report(entries)
    # 期望:聚合行失败次数=1;详单含 FAIL 行
    ok = (
        "| 2 |" in out and "| 1 |" in out  # 调用次数 2 + 失败次数 1
        and "FAIL (ValueError(boom))" in out
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_failure_recorded")
    if not ok:
        print(f"           output:\n{out}")
        fails += 1

    # ---- case 4: 空 entries → "无 entry" 提示 ----
    cases += 1
    out = render_report([])
    ok = "无 entry" in out
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_empty_entries_message")
    if not ok:
        print(f"           output: {out!r}")
        fails += 1

    # ---- case 5: >10 entries → 详单仅最近 10 ----
    cases += 1
    entries = [
        {"stage": f"stage_{i}", "duration_seconds": float(i), "success": True,
         "started_at": f"2026-04-27T{i:02d}:00:00"}
        for i in range(15)
    ]
    out = render_report(entries)
    # 期望:详单段只含 stage_5..stage_14(后 10 条),不含 stage_0..stage_4
    # (注意聚合表含全部 15 个 stage,所以只能在详单段范围内搜)
    detail_section = out.split("## 最近 10 次调用")[1]
    in_detail = {i: (f"| stage_{i} |" in detail_section) for i in range(15)}
    expected_in = set(range(5, 15))
    actual_in = {i for i, present in in_detail.items() if present}
    ok = actual_in == expected_in
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_recent_10_window")
    if not ok:
        print(f"           expected stages 5-14 in detail, actual present: {sorted(actual_in)}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
