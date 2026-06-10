# -*- coding: utf-8 -*-
"""
test_b_mode_v4_2a.py · V4-2a B 智能匹配·链路打通 测试

覆盖:
- CuratedLocalAssetsProvider.enumerate_inventory() 扫库行为 (case 1+2)
- scoring_matrix_excerpt 过滤算法 (case 3)
- inventory_match validator 抓盲写 / 通过真实命中 / 通过占位 (case 4-6)

测试目标 (plan §自检 3+4 关联):
- AI 选材落 inventory 内真实候选 (非盲写)
- 空库 / 无匹配时占位 R10 显式
- scoring_matrix_excerpt 只含本 Part 关联评分项

运行:
    ./run_script.bat tests/test_b_mode_v4_2a.py
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assets_provider import CuratedLocalAssetsProvider  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "b_mode_v4_2a"

PENDING_USER = "__PENDING_USER__"


def validate_inventory_match(manifest: dict, inventory: list[dict]) -> tuple[bool, list[str]]:
    """V4-2a inventory_match validator (R10 抓盲写).

    走遍 manifest.assembly_order 的每个 asset_query.inventory_match:
    - filename == __PENDING_USER__ → 合法占位 (PASS)
    - 否则 filename 必须在 inventory 内 → PASS
    - filename 不在 inventory 内(盲写)→ FAIL,记录违规项

    返回 (ok, violations) — violations 是字符串列表 (每条描述一处盲写)。
    """
    inventory_filenames = {entry.get("filename") for entry in inventory}
    violations: list[str] = []
    for spec in manifest.get("assembly_order", []) or []:
        aq = spec.get("asset_query") or {}
        im = aq.get("inventory_match")
        if not isinstance(im, dict):
            continue  # 没填 inventory_match 不在 validator 范围
        fn = im.get("filename")
        if fn == PENDING_USER:
            continue  # 占位, 合法
        if fn not in inventory_filenames:
            violations.append(
                f"section_id={spec.get('section_id')!r} "
                f"inventory_match.filename={fn!r} 不在 inventory 内 (盲写)"
            )
    return len(violations) == 0, violations


def _load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_inventory(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")).get("inventory", [])


def main() -> int:
    fails = 0
    cases = 0
    print("test_b_mode_v4_2a · V4-2a B 智能匹配 测试")
    print()

    inventory = _load_inventory(FIXTURES / "assets_inventory_clean.json")

    # ─── case 1: enumerate_inventory 对 tempdir 真扫返候选 + 字段 + 不含 frontmatter ───
    cases += 1
    with tempfile.TemporaryDirectory() as td:
        tmp_assets = Path(td)
        # mini 假 assets 树: 公司资质/test_co/_raw/20240101_a.docx + .pdf
        raw = tmp_assets / "公司资质" / "test_co" / "_raw"
        raw.mkdir(parents=True)
        (raw / "20240101_test_a.docx").write_bytes(b"x")
        (raw / "20231201_test_b.pdf").write_bytes(b"x")
        # 还要建一个无前缀文件验 year=null
        (raw / "no_date_c.docx").write_bytes(b"x")
        provider = CuratedLocalAssetsProvider(assets_root=tmp_assets)
        inv = provider.enumerate_inventory()
        ok_count = len(inv) == 3
        # 字段验证: 每条含 6 个键 + 不含 frontmatter 类字段
        required_keys = {"category", "company_id", "filename", "year", "path", "kind"}
        forbidden_keys = {"review_status", "颁证机构", "有效期至", "适用范围"}
        ok_keys = all(set(e.keys()) == required_keys for e in inv)
        ok_no_frontmatter = all(
            not (set(e.keys()) & forbidden_keys) for e in inv
        )
        # year 提取: 20240101 → 2024, 20231201 → 2023, no_date → None
        years = sorted([e["year"] for e in inv], key=lambda y: (y is None, y))
        ok_year = years == [2023, 2024, None]
        # kind 分流: docx → raw_docx, pdf → raw_pdf
        kinds = sorted(set(e["kind"] for e in inv))
        ok_kind = kinds == ["raw_docx", "raw_pdf"]

        case1_ok = ok_count and ok_keys and ok_no_frontmatter and ok_year and ok_kind
        icon = "PASS" if case1_ok else "FAIL"
        print(f"  [{icon}] case_1_enumerate_inventory_tempdir_scan")
        if not case1_ok:
            print(f"           count ok={ok_count} (got {len(inv)}), "
                  f"keys ok={ok_keys}, no_frontmatter ok={ok_no_frontmatter}, "
                  f"year ok={ok_year} (got {years}), kind ok={ok_kind} (got {kinds})")
            fails += 1

    # ─── case 2: enumerate_inventory 对不存在 / 空 root 返空 ───
    cases += 1
    with tempfile.TemporaryDirectory() as td:
        empty_root = Path(td) / "nonexistent_assets"
        # 不创建 empty_root 目录, 模拟不存在
        provider = CuratedLocalAssetsProvider(assets_root=empty_root)
        inv = provider.enumerate_inventory()
        case2_ok = inv == []
        icon = "PASS" if case2_ok else "FAIL"
        print(f"  [{icon}] case_2_enumerate_inventory_empty_returns_empty")
        if not case2_ok:
            print(f"           expected [], got {inv}")
            fails += 1

    # ─── case 3: scoring_matrix excerpt 过滤算法 — 只含本 Part 关联评分项 ───
    cases += 1
    csv_path = FIXTURES / "scoring_matrix_sample.csv"
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.DictReader(f))
    # fixture 设计: 4 行, 2 行归属 "其他资格证明文件", 2 行归属 "技术部分"
    target_part = "其他资格证明文件"
    filtered = [r for r in all_rows if (r.get("评分项归属") or "").strip() == target_part]
    # 应有 2 行 (营业执照与资质 / 税务社保证明)
    ok_count = len(filtered) == 2
    # 应不含 "技术部分" 的行
    other_in_filtered = any(
        (r.get("评分项归属") or "").strip() == "技术部分" for r in filtered
    )
    ok_no_other = not other_in_filtered
    # fixture 的 "证据材料" 列非空
    ok_evidence = all((r.get("证据材料") or "").strip() for r in filtered)

    case3_ok = ok_count and ok_no_other and ok_evidence
    icon = "PASS" if case3_ok else "FAIL"
    print(f"  [{icon}] case_3_scoring_matrix_excerpt_filter")
    if not case3_ok:
        print(f"           count ok={ok_count} (got {len(filtered)}), "
              f"no_other ok={ok_no_other}, evidence_filled ok={ok_evidence}")
        fails += 1

    # ─── case 4: validator 通过 good 样本 (inventory_match 真实命中) ───
    cases += 1
    good = _load_yaml(FIXTURES / "manifest_good.yaml")
    ok, violations = validate_inventory_match(good, inventory)
    case4_ok = ok and len(violations) == 0
    icon = "PASS" if case4_ok else "FAIL"
    print(f"  [{icon}] case_4_validator_passes_good_manifest")
    if not case4_ok:
        print(f"           expected pass, violations={violations}")
        fails += 1

    # ─── case 5: validator 通过 placeholder 样本 (占位 R10) ───
    cases += 1
    ph = _load_yaml(FIXTURES / "manifest_placeholder.yaml")
    ok, violations = validate_inventory_match(ph, inventory)
    case5_ok = ok and len(violations) == 0
    icon = "PASS" if case5_ok else "FAIL"
    print(f"  [{icon}] case_5_validator_passes_placeholder_manifest")
    if not case5_ok:
        print(f"           expected pass (placeholder is legal), violations={violations}")
        fails += 1

    # ─── case 6: validator 抓盲写 (manifest_bad_blind) ───
    # 这条是核心: V4-2a 修好的实证 — fail→pass 反映 "AI 从盲写变据候选选材"
    cases += 1
    bad = _load_yaml(FIXTURES / "manifest_bad_blind.yaml")
    ok, violations = validate_inventory_match(bad, inventory)
    case6_ok = (not ok) and len(violations) >= 1 and "our_company_business_license.docx" in violations[0]
    icon = "PASS" if case6_ok else "FAIL"
    print(f"  [{icon}] case_6_validator_catches_blind_write")
    if not case6_ok:
        print(f"           expected fail with 'our_company_business_license.docx' in violation, "
              f"got ok={ok}, violations={violations}")
        fails += 1

    print()
    print(f"汇总: {cases - fails} 通过 / {fails} 失败")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
