# -*- coding: utf-8 -*-
"""
test_export_deliverables.py · export_deliverables 回归测试

覆盖函数:
- _safe_part_dir_name(name)
- build_deliverable_mapping(brief)  ★ happy path: case 2

测试目标:
    保证 v2 单元 7 P19 修复后,DELIVERABLE_MAPPING 从 response_file_parts
    动态生成,不再硬编码另一项目的 Part 名;C-attachment / D / 不适用模式不进映射。

运行:
    ./run_script.bat tests/test_export_deliverables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from export_deliverables import (  # noqa: E402
    _safe_part_dir_name,
    build_deliverable_mapping,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "export_deliverables"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def find_target(mapping: list[dict], target: str) -> dict | None:
    for entry in mapping:
        if entry.get("target") == target:
            return entry
    return None


def main() -> int:
    fails = 0
    cases_run = 0
    print("export_deliverables 测试")
    print()

    # ---- _safe_part_dir_name 单元测试 ----
    SAFE_NAME_CASES = [
        ("一、技术方案", "技术方案", "去掉中文数字+顿号前缀"),
        ("3.采购需求", "采购需求", "去掉阿拉伯数字+点前缀"),
        ("技术(附录)方案", "技术方案", "去掉半角括号内容"),
        ("", "part", "空字符串兜底为 part"),
        ("纯净名称", "纯净名称", "无前缀无括号原样返回"),
    ]
    for inp, expected, note in SAFE_NAME_CASES:
        cases_run += 1
        actual = _safe_part_dir_name(inp)
        ok = actual == expected
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] _safe_part_dir_name({inp!r}) -> {actual!r}  ({note})")
        if not ok:
            print(f"           expected: {expected!r}")
            fails += int(not ok)

    print()

    # ---- build_deliverable_mapping case 1: 空 parts ----
    cases_run += 1
    brief = load_fixture("brief_no_parts.json")
    mapping = build_deliverable_mapping(brief)
    ok = len(mapping) == 2  # 仅 STATIC_TOP_MAPPING
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] case_1_empty_parts: 仅 STATIC_TOP_MAPPING 2 项")
    if not ok:
        print(f"           expected len=2, actual len={len(mapping)}")
        print(f"           mapping={mapping}")
        fails += 1

    # ---- build_deliverable_mapping case 2: A+B+C+D 混合(happy path)----
    cases_run += 1
    brief = load_fixture("brief_a_b_c_mixed.json")
    mapping = build_deliverable_mapping(brief)
    # 期望: static 2 + A 1 + B 1 + C-template 1 + C-reference 1 + C-attachment 2 = 8
    # V4-4 起 C-attachment 映射 2 entry (copy_dir attachments 目录 + copy _manifest.yaml);
    # D 仍不映射
    expected_count = 8
    ok_count = len(mapping) == expected_count
    a_entry = find_target(mapping, "A 模式产出/01_技术方案(分章节).docx")
    b_entry = find_target(mapping, "B 模式产出/02_业绩证明(占位).docx")
    ct_entry = find_target(mapping, "C 模式产出/03_格式响应.docx")
    cr_entry = find_target(mapping, "C 模式产出/04_操作说明操作说明.md")
    # V4-4: C-attachment 双 entry (目录 + 同位置 _manifest.yaml)
    cattach_dir_entry = find_target(mapping, "C 模式产出/05_挂档资料(附件)")
    cattach_manifest_entry = find_target(mapping, "C 模式产出/05_挂档资料(附件)/_manifest.yaml")
    d_entry = find_target(mapping, "D 模式产出/06_外部信息.docx")  # 不应存在

    ok_a = a_entry is not None and a_entry.get("source") == "output/tender_response.docx"
    ok_b = b_entry is not None and b_entry.get("source") == "output/b_mode/业绩证明/assembled.docx"
    ok_ct = ct_entry is not None and ct_entry.get("source") == "output/c_mode/格式响应/filled.docx"
    ok_cr = cr_entry is not None and cr_entry.get("source") == "output/c_mode/操作说明/instructions.md"
    # V4-4 C-attachment 真行为断言 (替换原 ok_skip_cattach):
    # - dir entry: 源是 final_tender_package/attachments/<dir_name>, mode='copy_dir'
    # - manifest entry: 源是 output/c_mode/<dir_name>/attachments.yaml, mode='copy'
    ok_cattach_dir = (
        cattach_dir_entry is not None
        and cattach_dir_entry.get("source") == "final_tender_package/attachments/挂档资料"
        and cattach_dir_entry.get("mode") == "copy_dir"
    )
    ok_cattach_manifest = (
        cattach_manifest_entry is not None
        and cattach_manifest_entry.get("source") == "output/c_mode/挂档资料/attachments.yaml"
        and cattach_manifest_entry.get("mode") == "copy"
    )
    ok_skip_d = d_entry is None

    case2_ok = all([ok_count, ok_a, ok_b, ok_ct, ok_cr,
                    ok_cattach_dir, ok_cattach_manifest, ok_skip_d])
    icon = "PASS" if case2_ok else "FAIL"
    # 注:本 case 验 build_deliverable_mapping() 返回的路径映射字符串,不验
    # 产物实际落盘 (端到端落盘验证在 test_v45_merge.case_7_c_attachment_e2e)
    print(f"  [{icon}] case_2_a_b_c_mixed: A+B+C-template+C-reference+C-attachment 映射, D 跳过 (V4-4 真行为)")
    if not case2_ok:
        print(f"           len: expected={expected_count}, actual={len(mapping)}")
        print(f"           A ok={ok_a}, B ok={ok_b}, C-template ok={ok_ct}, C-reference ok={ok_cr}")
        print(f"           C-attachment dir ok={ok_cattach_dir}, manifest ok={ok_cattach_manifest}")
        print(f"           skip D ok={ok_skip_d}")
        fails += 1

    # ---- case 3: 2 个 A 模式 part(无防重)----
    cases_run += 1
    brief3 = {
        "response_file_parts": [
            {"name": "技术方案上", "production_mode": "A", "order": 1},
            {"name": "技术方案下", "production_mode": "A", "order": 2},
        ]
    }
    mapping3 = build_deliverable_mapping(brief3)
    a1 = find_target(mapping3, "A 模式产出/01_技术方案上(分章节).docx")
    a2 = find_target(mapping3, "A 模式产出/02_技术方案下(分章节).docx")
    case3_ok = len(mapping3) == 4 and a1 is not None and a2 is not None
    icon = "PASS" if case3_ok else "FAIL"
    print(f"  [{icon}] case_3_two_a_no_dedup: 2 个 A part 各自映射(与 v45_merge 防重不同)")
    if not case3_ok:
        print(f"           mapping3={mapping3}")
        fails += 1

    # ---- case 4: order 字段缺失,fallback 到 i+1 ----
    cases_run += 1
    brief4 = {
        "response_file_parts": [
            {"name": "首项", "production_mode": "B"},  # i=0, order fallback i+1=1
            {"name": "次项", "production_mode": "B"},  # i=1, order fallback i+1=2
        ]
    }
    mapping4 = build_deliverable_mapping(brief4)
    e1 = find_target(mapping4, "B 模式产出/01_首项(占位).docx")
    e2 = find_target(mapping4, "B 模式产出/02_次项(占位).docx")
    case4_ok = e1 is not None and e2 is not None
    icon = "PASS" if case4_ok else "FAIL"
    print(f"  [{icon}] case_4_order_fallback: order 缺失时 fallback 到 i+1")
    if not case4_ok:
        print(f"           mapping4={mapping4}")
        fails += 1

    print()
    print(f"总结:{cases_run - fails} 通过 / {fails} 失败  (共 {cases_run} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
