# -*- coding: utf-8 -*-
"""
b_mode_run.py · B 模式 Part 一键运行器(v2)

把 extract-text + build-from-json + fill 三步合并为单命令。
支持单 Part 或 --all 批量。

用法:
    ./run_script.bat b_mode_run.py --project demo_cadre_training --part 3
    ./run_script.bat b_mode_run.py --project demo_cadre_training --all
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _safe_name(name: str) -> str:
    s = re.sub(r'^[一二三四五六七八九十\d]+[、.]\s*', '', name)
    s = re.sub(r'[(].+?[)]', '', s)
    s = re.sub(r'[(].+?[)]', '', s)
    return s.strip() or 'part'


def run_subprocess(args: list[str]) -> int:
    return subprocess.run([sys.executable] + args).returncode


def load_parts(project: str):
    brief_path = ROOT / 'projects' / project / 'output' / 'tender_brief.json'
    if not brief_path.exists():
        print(f"[错误] 找不到 {brief_path}", file=sys.stderr)
        sys.exit(1)
    return json.loads(brief_path.read_text(encoding='utf-8')).get(
        'response_file_parts', [])


def run_part(project: str, part_idx: int, with_extract: bool) -> dict:
    script_dir = ROOT / 'scripts'
    parts = load_parts(project)
    if part_idx >= len(parts):
        return {'status': 'error', 'msg': f'索引越界: {part_idx}'}
    part = parts[part_idx]
    name = part.get('name', '')
    mode = part.get('production_mode', '')
    if mode != 'B':
        return {'status': 'skipped', 'msg': f'production_mode={mode}(非 B)'}

    part_dir = ROOT / 'projects' / project / 'output' / 'b_mode' / _safe_name(name)
    inter = part_dir / 'intermediate.json'

    if with_extract:
        print(f"\n[Part {part_idx}] {name} - extract-text")
        rc = run_subprocess([str(script_dir / 'b_mode_extract.py'),
                             '--project', project,
                             '--part', str(part_idx),
                             '--extract-text'])
        if rc != 0:
            return {'status': 'error', 'msg': 'extract-text 失败'}

    if not inter.exists():
        return {'status': 'skipped',
                'msg': f'intermediate.json 未找到({inter});请 AI 先产'}

    print(f"\n[Part {part_idx}] {name} - build-from-json")
    rc = run_subprocess([str(script_dir / 'b_mode_extract.py'),
                         '--project', project,
                         '--part', str(part_idx),
                         '--build-from-json', str(inter)])
    if rc != 0:
        return {'status': 'error', 'msg': 'build-from-json 失败'}

    print(f"\n[Part {part_idx}] {name} - fill")
    rc = run_subprocess([str(script_dir / 'b_mode_fill.py'),
                         '--project', project,
                         '--part', str(part_idx)])
    if rc != 0:
        return {'status': 'error', 'msg': 'fill 失败'}

    return {'status': 'ok', 'msg': '三步完成'}


def main():
    p = argparse.ArgumentParser(
        description='B 模式 Part 一键运行器(extract + build + fill)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--project', required=True)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('--part', type=int)
    grp.add_argument('--all', action='store_true')
    p.add_argument('--with-extract', action='store_true')
    args = p.parse_args()

    parts = load_parts(args.project)
    if args.all:
        target = [i for i, prt in enumerate(parts)
                  if prt.get('production_mode') == 'B']
        print(f"[信息] 批量模式:{len(target)} 个 B 模式 Part (索引 {target})")
    else:
        target = [args.part]

    results = []
    for idx in target:
        res = run_part(args.project, idx, args.with_extract)
        results.append((idx, parts[idx].get('name', ''), res))

    print()
    print("=" * 60)
    print(f"B 模式一键运行汇总 ({args.project})")
    print("=" * 60)
    ok = sum(1 for _, _, r in results if r['status'] == 'ok')
    err = sum(1 for _, _, r in results if r['status'] == 'error')
    skip = sum(1 for _, _, r in results if r['status'] == 'skipped')
    for idx, name, r in results:
        icon = {'ok': '[OK]', 'error': '[ERR]', 'skipped': '[SKIP]'}[r['status']]
        print(f"  {icon} Part[{idx}] {name[:30]:30s}  {r['msg']}")
    print()
    print(f"总计: {ok} 成功 / {err} 失败 / {skip} 跳过")
    if err > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
