# -*- coding: utf-8 -*-
"""
test_generate_outline.py · generate_outline 回归测试

覆盖函数:
- load_project_type(json_path)  ★ happy path: case 1
- load_outline_template(project_type)  ★ happy path: case 4
- build_outline_from_template(...)  ★ happy path: case 7
- VALID_PROJECT_TYPES (常量校验)

测试目标:
    1. project_type 5 类合法值各能加载到对应 outline_skeleton.md
    2. 非法 / 缺字段 / 空 project_type 兜底为 "" 或 None
    3. build_outline_from_template 能把 score_rows 填到覆盖度自检表

不测试 build_outline()(主入口耦合 brief_schema 模块,纯函数测试只盖核心子函数)。

运行:
    ./run_script.bat tests/test_generate_outline.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from generate_outline import (  # noqa: E402
    load_project_type,
    load_outline_template,
    build_outline_from_template,
    VALID_PROJECT_TYPES,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "generate_outline"


def write_temp_json(data: dict) -> Path:
    """把 dict 写到临时 json 文件,返回路径。调用者负责 unlink。"""
    fd, name = tempfile.mkstemp(suffix=".json", text=True)
    path = Path(name)
    import os
    os.close(fd)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    fails = 0
    cases = 0
    print("generate_outline 测试")
    print()

    # ---- case 1: load_project_type 从 fixture 读 (happy path)----
    cases += 1
    actual = load_project_type(FIXTURES / "brief_engineering.json")
    ok = actual == "engineering"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_load_engineering (happy path)")
    if not ok:
        print(f"           expected='engineering', actual={actual!r}")
        fails += 1

    # ---- case 2: 非法 project_type ----
    cases += 1
    tmp = write_temp_json({"extracted": {"project_type": "INVALID_TYPE"}})
    try:
        actual = load_project_type(tmp)
    finally:
        tmp.unlink()
    ok = actual == ""
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_invalid_type_fallback")
    if not ok:
        print(f"           expected='', actual={actual!r}")
        fails += 1

    # ---- case 3: 缺 project_type 字段 ----
    cases += 1
    tmp = write_temp_json({"extracted": {"budget": "500000元"}})
    try:
        actual = load_project_type(tmp)
    finally:
        tmp.unlink()
    ok = actual == ""
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_missing_field_fallback")
    if not ok:
        print(f"           expected='', actual={actual!r}")
        fails += 1

    # ---- case 4: load_outline_template 主类型 (happy path)----
    cases += 1
    tpl = load_outline_template("engineering")
    ok = tpl is not None and len(tpl) > 0
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_load_template_engineering (happy path)")
    if not ok:
        print(f"           tpl={tpl!r}")
        fails += 1

    # ---- case 5: 5 类各加载一次 ----
    cases += 1
    all_loaded = True
    failed_types = []
    for t in VALID_PROJECT_TYPES:
        tpl = load_outline_template(t)
        if tpl is None or len(tpl) == 0:
            all_loaded = False
            failed_types.append(t)
    ok = all_loaded
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_load_all_5_types (engineering/platform/research/planning/other)")
    if not ok:
        print(f"           failed types: {failed_types}")
        fails += 1

    # ---- case 6: 空 project_type 兜底 ----
    cases += 1
    tpl = load_outline_template("")
    ok = tpl is None
    print(f"  [{'PASS' if ok else 'FAIL'}] case_6_empty_type_returns_none")
    if not ok:
        print(f"           expected None, actual={tpl!r}")
        fails += 1

    # ---- case 7: build_outline_from_template 集成 (happy path)----
    cases += 1
    template = load_outline_template("engineering")
    score_rows = [
        {"_row_no": 1, "评分项": "项目管理体系", "分值": "20", "评分项归属": "技术方案"},
        {"_row_no": 2, "评分项": "技术方案完整性", "分值": "15", "评分项归属": "技术方案"},
    ]
    out = build_outline_from_template(template, "技术方案", score_rows, "engineering")
    ok = (
        "# 技术方案 提纲(方向 C;project_type=engineering)" in out
        and "R01" in out
        and "R02" in out
        and "项目管理体系" in out
        and "合计覆盖分值:35" in out  # 20 + 15
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_7_build_outline_integration (happy path)")
    if not ok:
        print(f"           output preview (first 500 chars):\n{out[:500]}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
