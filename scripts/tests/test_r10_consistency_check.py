# -*- coding: utf-8 -*-
"""
test_r10_consistency_check.py · R10 扫描脚本回归测试

覆盖函数:
- run_scan(root, allowlist_path) -> (violations, report)
- index_constants(root)
- index_business_model_anchors(root)

测试目标:
    1. clean fixture: 0 violations (happy path)
    2. dirty fixture: 4 violations (path / const / anchor / section) 各 1
    3. allowlist self_ref_files: 同文件自指不报
    4. allowlist paths: 占位路径不报
    5. const_index 命中常量定义
    6. anchor_index 命中 §X #NXX

运行:
    ./run_script.bat tests/test_r10_consistency_check.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from r10_consistency_check import (  # noqa: E402
    run_scan,
    index_constants,
    index_business_model_anchors,
)

FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'r10_consistency_check'
CLEAN_ROOT = FIXTURES / 'clean'
DIRTY_ROOT = FIXTURES / 'dirty'


def main() -> int:
    fails = 0
    cases = 0
    print('r10_consistency_check 测试')
    print()

    # ─── case 1: clean fixture 0 violations (happy path) ───
    cases += 1
    violations, _ = run_scan(CLEAN_ROOT, allowlist_path=None)
    ok = len(violations) == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] case_1_clean_zero_violations (happy path)")
    if not ok:
        print(f"           expected 0, got {len(violations)}")
        for v in violations:
            print(f"             - [{v['type']}] {v['file']}:{v['line']} {v['ref']}")
        fails += 1

    # ─── case 2: dirty fixture: 4 violations, 4 types ───
    cases += 1
    violations, _ = run_scan(DIRTY_ROOT, allowlist_path=None)
    types = {v['type'] for v in violations}
    expected_types = {'path_ref', 'const_ref', 'business_model_anchor',
                      'business_model_section'}
    ok = expected_types.issubset(types)
    print(f"  [{'PASS' if ok else 'FAIL'}] case_2_dirty_all_four_types_detected")
    if not ok:
        print(f"           expected types {expected_types}, got {types}")
        for v in violations:
            print(f"             - [{v['type']}] {v['file']}:{v['line']} {v['ref']}")
        fails += 1

    # ─── case 3: dirty fixture: violations 行号精确 (L9-12 in bad_refs.py) ───
    cases += 1
    # 注: bad_refs.py L9-12 = 4 行注释, 每行 1 类违规
    bad_ref_violations = [
        v for v in violations if v['file'].endswith('bad_refs.py')
    ]
    lines = sorted({v['line'] for v in bad_ref_violations})
    ok = lines == [9, 10, 11, 12]
    print(f"  [{'PASS' if ok else 'FAIL'}] case_3_dirty_line_numbers_precise")
    if not ok:
        print(f"           expected lines [9,10,11,12], got {lines}")
        for v in bad_ref_violations:
            print(f"             - [{v['type']}] L{v['line']} {v['ref']}")
        fails += 1

    # ─── case 4: const_index 命中 valid_module.VALID_CONST ───
    cases += 1
    idx = index_constants(CLEAN_ROOT)
    ok = 'valid_module' in idx and 'VALID_CONST' in idx['valid_module']
    print(f"  [{'PASS' if ok else 'FAIL'}] case_4_const_index_hit")
    if not ok:
        print(f"           const_index={idx}")
        fails += 1

    # ─── case 5: anchor_index 命中 §8 #N20 ───
    cases += 1
    with_n, sections = index_business_model_anchors(CLEAN_ROOT)
    ok = ('8', '20') in with_n and '8' in sections
    print(f"  [{'PASS' if ok else 'FAIL'}] case_5_anchor_index_hit")
    if not ok:
        print(f"           with_n={with_n}, sections={sections}")
        fails += 1

    # ─── case 6: allowlist self_ref_files 同文件自指不报 ───
    cases += 1
    # 临时建一个 fixture: docs/changelog.md 自指 docs/changelog.md
    with tempfile.TemporaryDirectory() as td:
        tmp_root = Path(td)
        (tmp_root / 'docs').mkdir()
        # 文件内容: 自指本身 + 引一个不存在的非自指路径
        changelog = tmp_root / 'docs' / 'changelog.md'
        changelog.write_text(
            '# changelog\n\n'
            '本文档自身: 见 docs/changelog.md (自指, allowlist 放行)\n'
            '非自指坏路径: 见 docs/nonexistent_path.md\n',
            encoding='utf-8'
        )
        # 写 allowlist
        allow = tmp_root / 'allow.yaml'
        allow.write_text(
            'self_ref_files:\n'
            '  - docs/changelog.md\n',
            encoding='utf-8'
        )
        vs, _ = run_scan(tmp_root, allowlist_path=allow)
        # 期望: 仅 nonexistent_path.md 1 处违规, 自指被放行
        nonexistent_count = sum(1 for v in vs if 'nonexistent_path' in v['ref'])
        self_ref_count = sum(1 for v in vs if 'changelog' in v['ref'])
        ok = nonexistent_count == 1 and self_ref_count == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] case_6_allowlist_self_ref")
        if not ok:
            print(f"           nonexistent={nonexistent_count}, self_ref={self_ref_count}")
            for v in vs:
                print(f"             - [{v['type']}] {v['file']}:{v['line']} {v['ref']}")
            fails += 1

    # ─── case 7: allowlist paths 占位路径放行 ───
    cases += 1
    with tempfile.TemporaryDirectory() as td:
        tmp_root = Path(td)
        (tmp_root / 'scripts').mkdir()
        py = tmp_root / 'scripts' / 'demo.py'
        py.write_text(
            '# 占位路径: projects/{项目名}/output/x.json\n'
            '# 真违规: projects/real_nonexistent/foo.json\n',
            encoding='utf-8'
        )
        allow = tmp_root / 'allow.yaml'
        allow.write_text(
            'paths:\n'
            "  - 'projects/{项目名}/*'\n",
            encoding='utf-8'
        )
        vs, _ = run_scan(tmp_root, allowlist_path=allow)
        # 占位 projects/{项目名}/x.json 含 {} 会被脚本内置 {} 检测放行
        # 真违规 projects/real_nonexistent/foo.json 应被抓
        placeholder_caught = any('{' in v['ref'] for v in vs)
        real_caught = any('real_nonexistent' in v['ref'] for v in vs)
        ok = (not placeholder_caught) and real_caught
        print(f"  [{'PASS' if ok else 'FAIL'}] case_7_allowlist_placeholder")
        if not ok:
            print(f"           placeholder={placeholder_caught}, real={real_caught}")
            fails += 1

    # ─── case 8: 误报率盲区维度 (v2 V4-0.2 commit 6b 新增) ───
    # 验扫描器不抓"看起来像违规但其实合法"的样本: 元变量占位 / 跨仓引用 / glob
    # 字面源在 clean/scripts/legitimate_lookalikes.py
    cases += 1
    violations, _ = run_scan(CLEAN_ROOT, allowlist_path=None)
    # 任何来自 legitimate_lookalikes.py 的违规都算 case 8 失败
    lookalike_violations = [
        v for v in violations if 'legitimate_lookalikes' in v['file']
    ]
    ok = len(lookalike_violations) == 0
    print(f"  [{'PASS' if ok else 'FAIL'}] case_8_false_positive_blindspot "
          f"(元变量/跨仓/glob 合法样本不误抓)")
    if not ok:
        print(f"           expected 0 from legitimate_lookalikes.py, "
              f"got {len(lookalike_violations)}")
        for v in lookalike_violations:
            print(f"             - [{v['type']}] L{v['line']} {v['ref']}")
        fails += 1

    # ─── 汇总 ───
    print()
    print(f"汇总: {cases - fails} 通过 / {fails} 失败")
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main())
