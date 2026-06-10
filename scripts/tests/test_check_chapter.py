# -*- coding: utf-8 -*-
"""
test_check_chapter.py · check_chapter 单元测试(V3-4)

覆盖函数:
- check_content_keyword_stitching ★ happy path: case 1
  - 7 关键词压一句 → fail
  - 5 关键词压一句 → warn
  - 4 关键词散布(用户原型反例)→ pass
  - 列表枚举 / 表格 / nolint 注释 → pass(skip 规则)
  - 自然段 keywords 稀疏 → pass

阈值默认 warn=5 / fail=6 / window=30(plan 初值 4/5,demo 烟测调到 5/6)。

运行:
    ./run_script.bat tests/test_check_chapter.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from check_chapter import check_content_keyword_stitching  # noqa: E402


# 测试用 matrix_rows fixture(7 个评分项关键词)
TEST_MATRIX = [
    {"评分项": "项目管理", "关键词": "审核;质量管理体系;工作程序;风险控制;标准方法;制度;保障"},
]


def main() -> int:
    fails = 0
    cases = 0
    print("check_chapter / check_content_keyword_stitching 测试")
    print()

    # ---- case 1: 7 关键词压一句 → fail (happy path) ----
    cases += 1
    text = "本方案审核质量管理体系工作程序风险控制标准方法制度保障措施全部落实"
    status, detail = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "fail" and "失败" in detail
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_seven_kws_fail (happy path)")
    if not ok:
        print(f"           status={status}, detail={detail[:120]}")
        fails += 1

    # ---- case 2: 5 关键词压一句 → warn ----
    cases += 1
    text = "本方案审核质量管理体系工作程序风险控制标准方法"
    status, detail = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "warn" and "警告" in detail
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_five_kws_warn")
    if not ok:
        print(f"           status={status}, detail={detail[:120]}")
        fails += 1

    # ---- case 3: 用户原型(4 关键词散布)→ pass ----
    cases += 1
    # 用户审 plan 时举的反例:"质量管理体系覆盖审核工作程序"——4 关键词合规专业表述
    text = "质量管理体系覆盖审核标准方法工作程序"
    status, _ = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "pass"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_user_archetype_4kws_pass")
    if not ok:
        print(f"           status={status}(预期 pass,< 5 warn 阈值)")
        fails += 1

    # ---- case 4: 列表枚举 → pass(skip 规则) ----
    cases += 1
    text = "- 审核\n- 质量管理体系\n- 工作程序\n- 风险控制\n- 标准方法\n- 制度\n- 保障"
    status, _ = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "pass"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_list_skip_pass")
    if not ok:
        print(f"           status={status}(预期 pass,列表行被 skip)")
        fails += 1

    # ---- case 5: 表格行 → pass(skip 规则) ----
    cases += 1
    text = "| 审核 | 质量管理体系 | 工作程序 | 风险控制 | 标准方法 |"
    status, _ = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "pass"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_table_skip_pass")
    if not ok:
        print(f"           status={status}(预期 pass,表格行被 skip)")
        fails += 1

    # ---- case 6: 自然段落 keywords 稀疏 → pass ----
    cases += 1
    text = "我们坚持高质量交付,严格审核每个交付环节,确保按时完成。"
    status, _ = check_content_keyword_stitching(text, TEST_MATRIX)
    ok = status == "pass"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_6_natural_low_density_pass")
    if not ok:
        print(f"           status={status}(预期 pass,只 1 关键词)")
        fails += 1

    # ---- case 7: nolint 注释跳过下一段 → pass ----
    cases += 1
    # 没有 nolint 时这段是 fail(7 关键词);加 nolint 后被跳过 → pass
    text_with_nolint = (
        "<!-- nolint:stitching -->\n"
        "本方案审核质量管理体系工作程序风险控制标准方法制度保障措施"
    )
    status, _ = check_content_keyword_stitching(text_with_nolint, TEST_MATRIX)
    ok = status == "pass"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_7_nolint_skip_pass")
    if not ok:
        print(f"           status={status}(预期 pass,nolint 跳过下段)")
        fails += 1

    # ---- case 8: nolint 边界 - 跳过第一段不跳第二段 ----
    cases += 1
    # nolint 后跳第一段(7 keywords);第二段(7 keywords)无 nolint → fail
    text_two_paras = (
        "<!-- nolint:stitching -->\n"
        "本方案审核质量管理体系工作程序风险控制标准方法制度保障措施\n"
        "本方案审核质量管理体系工作程序风险控制标准方法制度保障措施"
    )
    status, _ = check_content_keyword_stitching(text_two_paras, TEST_MATRIX)
    ok = status == "fail"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_8_nolint_boundary")
    if not ok:
        print(f"           status={status}(预期 fail,nolint 仅跳过第 1 段)")
        fails += 1

    # ---- case 9: 空 matrix_rows → 无关键词 → warn(跳过检测)----
    cases += 1
    status, detail = check_content_keyword_stitching("任何文本", [])
    ok = status == "warn" and "无关键词" in detail
    print(f"  [{'PASS' if ok else 'FAIL'}] case_9_empty_matrix_warn")
    if not ok:
        print(f"           status={status}, detail={detail[:80]}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
