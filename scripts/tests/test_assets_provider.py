# -*- coding: utf-8 -*-
"""
test_assets_provider.py · CuratedLocalAssetsProvider 单元测试(V3-1)

覆盖函数:
- map_asset_type_to_category(_asset_type_mapping)  ★ happy path: case 12
- CuratedLocalAssetsProvider._scan_candidates  ★ happy path: case 1
- CuratedLocalAssetsProvider.lookup  ★ happy path: case 7
- CuratedLocalAssetsProvider._choose(交互 + 非交互)
- CuratedLocalAssetsProvider.resolve(docx 主路径)

测试目标:
    1. 0/1/多 命中边界
    2. year_filter 过滤(>=YYYY / 单年)
    3. lookup 多命中走 stdin 交互(monkey-patch sys.stdin)
    4. lookup 多命中 + non_interactive → 按 latest_year_first 自动选
    5. resolve docx 主路径返回真实 path
    6. asset_type 映射(精确 / 回退 / 兜底)

不测 pdf2docx 路径(可选依赖,fixture 不放 pdf 避免依赖缠绕)。

运行:
    ./run_script.bat tests/test_assets_provider.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assets_provider import (  # noqa: E402
    CuratedLocalAssetsProvider,
    AssetRef,
)
from _asset_type_mapping import map_asset_type_to_category  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "assets_provider"
TEST_MAPPING = FIXTURES / "asset_type_mapping.yaml"


def make_provider(non_interactive: bool = False) -> CuratedLocalAssetsProvider:
    return CuratedLocalAssetsProvider(
        assets_root=FIXTURES,
        company_id="company_a",
        non_interactive=non_interactive,
        mapping_path=TEST_MAPPING,
    )


def main() -> int:
    fails = 0
    cases = 0
    print("CuratedLocalAssetsProvider 测试")
    print()

    # ---- case 1: _scan_candidates 资质证书 → 3 candidates (happy path) ----
    cases += 1
    p = make_provider()
    cands = p._scan_candidates("资质证书")
    ok = (
        len(cands) == 3
        and all(c.metadata["kind"] == "raw_docx" for c in cands)
        and all(not c.is_placeholder for c in cands)
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_scan_3_docx (happy path)")
    if not ok:
        print(f"           candidates: {[c.metadata.get('filename') for c in cands]}")
        fails += 1

    # ---- case 2: 未映射 asset_type → 0 candidates ----
    cases += 1
    cands = p._scan_candidates("不存在类型")
    ok = cands == []
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_unmapped_returns_empty")
    if not ok:
        print(f"           cands={cands}")
        fails += 1

    # ---- case 3: 1 命中(团队简历)----
    cases += 1
    cands = p._scan_candidates("团队简历")
    ok = len(cands) == 1
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_scan_one_match")
    if not ok:
        print(f"           cands={[c.metadata for c in cands]}")
        fails += 1

    # ---- case 4: year_filter >= 2025 → 2 candidates(过滤 2024)----
    cases += 1
    cands = p._scan_candidates("资质证书", year_filter=">=2025")
    years = sorted(c.metadata.get("year") for c in cands)
    ok = years == [2025, 2025]
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_year_filter_ge")
    if not ok:
        print(f"           years={years}")
        fails += 1

    # ---- case 5: year_filter 单年 2024 → 1 candidate ----
    cases += 1
    cands = p._scan_candidates("资质证书", year_filter="2024")
    ok = len(cands) == 1 and cands[0].metadata.get("year") == 2024
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_year_filter_single")
    if not ok:
        print(f"           cands={[c.metadata for c in cands]}")
        fails += 1

    # ---- case 6: lookup 0 命中 → placeholder AssetRef ----
    cases += 1
    ref = p.lookup("不存在类型")
    ok = ref.is_placeholder is True and "0 命中" in ref.metadata.get("reason", "")
    print(f"  [{'PASS' if ok else 'FAIL'}] case_6_lookup_zero_returns_placeholder")
    if not ok:
        print(f"           ref={ref}")
        fails += 1

    # ---- case 7: lookup 1 命中 → 直接返回 (happy path) ----
    cases += 1
    ref = p.lookup("团队简历")
    ok = (
        ref.is_placeholder is False
        and "source_path" in ref.metadata
        and Path(ref.metadata["source_path"]).exists()
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_7_lookup_one_returns_real (happy path)")
    if not ok:
        print(f"           ref={ref}")
        fails += 1

    # ---- case 8: lookup 多命中 + monkey-patch stdin → 用户输入 "1" 选第 1 个 ----
    cases += 1
    p_tty = make_provider(non_interactive=False)
    saved_stdin = sys.stdin
    saved_isatty = sys.stdin.isatty
    try:
        # 模拟 tty 环境 + 用户输入
        fake_stdin = io.StringIO("1\n")
        fake_stdin.isatty = lambda: True
        sys.stdin = fake_stdin
        ref = p_tty.lookup("资质证书")
        ok = ref.is_placeholder is False and "source_path" in ref.metadata
        # 第一个是按 sorted name → 20240601_iso27001.docx
        first_name = "20240601_iso27001.docx"
        ok = ok and ref.metadata.get("filename") == first_name
        print(f"  [{'PASS' if ok else 'FAIL'}] case_8_lookup_multi_interactive_choice")
        if not ok:
            print(f"           ref={ref}")
            fails += 1
    finally:
        sys.stdin = saved_stdin

    # ---- case 9: lookup 多命中 + non_interactive → 按 latest_year_first ----
    cases += 1
    p_ni = make_provider(non_interactive=True)
    ref = p_ni.lookup("资质证书")
    ok = (
        ref.is_placeholder is False
        and ref.metadata.get("year") == 2025  # 最新年份
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_9_lookup_multi_non_interactive")
    if not ok:
        print(f"           ref={ref}")
        fails += 1

    # ---- case 10: resolve docx → 返回真实 path ----
    cases += 1
    ref = p.lookup("团队简历")
    resolved = p.resolve(ref)
    ok = resolved.exists() and resolved.suffix == ".docx"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_10_resolve_docx_returns_real_path")
    if not ok:
        print(f"           resolved={resolved}")
        fails += 1

    # ---- case 11: resolve placeholder → 走 PlaceholderAssetsProvider 兜底 ----
    cases += 1
    ph_ref = AssetRef(
        asset_type="未知类型",
        is_placeholder=True,
        lookup_key="test|miss",
        metadata={"reason": "test"},
    )
    resolved = p.resolve(ph_ref)
    ok = resolved.exists() and resolved.suffix == ".docx"
    print(f"  [{'PASS' if ok else 'FAIL'}] case_11_resolve_placeholder_fallback")
    if not ok:
        print(f"           resolved={resolved}")
        fails += 1

    # ---- case 12: map_asset_type_to_category 映射规则 (happy path) ----
    cases += 1
    cat1 = map_asset_type_to_category("资质证书", "", mapping_path=TEST_MAPPING)
    cat2 = map_asset_type_to_category("", "简历", mapping_path=TEST_MAPPING)
    cat3 = map_asset_type_to_category("未知", "未知", mapping_path=TEST_MAPPING)
    cat4 = map_asset_type_to_category("营业执照", "业绩", mapping_path=TEST_MAPPING)
    ok = (
        cat1 == "公司资质"
        and cat2 == "团队简历"
        and cat3 == "__placeholder__"
        and cat4 == "公司资质"  # 精确匹配优先
    )
    print(f"  [{'PASS' if ok else 'FAIL'}] case_12_map_asset_type_to_category (happy path)")
    if not ok:
        print(f"           cat1={cat1}, cat2={cat2}, cat3={cat3}, cat4={cat4}")
        fails += 1

    print()
    print(f"总结:{cases - fails} 通过 / {fails} 失败  (共 {cases} 个 case)")
    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
