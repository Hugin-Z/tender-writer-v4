# -*- coding: utf-8 -*-
"""
timing_report.py · 把 _timing.json 聚合为 markdown 报表(V3-3)

数据用途见 plans/v3-3.md §0:
- plan 估算校准:写 plan 时引用历史 timing 校准估算
- 慢阶段定位:跑完 demo 找最贵阶段排队优化
- 回归检测:commit 前后某阶段 duration 突变

输出:
- 控制台打印 markdown 报表
- 写入 project/output/_timing_report.md

用法:
    ./run_script.bat timing_report.py --project demo_cadre_training
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render_report(entries: list[dict]) -> str:
    """聚合 entries 按 stage,产出 markdown 表 + 最近 10 次详单。"""
    if not entries:
        return "# Timing Report\n\n(无 entry,_timing.json 为空)\n"

    by_stage: dict[str, list[dict]] = {}
    for e in entries:
        by_stage.setdefault(e.get("stage", "<unknown>"), []).append(e)

    lines: list[str] = []
    lines.append("# Timing Report\n")
    lines.append("## 阶段聚合统计\n")
    lines.append(
        "| 阶段 | 调用次数 | 最近 (s) | 平均 (s) | 最小 (s) | 最大 (s) | 失败次数 |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for stage in sorted(by_stage.keys()):
        es = by_stage[stage]
        durations = [e.get("duration_seconds", 0.0) for e in es]
        n_fail = sum(1 for e in es if not e.get("success", True))
        last = durations[-1] if durations else 0.0
        avg = statistics.mean(durations) if durations else 0.0
        lines.append(
            f"| {stage} | {len(es)} | {last:.2f} | {avg:.2f} | "
            f"{min(durations):.2f} | {max(durations):.2f} | {n_fail} |"
        )

    lines.append("")
    lines.append("## 最近 10 次调用\n")
    lines.append("| 时间 | 阶段 | 耗时 (s) | 状态 |")
    lines.append("|---|---|---|---|")
    for e in entries[-10:]:
        success = e.get("success", True)
        if success:
            status = "OK"
        else:
            err = e.get("error", "")[:40]
            status = f"FAIL ({err})"
        lines.append(
            f"| {e.get('started_at', '')} | {e.get('stage', '')} | "
            f"{e.get('duration_seconds', 0.0):.2f} | {status} |"
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(
        description="Timing report 报表生成(V3-3)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--project", required=True, help="项目名")
    args = p.parse_args()

    timing_path = ROOT / "projects" / args.project / "output" / "_timing.json"
    if not timing_path.exists():
        print(
            f"[错误] 未找到 {timing_path};是否跑过任何阶段脚本?",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        data = json.loads(timing_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[错误] _timing.json 解析失败: {exc!r}", file=sys.stderr)
        sys.exit(1)

    entries = data.get("entries", [])
    report = render_report(entries)

    out_path = timing_path.parent / "_timing_report.md"
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"\n[完成] 报表已写入 {out_path}({len(entries)} entries)")


if __name__ == "__main__":
    main()
