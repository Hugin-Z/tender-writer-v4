# -*- coding: utf-8 -*-
"""
_timing_hook.py · 阶段耗时埋点上下文管理器(V3-3)

每个核心脚本主入口包一层 stage_timer,记录起止时间 + 耗时秒数 + 成功状态,
append 到 project_dir/output/_timing.json。

数据用途:
- 写 plan 时引用历史 timing 校准估算(替换"X 分钟墙钟估算"为"实测 X 秒")
- 慢阶段定位(timing_report 找最贵阶段排队优化)
- 回归检测(commit 前后某阶段 duration 突变)
- demo 端到端节奏检查

用法:
    from _timing_hook import stage_timer

    def main():
        # ... 解析 args ...
        project_dir = ROOT / 'projects' / args.project
        with stage_timer("parse_tender", project_dir):
            # ... 原 main 逻辑 ...
            pass
"""
from __future__ import annotations

import json
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


@contextmanager
def stage_timer(stage_name: str, project_dir: Path | None = None):
    """记录一次脚本调用的耗时,append 到 project_dir/output/_timing.json。

    project_dir 为 None 时跳过写入(脚本无 --project 上下文 fallback)。
    异常路径:即使 with 块抛异常,也会记录 success=False 然后 re-raise。
    """
    started_at = datetime.now().isoformat(timespec='seconds')
    t0 = time.perf_counter()
    success = True
    error_msg = ""
    try:
        yield
    except SystemExit as exc:
        # sys.exit() 触发 SystemExit,exit code 0 视为正常退出
        if exc.code not in (None, 0):
            success = False
            error_msg = f"SystemExit({exc.code})"
        raise
    except BaseException as exc:
        success = False
        error_msg = repr(exc)[:200]
        raise
    finally:
        duration = time.perf_counter() - t0
        ended_at = datetime.now().isoformat(timespec='seconds')
        if project_dir is not None:
            _append_entry(project_dir, {
                "stage": stage_name,
                "started_at": started_at,
                "ended_at": ended_at,
                "duration_seconds": round(duration, 3),
                "success": success,
                "error": error_msg,
            })


def _append_entry(project_dir: Path, entry: dict):
    """append entry 到 project_dir/output/_timing.json,文件不存在则新建。"""
    out_dir = Path(project_dir) / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    timing_path = out_dir / "_timing.json"
    if timing_path.exists():
        try:
            data = json.loads(timing_path.read_text(encoding='utf-8'))
            if not isinstance(data, dict) or "entries" not in data:
                data = {"entries": []}
        except json.JSONDecodeError:
            data = {"entries": []}
    else:
        data = {"entries": []}
    data["entries"].append(entry)
    timing_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )
