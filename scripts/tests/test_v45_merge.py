# -*- coding: utf-8 -*-
"""
test_v45_merge.py · v45_merge 回归测试

覆盖函数:
- build_merge_order(brief)  ★ happy path: case 1 + case 2
- _main_body(args, project_dir) C-attachment 端到端  ★ V4-4 case_7

测试目标:
    保证按 response_file_parts 动态生成合并顺序,A 模式防重 + 未识别 mode 兜底为
    inapplicable 这两条 v2 单元 7 P1 修复后的关键逻辑不回归;V4-4 起 C-attachment
    入 merge_order (非 skip), 端到端跑通拷贝 attachments + 写 ops_checklist 段。

运行:
    ./run_script.bat tests/test_v45_merge.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

# 让测试文件能 import scripts/v45_merge.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from v45_merge import build_merge_order, _main_body  # noqa: E402

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
    # V4-4 case_5: C-attachment 从"整项跳过"改为"入 merge_order kind='c_attachment'"。
    # 验 build_merge_order 纯函数分流改变 (端到端 attachments 拷贝 + ops_checklist 段
    # 在 case_7 验证)
    (
        "case_5_c_attachment_in_order",
        load_fixture("brief_c_attachment.json"),
        [
            (0, "a_mode", "前导技术"),
            (1, "c_attachment", "挂档资料"),
            (2, "b_mode", "尾部材料"),
        ],
        "V4-4: C-attachment 入 merge_order kind='c_attachment',前后 part 顺序保留",
    ),
    (
        "case_6_empty_parts",
        {"response_file_parts": []},
        [],
        "边界:空 parts → 空 order",
    ),
]


def _run_case_7_c_attachment_e2e() -> tuple[bool, str]:
    """V4-4 case_7: C-attachment 端到端 (_main_body 真跑) e2e 验证。

    fixture 源: scripts/tests/fixtures/v45_merge/c_attachment_e2e/
    (tender_brief.json + attachments.yaml + sample_attachment.txt)

    验三件 (按 plan §S6 + 自检 2 + 自检 3):
    - final_tender_package/attachments/<part>/<resolved_file> 真产出
    - operations_checklist.md 含 "## 挂档资料 (附件)" 段标题
    - operations_checklist.md 显式标 "待人工放置" + 占位 source_path "__PENDING_USER__"
    """
    try:
        from docx import Document
    except ImportError:
        return False, "缺少 python-docx 依赖"

    fixture_dir = FIXTURES / "c_attachment_e2e"
    with tempfile.TemporaryDirectory() as td:
        proj_dir = Path(td) / "test_c_attach"
        output_dir = proj_dir / "output"
        c_part_dir = output_dir / "c_mode" / "挂档资料"
        c_part_attach_dir = c_part_dir / "attachments"
        c_part_attach_dir.mkdir(parents=True, exist_ok=True)

        # 复制 fixture 文件 → 模拟 extract + fill 产出
        shutil.copy2(fixture_dir / "tender_brief.json",
                     output_dir / "tender_brief.json")
        shutil.copy2(fixture_dir / "attachments.yaml",
                     c_part_dir / "attachments.yaml")
        shutil.copy2(fixture_dir / "sample_attachment.txt",
                     c_part_attach_dir / "营业执照.txt")  # 模拟 fill resolved 拷贝
        # .reviewed marker (ensure_reviewed 闸门)
        (output_dir / "tender_brief.reviewed").write_text("", encoding="utf-8")
        # A 模式 tender_response.docx (空文档, 让 composer 有 fragment 可处理)
        doc = Document()
        doc.add_paragraph("test fixture: A 模式技术方案占位")
        doc.save(str(output_dir / "tender_response.docx"))

        # 跑 v45_merge _main_body
        args = argparse.Namespace(project="test_c_attach")
        _main_body(args, proj_dir)

        # 断言三件 (真字段, 禁泛断言)
        pkg = proj_dir / "final_tender_package"
        attach_file = pkg / "attachments" / "挂档资料" / "营业执照.txt"
        ops_path = pkg / "operations_checklist.md"

        if not attach_file.exists():
            return False, f"resolved 附件未拷贝到 {attach_file}"
        if not ops_path.exists():
            return False, f"operations_checklist.md 未产出"
        ops_content = ops_path.read_text(encoding="utf-8")
        if "## 挂档资料 (附件)" not in ops_content:
            return False, "ops_checklist 未含 '## 挂档资料 (附件)' 段标题"
        if "待人工放置" not in ops_content:
            return False, "ops_checklist 未显式标 '待人工放置'"
        if "__PENDING_USER__" not in ops_content:
            return False, "ops_checklist 未显式透传 '__PENDING_USER__' 占位字面"
        # pending 项 target_filename 也应出现 (R10 占位透传)
        if "项目案例X.txt" not in ops_content:
            return False, "ops_checklist 未列出 pending 项 target_filename"

    return True, ""


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

    # V4-4 case_7: C-attachment 端到端 _main_body 真跑
    ok, err = _run_case_7_c_attachment_e2e()
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}] case_7_c_attachment_e2e         "
          f"V4-4: _main_body 真跑, attachments/ + ops_checklist 真验证")
    if not ok:
        print(f"           {err}")
        fails += 1

    print()
    print(f"总结:{len(CASES) + 1 - fails} 通过 / {fails} 失败")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
