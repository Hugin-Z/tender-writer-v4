# -*- coding: utf-8 -*-
"""
select_bidding_entity.py · v2 补丁 1:投标主体选择(回补)

目的:c_mode_run / b_mode_run 下游需要明确"本次投标以哪家 own 主体响应",
此脚本扫 companies.yaml 的 own 类型条目并把结果写入 tender_brief.json 的
`extracted.bidding_entity` 字段。

决策规则:
- 仅扫 type=own 且 status != placeholder 的条目
- 合格主体数 == 0 → 硬失败,提示先跑 add_company.py 注册
- 合格主体数 == 1 → 自动选中,stdout 打印"本次投标主体:{name}"
- 合格主体数 >= 2 → 列表让用户选编号,stdin 读入
  - 若 --non-interactive 指定,多主体场景会拒绝执行(不代用户选)

用法:
    ./run_script.bat select_bidding_entity.py --project <项目名>
    ./run_script.bat select_bidding_entity.py --project <项目名> --force
        (覆盖 tender_brief.json 中已有的 bidding_entity)
    ./run_script.bat select_bidding_entity.py --project <项目名> --non-interactive
        (CI/批处理;多主体场景退出非 0)

遵循 CLAUDE.md 红线:"AI 不得代替用户选择投标主体"。
多主体场景下:
- 交互模式必须由用户 stdin 选择
- 非交互模式必须退出非 0 并要求补参数 --entity-id 显式指定
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[错误] 缺少 PyYAML 依赖,请先双击 install.bat 安装依赖。",
          file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent


def load_own_candidates(companies_yaml_path: Path) -> list:
    """读 companies.yaml 过滤出合格的 own 主体。"""
    with open(companies_yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    candidates = []
    for c in data.get('companies', []):
        if c.get('type') != 'own':
            continue
        if c.get('status') == 'placeholder':
            continue
        candidates.append(c)
    return candidates


def prompt_user_select(candidates: list) -> dict:
    """交互选择主体;返回被选中的 company dict。"""
    print()
    print(f"发现 {len(candidates)} 家合格 own 主体,请选择本次投标使用哪一家:",
          file=sys.stderr)
    for i, c in enumerate(candidates, start=1):
        print(f"  [{i}] {c['id']} · {c['name']}", file=sys.stderr)
    while True:
        try:
            ans = input(f"请输入编号(1-{len(candidates)}): ").strip()
        except EOFError:
            print("[错误] 交互输入通道不可用(可能在 CI/管道中),"
                  "请改用 --non-interactive --entity-id <id>",
                  file=sys.stderr)
            sys.exit(1)
        try:
            idx = int(ans)
        except ValueError:
            print("  请输入一个整数", file=sys.stderr)
            continue
        if 1 <= idx <= len(candidates):
            return candidates[idx - 1]
        print(f"  请输入 1-{len(candidates)} 范围内的整数", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description='投标主体选择(v2 补丁 1)',
    )
    parser.add_argument('--project', required=True, help='项目名')
    parser.add_argument('--force', action='store_true',
                        help='覆盖 tender_brief.json 中已存在的 bidding_entity')
    parser.add_argument('--non-interactive', action='store_true',
                        help='非交互模式(CI/批处理);多主体时必须配 --entity-id')
    parser.add_argument('--entity-id', default=None,
                        help='非交互模式下显式指定 own 主体 id')
    args = parser.parse_args()

    project_dir = ROOT / 'projects' / args.project
    brief_path = project_dir / 'output' / 'tender_brief.json'
    companies_path = ROOT / 'companies.yaml'

    if not brief_path.exists():
        print(f"[错误] 找不到 tender_brief.json: {brief_path}",
              file=sys.stderr)
        sys.exit(1)
    if not companies_path.exists():
        print(f"[错误] 找不到 companies.yaml: {companies_path}",
              file=sys.stderr)
        sys.exit(1)

    brief = json.loads(brief_path.read_text(encoding='utf-8'))
    extracted = brief.setdefault('extracted', {})

    # 已有 bidding_entity 且未 --force
    existing = extracted.get('bidding_entity')
    if existing and not args.force:
        print(f"[信息] 已存在 bidding_entity={existing},"
              f"未指定 --force,不覆盖。", file=sys.stderr)
        print(existing)
        return 0

    candidates = load_own_candidates(companies_path)

    if len(candidates) == 0:
        print("[错误] 未发现合格 own 主体,请先跑 add_company.py 注册 "
              "(排除 status=placeholder 的条目)",
              file=sys.stderr)
        sys.exit(1)

    # 单主体 → 自动选中
    if len(candidates) == 1:
        chosen = candidates[0]
        print(f"[信息] 仅一家合格 own 主体,自动选中:{chosen['id']} · "
              f"{chosen['name']}", file=sys.stderr)

    # 多主体 → 按参数决定交互 or 拒绝
    else:
        if args.entity_id:
            match = [c for c in candidates if c['id'] == args.entity_id]
            if not match:
                print(f"[错误] --entity-id={args.entity_id} 不在合格 "
                      f"own 主体列表,可选:"
                      f"{[c['id'] for c in candidates]}",
                      file=sys.stderr)
                sys.exit(1)
            chosen = match[0]
            print(f"[信息] 非交互模式,按 --entity-id 选中:"
                  f"{chosen['id']}", file=sys.stderr)
        elif args.non_interactive:
            print(f"[错误] 发现 {len(candidates)} 家合格 own 主体,"
                  f"非交互模式下必须通过 --entity-id 显式指定。"
                  f"可选:{[c['id'] for c in candidates]}",
                  file=sys.stderr)
            sys.exit(1)
        else:
            chosen = prompt_user_select(candidates)

    # 写回 extracted.bidding_entity
    extracted['bidding_entity'] = chosen['id']
    brief_path.write_text(
        json.dumps(brief, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

    # stdout 打印结果(供脚本管道消费)
    print(f"本次投标主体:{chosen['name']}")
    print(f"  id: {chosen['id']}")
    print(f"  写回:{brief_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
