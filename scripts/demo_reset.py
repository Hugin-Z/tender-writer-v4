# -*- coding: utf-8 -*-
"""V3-13: demo 项目无破坏重跑工具。

restore demo_cadre_training/output/ 下所有 git tracked 文件回 HEAD 状态,
为 parse_tender --force 重跑提供干净 baseline。

红线 1 兼容:
- 不动 .reviewed 标记(它本就不在 git tracked 列表)
- 不动 untracked 文件
- 不调 git checkout / git clean

用法:
    ./run_script.bat demo_reset.py              # 默认 dry-run 预览
    ./run_script.bat demo_reset.py --dry-run    # 显式 dry-run
    ./run_script.bat demo_reset.py --yes        # 确认执行 git restore
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# Hardcode 路径(V3-13 范围仅 demo_cadre_training, 不接受 --project flag)
TARGET_PATH = "projects/demo_cadre_training/output/"
DEMO_REVIEWED_MARKER = "projects/demo_cadre_training/output/tender_brief.reviewed"


def ensure_repo_root(cwd: Path | None = None) -> Path:
    """确认当前在仓库根。否则 friendly error 退出。"""
    cwd = cwd or Path.cwd()
    if not (cwd / ".git").exists() or not (cwd / "scripts").is_dir():
        print(
            f"[错误] demo_reset.py 必须在仓库根跑,当前 cwd={cwd}\n"
            f"提示: 用 ./run_script.bat demo_reset.py 或 cd 到仓库根",
            file=sys.stderr,
        )
        sys.exit(1)
    if not (cwd / TARGET_PATH).is_dir():
        print(
            f"[错误] 找不到目标目录 {TARGET_PATH}\n"
            f"提示: V3-13 仅支持 demo_cadre_training 项目,当前仓库结构异常",
            file=sys.stderr,
        )
        sys.exit(1)
    return cwd


def list_tracked(repo_root: Path) -> list[str]:
    """git ls-files 列出 demo output/ 下所有 tracked 文件。"""
    try:
        result = subprocess.run(
            ["git", "ls-files", TARGET_PATH],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
        )
    except FileNotFoundError:
        print(
            "[错误] 未找到 git 命令。demo_reset.py 依赖 git CLI,"
            "请安装 git 并加入 PATH。",
            file=sys.stderr,
        )
        sys.exit(1)
    if result.returncode != 0:
        print(f"[错误] git ls-files 失败: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return [line for line in result.stdout.splitlines() if line.strip()]


def restore_files(repo_root: Path) -> int:
    """git restore 全部 tracked 文件。返回 git 退出码。"""
    try:
        result = subprocess.run(
            ["git", "restore", TARGET_PATH],
            cwd=repo_root, capture_output=True, text=True, encoding="utf-8",
        )
    except FileNotFoundError:
        print("[错误] 未找到 git 命令。", file=sys.stderr)
        return 127
    if result.returncode != 0:
        print(f"[错误] git restore 失败: {result.stderr}", file=sys.stderr)
        return result.returncode
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=(
            "V3-13: demo 项目无破坏重跑工具。restore demo_cadre_training/output/ "
            "回 HEAD 状态,为 parse_tender --force 重跑提供干净 baseline。"
        ),
    )
    g = parser.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true",
                   help="只显示要做的事,不执行(默认行为)")
    g.add_argument("--yes", action="store_true",
                   help="确认执行 git restore")
    args = parser.parse_args()

    # 默认 --dry-run(没 --yes 即视为 dry-run)
    is_dry = args.dry_run or (not args.yes)

    repo_root = ensure_repo_root()
    tracked = list_tracked(repo_root)

    print("=" * 60)
    print(f"V3-13 demo_reset: {'DRY-RUN(预览)' if is_dry else 'EXECUTING(执行)'}")
    print("=" * 60)
    print(f"目标目录: {TARGET_PATH}")
    print(f"将 restore {len(tracked)} 个 git tracked 文件 → HEAD 状态")
    print()
    print("范例文件(前 10 条):")
    for f in tracked[:10]:
        print(f"  {f}")
    if len(tracked) > 10:
        print(f"  ... 还有 {len(tracked) - 10} 个文件")
    print()
    print(f".reviewed 标记: 不动({DEMO_REVIEWED_MARKER}, 红线 1 兼容)")
    print(f"untracked 文件: 不动")
    print()

    if is_dry:
        print("[DRY-RUN] 没有执行任何变更。如确认,加 --yes 重跑。")
        sys.exit(0)

    rc = restore_files(repo_root)
    if rc != 0:
        sys.exit(rc)

    # 校验 .reviewed 仍在(只读校验,不创建)
    reviewed = repo_root / DEMO_REVIEWED_MARKER
    if not reviewed.exists():
        print(
            f"[警告] .reviewed 标记不存在 ({reviewed}),"
            f"parse_tender 仍可跑(它不检查 .reviewed),但下游脚本"
            f"(build_scoring_matrix / generate_outline / b_mode / c_mode / "
            f"compliance_check / v45_merge 等)会被 ensure_reviewed 闸门拦住。"
            f"完成新一轮 review 后请手动建 .reviewed 标记。"
        )
    else:
        print(f"[确认] .reviewed 标记存在 ({reviewed})")

    print()
    print(f"[完成] {len(tracked)} 个文件已 restore 到 HEAD 状态")
    print()
    print("下一步可选操作:")
    print("  ./run_script.bat parse_tender.py \\")
    print("      projects/demo_cadre_training/input/tender_demo.docx \\")
    print("      --out projects/demo_cadre_training/output --force")
    sys.exit(0)


if __name__ == "__main__":
    main()
