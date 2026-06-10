# -*- coding: utf-8 -*-
"""
test_v45_merge.py · v45_merge 回归测试

覆盖函数:
- build_merge_order(brief)  ★ happy path: case 1 + case 2

测试目标:
    保证按 response_file_parts 动态生成合并顺序,A 模式防重 + C-attachment 跳过 +
    未识别 mode 兜底为 inapplicable 这三条 v2 单元 7 P1 修复后的关键逻辑不回归。

运行:
    ./run_script.bat tests/test_v45_merge.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 让测试文件能 import scripts/v45_merge.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v45_merge import build_merge_order  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "v45_merge"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# (case_name, brief_dict, expected_order_list, note)
CASES: list[tuple[str, dict, list, str]] = [
    (
        "case_1_a_only",
        load_fixture("brief_a_only.json"),
        [(0, "a_mode", "技术方案")],
        "happy path: 单 A 模式 part",
    ),
    # 注:验 build_merge_order() 纯函数分流,不验执行端渲染落盘
    (
        "case_2_a_b_c_mixed",
        load_fixture("brief_a_b_c_mixed.json"),
        [
            (0, "a_mode", "技术方案"),
            (1, "b_mode", "业绩证明"),
            (2, "c_template", "格式响应"),
            (3, "c_reference", "操作说明"),
        ],
        "happy path: A+B+C-template+C-reference 主流场景",
    ),
    (
        "case_3_a_dedup",
        {
            "response_file_parts": [
                {"name": "技术方案 第一部分", "production_mode": "A"},
                {"name": "技术方案 第二部分", "production_mode": "A"},
            ]
        },
        [(0, "a_mode", "技术方案 第一部分")],
        "A 模式只追加一次(a_mode_appended 防重)",
    ),
    (
        "case_4_d_and_unrecognized",
        load_fixture("brief_d_inapplicable.json"),
        [
            (0, "inapplicable", "外部信息采集"),
            (1, "inapplicable", "无模式声明"),
            (2, "inapplicable", "未识别模式"),
        ],
        "D / 空 mode / 未识别 mode 全部归为 inapplicable",
    ),
    (
        "case_5_c_attachment_skip",
        load_fixture("brief_c_attachment_skip.json"),
        [
            (0, "a_mode", "前导技术"),
            (2, "b_mode", "尾部材料"),
        ],
        "C-attachment 整项跳过,前后 part 顺序保留",
    ),
    (
        "case_6_empty_parts",
        {"response_file_parts": []},
        [],
        "边界:空 parts → 空 order",
    ),
]


def main() -> int:
    fails = 0
    print(f"v45_merge.build_merge_order fixture:{len(CASES)} 个用例")
    print()
    for case_name, brief, expected, note in CASES:
        actual = build_merge_order(brief)
        ok = actual == expected
        icon = "PASS" if ok else "FAIL"
        print(f"  [{icon}] {case_name:30s}  {note}")
        if not ok:
            print(f"           expected: {expected}")
            print(f"           actual:   {actual}")
            fails += 1

    print()
    print(f"总结:{len(CASES) - fails} 通过 / {fails} 失败")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
