# -*- coding: utf-8 -*-
"""
test_parse_tender.py · parse_tender 回归测试

覆盖函数:
- normalize_text(text)
- extract_raw_lines_with_features(text)  ★ happy path: case 3
- extract_section_by_anchors(text, anchors)  ★ happy path: case 6
- extract_substantial_marks(text)  ★ happy path: case 7
- extract_score_items_raw_positions(text, anchors)  ★ happy path: case 9

测试目标:
    1. 文本预处理:多空白压缩 + 多换行压缩
    2. 行特征:is_standalone / has_chapter_num / has_dots_leader 三类标签
    3. 章节切片按 anchors 切
    4. ★▲ 标记抽取
    5. 评审办法范围内按 (N分) 切位置

运行:
    ./run_script.bat tests/test_parse_tender.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from parse_tender import (  # noqa: E402
    normalize_text,
    extract_raw_lines_with_features,
    extract_section_by_anchors,
    extract_substantial_marks,
    extract_score_items_raw_positions,
    read_pdf,
    ScannedPdfDetected,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "parse_tender"
TEXT_PDF = FIXTURES / "text_pdf_naturalsci.pdf"
SCANNED_PDF = FIXTURES / "scanned_synthetic.pdf"
SCANNED_FALLBACK = FIXTURES / "scanned_fallback.txt"


def main() -> int:
    fails = 0
    cases = 0
    print("parse_tender 测试")
    print()

    # ---- case 1: normalize_text 多空白压缩 ----
    cases += 1
    actual = normalize_text("测试   多  空格")
    expected = "测试 多 空格"
    ok = actual == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_normalize_collapse_spaces")
    if not ok:
        print(f"           expected: {expected!r}")
        print(f"           actual:   {actual!r}")
        fails += 1

    # ---- case 2: normalize_text 多换行压缩 ----
    cases += 1
    actual = normalize_text("行1\n\n\n\n行2")
    expected = "行1\n\n行2"
    ok = actual == expected
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_normalize_collapse_newlines")
    if not ok:
        print(f"           expected: {expected!r}")
        print(f"           actual:   {actual!r}")
        fails += 1

    # ---- case 3: extract_raw_lines_with_features 短行 vs 长行 (happy path)----
    cases += 1
    text = "短行\n这是一个长度刻意超过六十个字符的长行,目的是验证 is_standalone 在超长行上的反向判定逻辑确实生效不会被误判为短独立行,需要超过六十"
    rows = extract_raw_lines_with_features(text)
    ok = (
        len(rows) == 2
        and rows[0]["is_standalone"] is True
        and rows[0]["text"] == "短行"
        and rows[1]["is_standalone"] is False
        and rows[1]["length"] > 60
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_features_standalone (happy path)")
    if not ok:
        print(f"           rows: {rows}")
        fails += 1

    # ---- case 4: has_chapter_num ----
    cases += 1
    rows = extract_raw_lines_with_features("第三章 评审办法")
    ok = len(rows) == 1 and rows[0]["has_chapter_num"] is True
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_features_chapter_num")
    if not ok:
        print(f"           rows: {rows}")
        fails += 1

    # ---- case 5: has_dots_leader ----
    cases += 1
    rows = extract_raw_lines_with_features("目录...........5")
    ok = len(rows) == 1 and rows[0]["has_dots_leader"] is True
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_features_dots_leader")
    if not ok:
        print(f"           rows: {rows}")
        fails += 1

    # ---- case 6: extract_section_by_anchors (happy path)----
    cases += 1
    text = "L0\nL1\nL2\nL3\nL4\nL5\nL6\nL7\nL8\nL9"
    anchors = [{"section": "评审办法", "start_line": 5, "end_line": 10}]
    sections = extract_section_by_anchors(text, anchors)
    ok = (
        "评审办法" in sections
        and sections["评审办法"]["start"] == 5
        and sections["评审办法"]["end"] == 10
        and sections["评审办法"]["content"] == "L5\nL6\nL7\nL8\nL9"
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_6_section_by_anchors_slice (happy path)")
    if not ok:
        print(f"           sections: {sections}")
        fails += 1

    # ---- case 7: extract_substantial_marks 从 fixture 文件 (happy path)----
    cases += 1
    with_marks_text = (FIXTURES / "with_marks.txt").read_text(encoding="utf-8")
    marks = extract_substantial_marks(with_marks_text)
    line_nos = [m["line_no"] for m in marks]
    ok = (
        len(marks) == 4
        and line_nos == sorted(line_nos)  # 单调递增
        and all(("★" in m["text"]) or ("▲" in m["text"]) for m in marks)
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_7_substantial_marks_from_fixture (happy path)")
    if not ok:
        print(f"           marks: {marks}")
        fails += 1

    # ---- case 8: extract_substantial_marks 边界(无标记)----
    cases += 1
    marks = extract_substantial_marks("纯文本无任何标记符号")
    ok = marks == []
    print(f"  [{'PASS' if ok else 'FAIL'}] case_8_substantial_marks_empty")
    if not ok:
        print(f"           marks: {marks}")
        fails += 1

    # ---- case 9: extract_score_items_raw_positions (happy path)----
    cases += 1
    score_text = (
        "第三章 评审办法\n"
        "\n"
        "(20分)项目管理体系\n"
        "评审依据:制度文件\n"
        "\n"
        "(15分)技术方案\n"
        "评审依据:架构图\n"
    )
    # lines[0..7]; 评审办法范围 0..7;match 在 line 2 和 line 5
    score_anchors = [{"section": "评审办法", "start_line": 0, "end_line": 7}]
    positions = extract_score_items_raw_positions(score_text, score_anchors)
    ok = (
        len(positions) == 2
        and positions[0]["start_line"] == 2
        and positions[1]["start_line"] == 5
        and "(20分)" in positions[0]["raw_text"]
        and "(15分)" in positions[1]["raw_text"]
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_9_score_items_raw_positions (happy path)")
    if not ok:
        print(f"           positions: {positions}")
        fails += 1

    # ---- case 10: extract_score_items_raw_positions 缺评审办法 anchor ----
    cases += 1
    positions = extract_score_items_raw_positions("无关文本", [])
    ok = positions == []
    print(f"  [{'PASS' if ok else 'FAIL'}] case_10_score_items_no_anchor_fallback")
    if not ok:
        print(f"           positions: {positions}")
        fails += 1

    # ==== V3-6 扫描版 PDF 检测 case 11-15 ====

    # ---- case 11: 文字版 PDF (text_pdf_naturalsci) → 不误报,正常返回非空字符串 ----
    cases += 1
    text = read_pdf(TEXT_PDF)
    ok = isinstance(text, str) and len(text) > 20000
    print(f"  [{'PASS' if ok else 'FAIL'}] case_11_text_pdf_naturalsci_passes")
    if not ok:
        print(f"           len(text)={len(text) if isinstance(text, str) else 'not-str'}")
        fails += 1

    # ---- case 12: 扫描版 PDF 无 fallback → 抛 ScannedPdfDetected ----
    cases += 1
    raised = False
    err_attrs = None
    try:
        read_pdf(SCANNED_PDF)
    except ScannedPdfDetected as e:
        raised = True
        err_attrs = (e.n_pages, e.total_chars, e.avg_per_page)
    ok = raised and err_attrs == (4, 0, 0.0)
    print(f"  [{'PASS' if ok else 'FAIL'}] case_12_scanned_pdf_raises_without_fallback")
    if not ok:
        print(f"           raised={raised}, attrs={err_attrs}")
        fails += 1

    # ---- case 13: 扫描版 PDF + fallback txt → 走 txt 内容 ----
    cases += 1
    text = read_pdf(SCANNED_PDF, ocr_fallback_txt=SCANNED_FALLBACK)
    expected_marker = "TC250E06T-V3-6-FIXTURE"
    ok = isinstance(text, str) and expected_marker in text
    print(f"  [{'PASS' if ok else 'FAIL'}] case_13_scanned_pdf_with_fallback_returns_txt")
    if not ok:
        print(f"           len={len(text) if isinstance(text, str) else 'not-str'}, "
              f"marker_in_text={expected_marker in text if isinstance(text, str) else 'N/A'}")
        fails += 1

    # ---- case 14: 扫描版 PDF + 不存在的 fallback 路径 → SystemExit(1) ----
    cases += 1
    nonexist = FIXTURES / "_no_such_fallback.txt"
    exit_code = None
    try:
        read_pdf(SCANNED_PDF, ocr_fallback_txt=nonexist)
    except SystemExit as e:
        exit_code = e.code
    ok = exit_code == 1
    print(f"  [{'PASS' if ok else 'FAIL'}] case_14_missing_fallback_exits_1")
    if not ok:
        print(f"           exit_code={exit_code}")
        fails += 1

    # ---- case 15: 阈值边界单元 (mock pdfplumber.open) ----
    cases += 1
    from unittest.mock import patch, MagicMock

    def _make_fake_pdfplumber(page_texts):
        cm = MagicMock()
        pages = [MagicMock() for _ in page_texts]
        for p, t in zip(pages, page_texts):
            p.extract_text.return_value = t
        cm.__enter__.return_value.pages = pages
        return cm

    sub_results = {}

    # avg=49 (10 页 × 49 字 = 490 总字符,avg<50 触发) → 扫描版
    with patch("pdfplumber.open", return_value=_make_fake_pdfplumber([" " * 49] * 10)):
        try:
            read_pdf(Path("mock.pdf"))
            sub_results["avg_49"] = False
        except ScannedPdfDetected:
            sub_results["avg_49"] = True

    # avg=51 (10 页 × 51 = 510 总字符,avg≥50 且 total≥100) → 文字版
    with patch("pdfplumber.open", return_value=_make_fake_pdfplumber(["a" * 51] * 10)):
        try:
            result = read_pdf(Path("mock.pdf"))
            sub_results["avg_51"] = isinstance(result, str) and len(result) > 0
        except ScannedPdfDetected:
            sub_results["avg_51"] = False

    # total<100 兜底 (2 页 × 40 = 80,avg=40 也 <50,但兜底也命中) → 扫描版
    with patch("pdfplumber.open", return_value=_make_fake_pdfplumber(["a" * 40] * 2)):
        try:
            read_pdf(Path("mock.pdf"))
            sub_results["total_lt_100"] = False
        except ScannedPdfDetected:
            sub_results["total_lt_100"] = True

    # 0 页 → 扫描版
    with patch("pdfplumber.open", return_value=_make_fake_pdfplumber([])):
        try:
            read_pdf(Path("mock.pdf"))
            sub_results["zero_pages"] = False
        except ScannedPdfDetected:
            sub_results["zero_pages"] = True

    ok = all(sub_results.values())
    print(f"  [{'PASS' if ok else 'FAIL'}] case_15_threshold_boundary_units")
    if not ok:
        print(f"           sub_results={sub_results}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
