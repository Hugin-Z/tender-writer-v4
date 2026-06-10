# -*- coding: utf-8 -*-
"""
b_mode_fill.py · B 模式 Part 组装(V61)

职责:读 manifest.yaml 和 assets_provider 字段,按 assembly_order 逐段处理,
产出 assembled.docx + .pending_marker 空文件。

source_type 分流:
- inline_template: 占位文字 + 引用 c_mode 填充能力(本轮不实际调用,产占位段落说明)
- asset_lookup: 调 AssetsProvider.lookup + resolve → 从返回的占位 docx 拷贝段落
- self_drafted: 产占位段落 "[本节需供应商自撰: <section_title>]"
- 未知 source_type: raise ValueError

用法:
    python scripts/b_mode_fill.py --project <项目> --part <N>
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from docx import Document
    from docx.shared import Pt
except ImportError:
    print("[错误] 缺少 python-docx 依赖,请先双击 install.bat 安装依赖。", file=sys.stderr)
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖。", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent


def _safe_name(name: str) -> str:
    s = re.sub(r'^[一二三四五六七八九十\d]+[、.]\s*', '', name)
    s = re.sub(r'[（(].+?[)）]', '', s)
    s = s.strip()
    return s or 'part'


def _append_heading(doc, text: str, level: int = 2):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(14)


def _append_placeholder_body(doc, text: str):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True


def _handle_inline_template(doc, spec: dict, part_name: str):
    """inline_template: 招标文件给模板,调 c_mode 填充能力。

    本轮实现:写占位段落,提示"借用 c_mode_fill 填充"。
    真实填充需用户手工触发 c_mode_fill 或未来 b_mode_fill 扩展。
    """
    title = spec.get('section_title', '<untitled>')
    _append_heading(doc, f"{spec.get('section_id', '')} {title}")
    _append_placeholder_body(
        doc,
        f"[inline_template 占位] 本段为招标文件给定模板的变量填充。"
        f"当前 B 模式基建阶段不实际调用 c_mode 填充能力,"
        f"产出 assembled.docx 后请手工按 variables 要求填写,"
        f"或在材料管理子系统上线后通过 b_mode_fill 自动调 c_mode 填充完成。"
    )
    items = spec.get('items') or []
    if items:
        _append_placeholder_body(doc, f"字段清单: {', '.join(str(i) for i in items)}")


def _handle_asset_lookup(doc, spec: dict, provider, part_name: str):
    """asset_lookup: 走 AssetsProvider 接口。

    V3-1:把 lookup_priority / year_filter / asset_query.type 从 spec 传给
    provider.lookup;真实命中时追加来源溯源行(便于审核位回查),不再追加占位文字。
    """
    from docx import Document as _DocxDocument

    title = spec.get('section_title', '<untitled>')
    asset_type = spec.get('asset_type', 'unknown')
    _append_heading(doc, f"{spec.get('section_id', '')} {title}")

    asset_query = spec.get('asset_query', {}) or {}
    ref = provider.lookup(
        asset_type,
        asset_query_type=asset_query.get('type', ''),
        lookup_priority=spec.get('lookup_priority', 'latest_year_first'),
        year_filter=spec.get('year_filter'),
        # 旧字段保留(PlaceholderAssetsProvider 用于构造 lookup_key)
        part=part_name,
        section_id=spec.get('section_id', ''),
        source=spec.get('source', ''),
    )
    resolved_path = provider.resolve(ref)

    # 从 resolve 返回的 docx 拷贝段落内容到当前 doc
    src_doc = _DocxDocument(str(resolved_path))
    for para in src_doc.paragraphs:
        if para.text.strip():
            new_p = doc.add_paragraph()
            new_p.add_run(para.text)

    if ref.is_placeholder:
        _append_placeholder_body(
            doc,
            f"(AssetRef 占位: is_placeholder={ref.is_placeholder}, "
            f"lookup_key={ref.lookup_key})"
        )
    else:
        # V3-1:真实命中时追加溯源行(便于审核位回查实际选用的 asset)
        src_filename = ref.metadata.get("filename", "")
        src_kind = ref.metadata.get("kind", "")
        if src_filename:
            _append_placeholder_body(
                doc, f"(asset 来源: {src_filename}, kind={src_kind})"
            )


def _handle_self_drafted(doc, spec: dict, part_name: str):
    """self_drafted: 供应商自撰,产占位段落。"""
    title = spec.get('section_title', part_name)
    _append_heading(doc, f"{spec.get('section_id', '')} {title}".strip())
    _append_placeholder_body(
        doc,
        f"[本节需供应商自撰: {title}]"
    )
    if spec.get('source'):
        _append_placeholder_body(doc, f"招标文件原文提示: {spec.get('source')}")


def _dispatch(doc, spec: dict, provider, part_name: str):
    st = spec.get('source_type')
    if st == 'inline_template':
        _handle_inline_template(doc, spec, part_name)
    elif st == 'asset_lookup':
        _handle_asset_lookup(doc, spec, provider, part_name)
    elif st == 'self_drafted':
        _handle_self_drafted(doc, spec, part_name)
    else:
        raise ValueError(
            f"未知 source_type='{st}' 在 assembly_order 项 section_id="
            f"{spec.get('section_id', '?')}。"
            f"当前合法值: inline_template / asset_lookup / self_drafted。"
            f"AI 判出新形态由用户 review 决定是否扩展 b_mode_fill。"
        )


def main():
    parser = argparse.ArgumentParser(
        description='B 模式 Part 组装(V61)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--project', required=True, help='项目名')
    parser.add_argument('--part', type=int, required=True, help='response_file_parts 索引')
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='V3-1:CuratedLocalAssetsProvider 多命中时不弹 stdin 提示,'
             '按 lookup_priority 自动选(适用于 CI / 自动化场景)',
    )
    args = parser.parse_args()

    project_dir = ROOT / 'projects' / args.project

    # V3-3: timing hook
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _timing_hook import stage_timer

    with stage_timer("b_mode_fill", project_dir):
        _main_body(args, project_dir)


def _main_body(args, project_dir):
    # V53: 未 review 则硬失败
    from brief_schema import ensure_reviewed
    ensure_reviewed(project_dir / 'output')

    import json as _json
    with open(project_dir / 'output' / 'tender_brief.json', 'r', encoding='utf-8') as f:
        brief = _json.load(f)
    parts = brief.get('response_file_parts', [])
    if args.part < 0 or args.part >= len(parts):
        print(f"[错误] --part 超出范围", file=sys.stderr)
        sys.exit(1)
    part = parts[args.part]
    if part.get('production_mode') != 'B':
        print(f"[错误] Part[{args.part}] production_mode="
              f"{part.get('production_mode')} 不是 B", file=sys.stderr)
        sys.exit(1)

    part_dir_name = _safe_name(part['name'])
    b_dir = project_dir / 'output' / 'b_mode' / part_dir_name

    manifest_path = b_dir / 'manifest.yaml'
    if not manifest_path.exists():
        print(f"[错误] 找不到 manifest.yaml: {manifest_path}", file=sys.stderr)
        print(f"  请先跑 b_mode_extract.py 产出 manifest", file=sys.stderr)
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = yaml.safe_load(f)

    provider_name = manifest.get('assets_provider', 'placeholder')
    from assets_provider import get_provider

    # V3-1:把 brief.extracted.bidding_entity 透传给 provider 当 company_id,
    # 让 CuratedLocalAssetsProvider 扫到正确公司目录。bidding_entity 缺省时
    # 走 provider 自身的默认值(CuratedLocalAssetsProvider 默认 own_default)。
    provider_kwargs: dict = {}
    bidding_entity = (brief.get('extracted', {}) or {}).get('bidding_entity', '')
    if provider_name == 'curated_local':
        if bidding_entity:
            provider_kwargs['company_id'] = bidding_entity
        if args.non_interactive:
            provider_kwargs['non_interactive'] = True

    provider = get_provider(provider_name, **provider_kwargs)

    assembly_order = manifest.get('assembly_order', [])
    print(f"[信息] 组装 Part[{args.part}] '{part['name']}' (B 模式)"
          f",共 {len(assembly_order)} 项")
    print(f"  assets_provider: {provider_name}")

    # v2 补丁 2(字体修复):为 assembled.docx 的 Normal/Heading 样式设字体,
    # 避免 run fallback 到 docDefaults 主题字体(WPS 会渲染为日文 MS 明朝)
    from docx_builder import apply_default_styles

    doc = Document()
    apply_default_styles(doc)
    # 第一段:Part 标题
    p = doc.add_paragraph()
    run = p.add_run(part['name'])
    run.bold = True
    run.font.size = Pt(16)

    stats = {'inline_template': 0, 'asset_lookup': 0, 'self_drafted': 0}
    for i, spec in enumerate(assembly_order):
        _dispatch(doc, spec, provider, part['name'])
        st = spec.get('source_type')
        if st in stats:
            stats[st] += 1

    assembled_path = b_dir / 'assembled.docx'
    doc.save(str(assembled_path))

    # .pending_marker 空文件
    marker_path = b_dir / '.pending_marker'
    marker_path.write_text('', encoding='utf-8')

    print()
    print("=" * 60)
    print(f"[完成] assembled.docx: {assembled_path}")
    print(f"[完成] .pending_marker: {marker_path} (占位状态标记)")
    print(f"  inline_template 段: {stats['inline_template']}")
    print(f"  asset_lookup 段:    {stats['asset_lookup']}")
    print(f"  self_drafted 段:    {stats['self_drafted']}")
    print()
    print("用户填充完成真实内容后,请手工删除 .pending_marker。")
    print("V45 整标合并器会检测 marker,列入 pending_manual_work.md。")
    print("=" * 60)


if __name__ == '__main__':
    main()
