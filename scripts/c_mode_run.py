# -*- coding: utf-8 -*-
"""
c_mode_run.py · C 模式 Part 一键运行器(v2)

把 extract-text + build-from-json + fill 三步合并为单命令。
支持单 Part 或 --all 批量。

用法:
    # 单 Part
    ./run_script.bat c_mode_run.py --project demo_cadre_training --part 0

    # 所有 C 模式 Part(按 response_file_parts 顺序)
    ./run_script.bat c_mode_run.py --project demo_cadre_training --all

    # 必须已有 intermediate.json(由 AI 按 SKILL.md 阶段 4-C 产出)
    # 若 intermediate.json 不存在,会跳过该 Part 并在汇总中提示

前提:
    - output/tender_brief.json 已含 response_file_parts + 各 Part 的 production_mode
    - output/tender_brief.reviewed 已由用户建立
    - output/c_mode/<part_name>/intermediate.json 已由 AI 产出

本脚本不包含"extract-text"阶段,因为 raw.txt 只是供 AI 产 intermediate.json 的
中间产物,不是渲染必需。实际流程:raw.txt 由 c_mode_extract --extract-text
产出,AI 读后产 intermediate.json,本脚本从 intermediate.json 直接一键跑完
build-from-json + fill。

若需要先产 raw.txt,加 --with-extract 参数。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _safe_name(name: str) -> str:
    import re
    s = re.sub(r'^[一二三四五六七八九十\d]+[、.]\s*', '', name)
    s = re.sub(r'[(].+?[)]', '', s)
    s = re.sub(r'[(].+?[)]', '', s)
    return s.strip() or 'part'


def run_subprocess(args: list[str]) -> int:
    """运行一个 python 子进程,直通 stdout/stderr,返回 exit code。"""
    python = sys.executable
    proc = subprocess.run([python] + args)
    return proc.returncode


def _ensure_bidding_entity(project: str, non_interactive: bool,
                           entity_id: str | None) -> None:
    """
    v2 补丁 1:c_mode_run 启动时检查 extracted.bidding_entity,缺则自动
    触发 select_bidding_entity.py。若该脚本因多主体交互失败,本函数同样会退出。
    """
    brief_path = (ROOT / 'projects' / project / 'output' / 'tender_brief.json')
    if not brief_path.exists():
        # 让后续 load_parts 继续报错,这里不重复报
        return
    data = json.loads(brief_path.read_text(encoding='utf-8'))
    if (data.get('extracted') or {}).get('bidding_entity'):
        return  # 已就位

    print("[信息] extracted.bidding_entity 未设置,自动触发 "
          "select_bidding_entity.py", file=sys.stderr)
    argv = [str(ROOT / 'scripts' / 'select_bidding_entity.py'),
            '--project', project]
    if non_interactive:
        argv.append('--non-interactive')
    if entity_id:
        argv += ['--entity-id', entity_id]
    rc = run_subprocess(argv)
    if rc != 0:
        print("[错误] select_bidding_entity.py 未能确定投标主体,"
              "c_mode_run 退出", file=sys.stderr)
        sys.exit(rc)


def load_parts(project: str):
    brief_path = ROOT / 'projects' / project / 'output' / 'tender_brief.json'
    if not brief_path.exists():
        print(f"[错误] 找不到 {brief_path},请先跑阶段 1", file=sys.stderr)
        sys.exit(1)
    data = json.loads(brief_path.read_text(encoding='utf-8'))
    return data.get('response_file_parts', [])


def run_part(project: str, part_idx: int, with_extract: bool) -> dict:
    """单 Part 执行:可选 extract → build → fill。返回 {status, msgs}。"""
    script_dir = ROOT / 'scripts'
    parts = load_parts(project)
    if part_idx >= len(parts):
        return {'status': 'error', 'msg': f'索引越界: {part_idx}'}
    part = parts[part_idx]
    name = part.get('name', '')
    mode = part.get('production_mode', '')
    if mode != 'C':
        return {'status': 'skipped', 'msg': f'production_mode={mode}(非 C)'}

    part_dir = (ROOT / 'projects' / project / 'output' / 'c_mode'
                / _safe_name(name))
    inter = part_dir / 'intermediate.json'

    # 可选:extract-text 产 raw.txt(仅当 --with-extract 或 intermediate.json 不存在时)
    if with_extract:
        print(f"\n[Part {part_idx}] {name} - extract-text")
        rc = run_subprocess([str(script_dir / 'c_mode_extract.py'),
                             '--project', project,
                             '--part', str(part_idx),
                             '--extract-text'])
        if rc != 0:
            return {'status': 'error', 'msg': 'extract-text 失败'}

    if not inter.exists():
        return {'status': 'skipped',
                'msg': f'intermediate.json 未找到({inter});请 AI 先产'}

    # V3-7: 在 jinja build/fill 之前,尝试 docx passthrough 分流
    # 先从 intermediate.json 数 variable blocks,避免 passthrough_part 在
    # variables.yaml 不存在时默认 n_vars=0 → 漏判变量超阈 part
    PASSTHROUGH_MAX_VARS = 5
    try:
        inter_data = json.loads(inter.read_text(encoding='utf-8'))
        n_var_blocks = sum(
            1 for b in inter_data.get('blocks', []) if b.get('type') == 'variable'
        )
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[Part {part_idx}] {name} - intermediate.json 解析失败"
              f"({exc!r}),按 jinja 路径处理", file=sys.stderr)
        n_var_blocks = PASSTHROUGH_MAX_VARS + 1  # 强制走 jinja

    if n_var_blocks > PASSTHROUGH_MAX_VARS:
        print(f"\n[Part {part_idx}] {name} - docx 直切跳过"
              f"(变量数 {n_var_blocks} > {PASSTHROUGH_MAX_VARS});走 jinja 模板填充")
    else:
        # 调 passthrough_part(内部还会校 source_format / sub_mode / anchor.type)
        sys.path.insert(0, str(script_dir))
        from c_mode_docx_passthrough import passthrough_part
        ps_result = passthrough_part(
            project, part_idx,
            max_vars=PASSTHROUGH_MAX_VARS, dry_run=False,
        )
        if ps_result['status'] == 'ok':
            print(f"\n[Part {part_idx}] {name} - docx 直切完成 ({ps_result['msg']})")
            return {'status': 'ok',
                    'msg': f'docx 直切: {ps_result["msg"]}'}
        if ps_result['status'] == 'error':
            return {'status': 'error',
                    'msg': f'docx 直切错误: {ps_result["msg"]}'}
        # status == 'skipped' → 显示原因后 fallthrough 到 jinja
        print(f"\n[Part {part_idx}] {name} - docx 直切跳过"
              f"({ps_result['msg']});走 jinja 模板填充")

    # ── jinja 路径(build-from-json + fill)──

    # build-from-json
    print(f"\n[Part {part_idx}] {name} - build-from-json")
    rc = run_subprocess([str(script_dir / 'c_mode_extract.py'),
                         '--project', project,
                         '--part', str(part_idx),
                         '--build-from-json', str(inter)])
    if rc != 0:
        return {'status': 'error', 'msg': 'build-from-json 失败'}

    # fill(非交互)
    print(f"\n[Part {part_idx}] {name} - fill")
    rc = run_subprocess([str(script_dir / 'c_mode_fill.py'),
                         '--project', project,
                         '--part', str(part_idx)])
    if rc != 0:
        return {'status': 'error', 'msg': 'fill 失败'}

    return {'status': 'ok', 'msg': 'jinja 模板填充: 三步完成'}


def main():
    p = argparse.ArgumentParser(
        description='C 模式 Part 一键运行器(extract + build + fill)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--project', required=True)
    grp = p.add_mutually_exclusive_group(required=True)
    grp.add_argument('--part', type=int, help='单 Part 索引(0 基)')
    grp.add_argument('--all', action='store_true',
                     help='所有 production_mode=C 的 Part')
    p.add_argument('--with-extract', action='store_true',
                   help='额外先跑 extract-text 刷 raw.txt')
    p.add_argument('--non-interactive', action='store_true',
                   help='非交互模式:若 bidding_entity 缺失,多主体场景拒绝执行')
    p.add_argument('--entity-id', default=None,
                   help='非交互模式下显式指定 own 主体 id(透传给 '
                        'select_bidding_entity.py)')
    args = p.parse_args()

    # V3-3: timing hook
    project_dir = ROOT / 'projects' / args.project
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _timing_hook import stage_timer

    with stage_timer("c_mode_run", project_dir):
        _main_body(args)


def _main_body(args):
    # v2 补丁 1:自动触发 select_bidding_entity(若 extracted.bidding_entity 未设置)
    _ensure_bidding_entity(args.project, args.non_interactive, args.entity_id)

    parts = load_parts(args.project)
    if args.all:
        target_indices = [i for i, prt in enumerate(parts)
                          if prt.get('production_mode') == 'C']
        print(f"[信息] 批量模式:{len(target_indices)} 个 C 模式 Part "
              f"(索引 {target_indices})")
    else:
        target_indices = [args.part]

    results = []
    for idx in target_indices:
        res = run_part(args.project, idx, args.with_extract)
        results.append((idx, parts[idx].get('name', ''), res))

    print()
    print("=" * 60)
    print(f"C 模式一键运行汇总 ({args.project})")
    print("=" * 60)
    ok_cnt = sum(1 for _, _, r in results if r['status'] == 'ok')
    err_cnt = sum(1 for _, _, r in results if r['status'] == 'error')
    skip_cnt = sum(1 for _, _, r in results if r['status'] == 'skipped')
    for idx, name, r in results:
        icon = {'ok': '[OK]', 'error': '[ERR]', 'skipped': '[SKIP]'}[r['status']]
        print(f"  {icon} Part[{idx}] {name[:30]:30s}  {r['msg']}")
    print()
    print(f"总计: {ok_cnt} 成功 / {err_cnt} 失败 / {skip_cnt} 跳过")

    if err_cnt > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
