# -*- coding: utf-8 -*-
"""
b_mode_extract.py · B 模式材料组装清单产出(V61)

职责:读 tender_brief.json 筛 production_mode=B 的 Part,按 source_anchor 取原文,
产出 manifest.yaml(含 assembly_order,AI 判 source_type)。

不做:内容抽取、资产查找、版本管理。

用法:
    # Step 1-2: 提取原文到 raw.txt
    python scripts/b_mode_extract.py --project <项目> --part <N> --extract-text

    # Step 3.5: 从人工/AI 产出的 intermediate.json 构建 manifest.yaml
    python scripts/b_mode_extract.py --project <项目> --part <N> \\
        --build-from-json <intermediate.json 路径>
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖,请先双击 install.bat 安装依赖。", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent


def _safe_name(name: str) -> str:
    s = re.sub(r'^[一二三四五六七八九十\d]+[、.]\s*', '', name)
    s = re.sub(r'[（(].+?[)）]', '', s)
    s = s.strip()
    return s or 'part'


def load_brief(project_dir: Path) -> dict:
    brief_path = project_dir / 'output' / 'tender_brief.json'
    if not brief_path.exists():
        print(f"[错误] 找不到 tender_brief.json: {brief_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(brief_path.read_text(encoding='utf-8'))


def get_b_part(brief: dict, part_index: int) -> dict:
    parts = brief.get('response_file_parts', [])
    if part_index < 0 or part_index >= len(parts):
        print(f"[错误] --part {part_index} 超出范围(0..{len(parts)-1})", file=sys.stderr)
        sys.exit(1)
    part = parts[part_index]
    if part.get('production_mode') != 'B':
        print(f"[错误] Part[{part_index}] '{part.get('name')}' 的 production_mode "
              f"是 {part.get('production_mode')},不是 B。", file=sys.stderr)
        sys.exit(1)
    return part


def cmd_extract_text(args, project_dir: Path):
    # V53: 未 review 则硬失败
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from brief_schema import resolve_source_anchor, validate_source_anchor, validate_response_part_b

    brief = load_brief(project_dir)
    part = get_b_part(brief, args.part)
    validate_response_part_b(part)

    part_dir_name = _safe_name(part['name'])
    out_dir = project_dir / 'output' / 'b_mode' / part_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    anchor = part.get('source_anchor')
    try:
        anchor_type = validate_source_anchor(anchor)
        resolved = resolve_source_anchor(brief, anchor)
    except ValueError as e:
        print(f"[错误] source_anchor 校验失败: {e}", file=sys.stderr)
        sys.exit(1)

    # V4-2a: 同时产 scoring_matrix_excerpt.md (本 Part 关联评分项的关键词 +
    # 证据材料) + assets_inventory.json (库内候选清单), 供 AI 写
    # intermediate.json 时 awareness 选材。详见函数末尾 sidecar 写盘。
    raw_path = out_dir / 'raw.txt'
    if anchor_type == 'text':
        text = '\n'.join(t for _, t in resolved)
    else:
        # table 型:按 table 渲染(B 模式当前项目无此场景,预留)
        sections = []
        for t in resolved:
            lines = [f"# table_id: {t['table_id']}"]
            lines.append('| ' + ' | '.join(t['headers']) + ' |')
            for row in t['rows']:
                lines.append('| ' + ' | '.join(row) + ' |')
            sections.append('\n'.join(lines))
        text = '\n\n'.join(sections)
    raw_path.write_text(text, encoding='utf-8')

    # ── V4-2a sidecar 1: scoring_matrix_excerpt.md ──
    # 从 output/scoring_matrix.csv 过滤 评分项归属 == part['name'] 的行,
    # 渲染 markdown 表 (评分项 / 分值 / 关键词 / 证据材料 四列)。
    # CSV 不存在时产空表 + 注明 (不报错; 阶段 1 后阶段 2 跑过即有 CSV)。
    excerpt_path = out_dir / 'scoring_matrix_excerpt.md'
    csv_path = project_dir / 'output' / 'scoring_matrix.csv'
    excerpt_lines = [f"# scoring_matrix 评分项摘录 · Part: {part['name']}", ""]
    if not csv_path.exists():
        excerpt_lines.append("> 注:scoring_matrix.csv 尚未生成 (需先跑阶段 2 "
                             "build_scoring_matrix.py)。")
        excerpt_lines.append("> AI 写 intermediate.json 时无评分项参考,"
                             "仅凭 raw.txt + assets_inventory 选材。")
    else:
        with open(csv_path, 'r', encoding='utf-8-sig', newline='') as f:
            rows = [r for r in csv.DictReader(f)
                    if (r.get('评分项归属') or '').strip() == part['name']]
        if not rows:
            excerpt_lines.append(f"> 注:scoring_matrix 中无 评分项归属 == "
                                 f"'{part['name']}' 的行。本 Part 无关联评分项。")
        else:
            excerpt_lines.append(f"本 Part 关联 {len(rows)} 条评分项:")
            excerpt_lines.append("")
            excerpt_lines.append("| 评分项 | 分值 | 关键词 | 证据材料 |")
            excerpt_lines.append("|---|---|---|---|")
            for r in rows:
                cells = [
                    (r.get('评分项') or '').replace('|', '\\|'),
                    (r.get('分值') or '').replace('|', '\\|'),
                    (r.get('关键词') or '').replace('|', '\\|'),
                    (r.get('证据材料') or '').replace('|', '\\|'),
                ]
                excerpt_lines.append('| ' + ' | '.join(cells) + ' |')
    excerpt_path.write_text('\n'.join(excerpt_lines) + '\n', encoding='utf-8')

    # ── V4-2a sidecar 2: assets_inventory.json ──
    # 调 CuratedLocalAssetsProvider.enumerate_inventory() 扫库, 写盘供 AI awareness。
    # 不读 frontmatter (留 V4-2b)。assets/ 目录不存在 → 产空 inventory + 标注。
    inventory_path = out_dir / 'assets_inventory.json'
    from assets_provider import CuratedLocalAssetsProvider
    inventory = CuratedLocalAssetsProvider().enumerate_inventory()
    inventory_path.write_text(
        json.dumps({"inventory": inventory, "size": len(inventory)},
                   ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    print(f"[完成] Part[{args.part}] '{part['name']}' 原文已写入: {raw_path}")
    print(f"[完成] V4-2a sidecar: {excerpt_path} (本 Part 评分项摘录)")
    print(f"[完成] V4-2a sidecar: {inventory_path} (库内候选 {len(inventory)} 条)")
    print()
    print("=" * 60)
    print("下一步(Step 3):AI 写 intermediate.json 必须读三件源 (V4-2a):")
    print("  (a) raw.txt                        ← 招标文件原文片段")
    print("  (b) scoring_matrix_excerpt.md      ← 本 Part 关联评分项关键词 + 证据材料")
    print("  (c) assets_inventory.json          ← 库内候选清单 (filename/company_id/year)")
    print("AI 在 asset_query 字段写 inventory_match (从候选清单选中的真实条目);")
    print("库内无匹配候选时 inventory_match 标占位 (__PENDING_USER__), 不盲写不存在的 name。")
    print()
    print("  (prompt 字面见 docs/business_model_v1.md §8 #N21;原 brief_schema.B_MODE_EXTRACT_PROMPT")
    print("   常量已在 v1 P2 清理中删除,迁移到 business_model §8 #N21)")
    print()
    print("intermediate.json 结构:")
    print("  {")
    print('    "part_name": "...",')
    print('    "assembly_order": [')
    print('      {"section_id": "...", "section_title": "...", "asset_type": "...",')
    print('       "source_type": "inline_template|asset_lookup|self_drafted",')
    print('       "source": "...", "items": [...], "format": "..."}')
    print("    ]")
    print("  }")
    print()
    print(f"保存到: {out_dir / 'intermediate.json'}")
    print()
    print("然后运行:")
    print(f"  python scripts/b_mode_extract.py --project {args.project} "
          f"--part {args.part} --build-from-json {out_dir / 'intermediate.json'}")
    print("=" * 60)
    print()
    print("--- raw.txt 内容 ---")
    print(text)


def cmd_build_from_json(args, project_dir: Path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from brief_schema import validate_response_part_b

    brief = load_brief(project_dir)
    part = get_b_part(brief, args.part)
    validate_response_part_b(part)

    part_dir_name = _safe_name(part['name'])
    out_dir = project_dir / 'output' / 'b_mode' / part_dir_name

    json_path = Path(args.build_from_json)
    if not json_path.exists():
        print(f"[错误] intermediate.json 不存在: {json_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding='utf-8'))
    assembly_order = data.get('assembly_order', [])
    if not assembly_order:
        print(f"[错误] intermediate.json 中 assembly_order 为空", file=sys.stderr)
        sys.exit(1)

    manifest = {
        'part_name': part['name'],
        'production_mode': 'B',
        'source_anchor': part.get('source_anchor'),
        'assembly_order': assembly_order,
        'assets_provider': 'placeholder',
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / 'manifest.yaml'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(manifest, f, allow_unicode=True, sort_keys=False)

    # 统计 source_type 分布
    from collections import Counter
    source_types = Counter(s.get('source_type', '<missing>') for s in assembly_order)

    print(f"[完成] Part[{args.part}] '{part['name']}' (B 模式)")
    print(f"  manifest.yaml: {manifest_path}")
    print(f"  assembly_order 项数: {len(assembly_order)}")
    print(f"  source_type 分布: {dict(source_types)}")
    print()
    print("=" * 60)
    print("下一步(Step 4): 用户 review manifest.yaml 确认 assembly_order 合理。")
    print("Step 5: 跑 b_mode_fill.py 按 manifest 组装 assembled.docx + .pending_marker")
    print(f"  python scripts/b_mode_fill.py --project {args.project} --part {args.part}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='B 模式材料组装清单产出(V61)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--project', required=True, help='项目名')
    parser.add_argument('--part', type=int, required=True,
                        help='response_file_parts 索引(0 基,production_mode=B)')
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--extract-text', action='store_true',
                   help='Step 1-2: 提取原文到 raw.txt')
    g.add_argument('--build-from-json',
                   help='Step 3.5: 从 intermediate.json 构建 manifest.yaml')
    args = parser.parse_args()

    project_dir = ROOT / 'projects' / args.project

    # V3-3: timing hook
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _timing_hook import stage_timer

    with stage_timer("b_mode_extract", project_dir):
        if not project_dir.exists():
            print(f"[错误] 项目目录不存在: {project_dir}", file=sys.stderr)
            sys.exit(1)

        # V53: 未 review 则硬失败
        from brief_schema import ensure_reviewed
        ensure_reviewed(project_dir / 'output')

        if args.extract_text:
            cmd_extract_text(args, project_dir)
        else:
            cmd_build_from_json(args, project_dir)


if __name__ == '__main__':
    main()
