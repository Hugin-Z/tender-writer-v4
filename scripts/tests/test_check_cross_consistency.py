# -*- coding: utf-8 -*-
"""
test_check_cross_consistency.py · check_cross_consistency 回归测试

覆盖函数:
- parse_d_plus(text)
- parse_people(text)              ← 含 v2.0.1 团队上下文窗口过滤回归
- parse_money_in_yuan(text)
- check_duration_vs_dplus(...)    ★ happy path: case 8
- check_team_cost_vs_budget(...)  ★ happy path: case 11
- check_key_numbers_consistency(...) ★ happy path: case 12

测试目标:
    1. 解析函数的字符串边界(空格容错 / 边界数字 / 多匹配)
    2. v2.0.1 团队语境窗口过滤(培训规模 / 服务对象不计入团队成本)
    3. 三个 check_* 函数的失败 / 警告 / 通过 三态都能触发

运行:
    ./run_script.bat tests/test_check_cross_consistency.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_cross_consistency import (  # noqa: E402
    parse_d_plus,
    parse_people,
    parse_money_in_yuan,
    check_duration_vs_dplus,
    check_team_cost_vs_budget,
    check_key_numbers_consistency,
    # V3-9
    check_field_consistency,
    check_resume_org_consistency,
    check_section_ref_validity,
    extract_docx_text,
    _normalize_for_token,
    _jaccard,
    NAME_RE,
    REF_RE,
)

import json
from docx import Document

V39_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "check_cross_consistency"


def assert_eq(actual, expected, label: str) -> bool:
    if actual == expected:
        print(f"  [PASS] {label}")
        return True
    print(f"  [FAIL] {label}")
    print(f"           expected: {expected!r}")
    print(f"           actual:   {actual!r}")
    return False


def assert_contains(issues: list[str], substring: str, label: str) -> bool:
    hit = any(substring in m for m in issues)
    if hit:
        print(f"  [PASS] {label}")
        return True
    print(f"  [FAIL] {label}")
    print(f"           expected substring: {substring!r}")
    print(f"           issues: {issues!r}")
    return False


def main() -> int:
    fails = 0
    cases = 0
    print("check_cross_consistency 测试")
    print()

    # ---- parse_d_plus ----
    cases += 1
    if not assert_eq(
        parse_d_plus("D+15 调研, D+30 初稿, D+60 终稿"),
        [15, 30, 60],
        "case_1_parse_d_plus_basic (happy path)",
    ):
        fails += 1

    cases += 1
    if not assert_eq(
        parse_d_plus("方案 D + 45,初稿 D+45"),
        [45, 45],
        "case_2_parse_d_plus_space_tolerant",
    ):
        fails += 1

    # ---- parse_people ----
    cases += 1
    if not assert_eq(
        parse_people("项目组共15人"),
        [15],
        "case_3_parse_people_team_context_hit",
    ):
        fails += 1

    cases += 1
    if not assert_eq(
        parse_people("培训不少于100人"),
        [],
        "case_4_parse_people_filter_training (v2.0.1 回归)",
    ):
        fails += 1

    cases += 1
    if not assert_eq(
        parse_people("服务3000万群众,项目组1人带技术骨干3位"),
        [1, 3],
        "case_5_parse_people_mixed_only_team",
    ):
        fails += 1

    # ---- parse_money_in_yuan ----
    cases += 1
    if not assert_eq(
        parse_money_in_yuan("预算50万元"),
        [(500000.0, "50万元")],
        "case_6_parse_money_wanyuan (happy path)",
    ):
        fails += 1

    cases += 1
    if not assert_eq(
        parse_money_in_yuan("保证金3000元"),
        [(3000.0, "3000元")],
        "case_7_parse_money_yuan_4digits",
    ):
        fails += 1

    # ---- check_duration_vs_dplus ----
    cases += 1
    if not assert_contains(
        check_duration_vs_dplus(60, [15, 30, 60]),
        "[通过]",
        "case_8_dplus_within_duration (happy path)",
    ):
        fails += 1

    cases += 1
    if not assert_contains(
        check_duration_vs_dplus(60, [130]),
        "[失败]",
        "case_9_dplus_hard_violation",
    ):
        fails += 1

    cases += 1
    if not assert_contains(
        check_duration_vs_dplus(60, [90]),
        "[警告]",
        "case_10_dplus_soft_violation",
    ):
        fails += 1

    # ---- check_team_cost_vs_budget ----
    cases += 1
    # 20人 × 50% × 60天 × 1500元 = 900000 元;预算 500000 × 1.5 = 750000 → 超
    if not assert_contains(
        check_team_cost_vs_budget(
            people_counts=[20],
            duration_days=60,
            budget_yuan=500_000,
            per_person_day_yuan=1500,
        ),
        "[失败]",
        "case_11_team_cost_overrun (happy path)",
    ):
        fails += 1

    # ---- check_key_numbers_consistency ----
    cases += 1
    # 预算 5,000,000 元;3000万元 = 30,000,000 在 1-10x 区间 → 警告
    if not assert_contains(
        check_key_numbers_consistency(
            "项目500万元,保险额3000万元",
            budget_yuan=5_000_000,
        ),
        "[警告]",
        "case_12_money_soft_inflated (happy path)",
    ):
        fails += 1

    # ───────────────────────────────────────
    # V3-9: 项 4/5/6 新增 case 13-18
    # ───────────────────────────────────────
    brief_data = json.loads((V39_FIXTURES / "brief_minimal.json").read_text(encoding="utf-8"))
    brief_extracted = brief_data["extracted"]

    def get_h1(docx_path: Path) -> list[str]:
        return [
            p.text.strip()
            for p in Document(str(docx_path)).paragraphs
            if getattr(p.style, "name", "") == "Heading 1" and p.text.strip()
        ]

    # ---- case 13: clean fixture 三项检查全 [通过] / [信息],0 [失败] ----
    cases += 1
    clean_p = V39_FIXTURES / "clean_response.docx"
    clean_text = extract_docx_text(clean_p)
    clean_h1 = get_h1(clean_p)
    issues_4 = check_field_consistency(brief_extracted, clean_text, clean_h1)
    issues_5 = check_resume_org_consistency(clean_p)
    issues_6 = check_section_ref_validity(clean_p)
    all13 = issues_4 + issues_5 + issues_6
    fail_count = sum(1 for m in all13 if m.startswith("[失败]"))
    ok = fail_count == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] case_13_clean_no_failures (V3-9 happy path)")
    if not ok:
        print(f"           failures: {[m for m in all13 if m.startswith('[失败]')]}")
        fails += 1

    # case 13 子项 a: clean fixture NAME_RE 不跨人(C7) — 张三 不带技术负责人
    cases += 1
    text_c7 = (
        "本项目由张三负责整体管理,李四担任技术负责人,王五负责具体实施工作。"
    )
    matches = [(m.group(1), m.group(2)) for m in NAME_RE.finditer(text_c7)]
    ok = ("张三", "技术负责人") not in matches and ("李四", "技术负责人") in matches
    print(f"  [{'PASS' if ok else 'FAIL'}] case_13a_NAME_RE_no_cross_person (C7)")
    if not ok:
        print(f"           matches={matches}")
        fails += 1

    # ---- case 14: dirty_project_name 项 4 触发 [失败] 或 [警告] ----
    cases += 1
    dirty_pn_p = V39_FIXTURES / "dirty_project_name.docx"
    text_pn = extract_docx_text(dirty_pn_p)
    h1_pn = get_h1(dirty_pn_p)
    issues = check_field_consistency(brief_extracted, text_pn, h1_pn)
    ok = any("[失败]" in m or "[警告]" in m for m in issues)
    print(f"  [{'PASS' if ok else 'FAIL'}] case_14_dirty_project_name_triggered")
    if not ok:
        print(f"           issues={issues}")
        fails += 1

    # ---- case 15: dirty_resume_org 项 5 触发 [失败](人名职称冲突) ----
    cases += 1
    issues = check_resume_org_consistency(V39_FIXTURES / "dirty_resume_org.docx")
    ok = any("[失败]" in m and "张三" in m for m in issues)
    print(f"  [{'PASS' if ok else 'FAIL'}] case_15_dirty_resume_org_conflict")
    if not ok:
        print(f"           issues={issues}")
        fails += 1

    # ---- case 16: dirty_section_ref 项 6 抓段落 8.5 + 表格 cell 9.1 双覆盖 ----
    cases += 1
    issues = check_section_ref_validity(V39_FIXTURES / "dirty_section_ref.docx")
    failed_refs = [m for m in issues if "[失败]" in m]
    ok = (
        len(failed_refs) >= 2
        and any("'8.5'" in m for m in failed_refs)
        and any("'9.1'" in m for m in failed_refs)
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_16_dirty_section_ref_para_and_table")
    if not ok:
        print(f"           failed_refs={failed_refs}")
        fails += 1

    # ---- case 17: _normalize_for_token + _jaccard 单元 ----
    cases += 1
    same = _jaccard(_normalize_for_token("ABCDEFGH"), _normalize_for_token("ABCDEFGH"))
    diff = _jaccard(_normalize_for_token("ABCDEFGH"), _normalize_for_token("ZYXWVUTS"))
    partial = _jaccard(_normalize_for_token("ABCDEFGH"), _normalize_for_token("ABCDXXXX"))
    ok = same == 1.0 and diff == 0.0 and 0.0 < partial < 1.0
    print(f"  [{'PASS' if ok else 'FAIL'}] case_17_normalize_jaccard_unit")
    if not ok:
        print(f"           same={same} diff={diff} partial={partial}")
        fails += 1

    # ---- case 18: NAME_RE / REF_RE 边界 ----
    cases += 1
    # 占位符不命中
    placeholder_matches = list(NAME_RE.finditer("我方指派 【待填:项目负责人姓名】 为项目负责人。"))
    placeholder_ok = all(
        "待填" not in m.group(1) for m in placeholder_matches
    ) or len(placeholder_matches) == 0
    # REF_RE 不抓 "3.1 元"
    ref_money = list(REF_RE.finditer("保证金3.1元,详见1.2节"))
    ref_money_ok = all(m.group(1) != "3.1" for m in ref_money)
    # 同段两人名:NAME_RE 只匹配李四+技术负责人,不抓张三
    same_para = [(m.group(1), m.group(2)) for m in NAME_RE.finditer(
        "本项目由张三负责整体管理,李四担任技术负责人,王五负责具体实施工作。"
    )]
    same_para_ok = ("张三", "技术负责人") not in same_para and ("李四", "技术负责人") in same_para
    ok = placeholder_ok and ref_money_ok and same_para_ok
    print(f"  [{'PASS' if ok else 'FAIL'}] case_18_regex_edges")
    if not ok:
        print(f"           placeholder_ok={placeholder_ok} ref_money_ok={ref_money_ok} same_para_ok={same_para_ok}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
