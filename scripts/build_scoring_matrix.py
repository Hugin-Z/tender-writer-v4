# -*- coding: utf-8 -*-
"""
build_scoring_matrix.py · 评分矩阵构建脚本（阶段 2）

输入:
    tender_brief.json（含 score_items_raw_positions 和 response_file_parts）

输出:
    output/scoring_matrix.csv

目标:
    从 tender_brief.json 读取 Step 1 已结构化的评分项数据,
    生成 10 列 CSV 骨架。第 1 列(评分项归属)和第 6 列(应答章节 placeholder)
    由脚本填,其余列由 AI 在阶段 2 Step 2 填充。
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brief_schema import normalize_response_parts, SCORING_MATRIX_COLUMNS, ensure_reviewed


def load_score_data(json_path: Path) -> tuple[list[dict], dict[str, str]]:
    """从 tender_brief.json 读取评分项和 Part 映射。

    返回:
        score_items: score_items_raw_positions 数组
        part_mode_map: {part_name: production_mode} 映射
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))

    score_items = data.get("score_items_raw_positions", [])
    if not score_items:
        print("[错误] tender_brief.json 中 score_items_raw_positions 为空。",
              file=sys.stderr)
        print("  请确认阶段 1 Step 2 已完成（section_anchors 写回 + "
              "update_score_positions.py 重算）。", file=sys.stderr)
        sys.exit(1)

    parts = normalize_response_parts(data.get("response_file_parts", []))
    if not parts:
        print("[错误] tender_brief.json 中 response_file_parts 为空。",
              file=sys.stderr)
        print("  请确认阶段 1 Step 4 已完成。", file=sys.stderr)
        sys.exit(1)

    # part_name → production_mode 映射
    part_mode_map: dict[str, str] = {}
    for part in parts:
        name = part["name"]
        mode = part.get("production_mode") or ""
        if not mode or mode == "__PENDING_AI__":
            print(f"[错误] response_file_parts 中 Part '{name}' 缺少 "
                  "production_mode（或仍为 __PENDING_AI__）。",
                  file=sys.stderr)
            print("  若为旧 schema,请先运行 migrate_brief_schema.py。",
                  file=sys.stderr)
            print("  若已迁移,需按 SKILL.md 阶段 1 Step 5 由 AI "
                  "补齐 production_mode。", file=sys.stderr)
            sys.exit(1)
        part_mode_map[name] = mode

    # 校验每条评分项的 part_attribution（硬失败,不做语义推断）
    for i, item in enumerate(score_items):
        attr = (item.get("part_attribution") or "").strip()
        if not attr or attr == "__PENDING_AI__":
            print(f"[错误] score_items_raw_positions[{i}] 缺少 "
                  "part_attribution（或仍为 __PENDING_AI__）。",
                  file=sys.stderr)
            print("  若 tender_brief.json 为旧 schema,请先运行 "
                  "migrate_brief_schema.py 迁移。", file=sys.stderr)
            print("  若已迁移,需按 SKILL.md 阶段 1 Step 6 由 AI "
                  "补齐 part_attribution。", file=sys.stderr)
            sys.exit(1)
        if attr not in part_mode_map:
            print(f"[错误] score_items_raw_positions[{i}] 的 "
                  f"part_attribution='{attr}' "
                  "在 response_file_parts 中找不到对应 Part。",
                  file=sys.stderr)
            sys.exit(1)

    return score_items, part_mode_map


def build_matrix_rows(
    score_items: list[dict],
    part_mode_map: dict[str, str],
) -> list[list[str]]:
    """构建 CSV 行。第 1 列和第 6 列由脚本填，其余留空给 AI。"""
    rows = []
    for item in score_items:
        attr = item["part_attribution"]
        mode = part_mode_map[attr]

        # 第 6 列: 应答章节 placeholder
        # v2/P13:对外表述,禁用"v1.1 范围"这类工具链内部版本术语
        if mode == "A":
            chapter_placeholder = f"{attr} / [待阶段 3 回填]"
        else:
            # 按生产模式给出明确归属说明
            mode_desc = {
                "B": "素材组装类",
                "C": "模板填充类",
                "D": "外部信息采集类",
            }.get(mode, "不适用")
            chapter_placeholder = f"{attr} / 不适用(归属非技术部分,{mode_desc})"

        rows.append([
            attr,                   # 1: 评分项归属
            "",                     # 2: 评分项 (AI 填)
            "",                     # 3: 分值 (AI 填)
            "",                     # 4: 评分标准 (AI 填)
            "",                     # 5: 关键词 (AI 填)
            chapter_placeholder,    # 6: 应答章节
            "",                     # 7: 证据材料 (AI 填)
            "",                     # 8: 风险提示 (AI 填)
            "",                     # 9: 撰写指引 (AI 填)
            "",                     # 10: 必备要素 (AI 填)
        ])
    return rows


def count_csv_columns(path: Path) -> int:
    """读取 CSV 第一行,返回列数。"""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        first_row = next(reader, None)
        return len(first_row) if first_row else 0


def check_existing_csv(csv_path: Path, force: bool) -> None:
    """检查输出文件是否已存在。已存在时根据 force 决定行为。"""
    if not csv_path.exists():
        return

    if force:
        print(f"[警告] --force 模式:覆盖已有 {csv_path}", file=sys.stderr)
        return

    existing_cols = count_csv_columns(csv_path)
    current_cols = len(SCORING_MATRIX_COLUMNS)

    if existing_cols == current_cols:
        print(
            f"[错误] scoring_matrix.csv 已存在且列数({existing_cols})与当前 schema 一致。\n"
            f"  build_scoring_matrix.py 的职责是初次生成骨架,不应覆盖已填充数据。\n"
            f"  如需覆盖,加 --force 参数。\n"
            f"  如需 schema 升级,走 migrate_brief_schema.py 路径。",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        print(
            f"[错误] scoring_matrix.csv 已存在但列数({existing_cols})与当前 schema({current_cols})不一致。\n"
            f"  这是 schema 升级场景,不要用 build_scoring_matrix 重建(会丢数据),\n"
            f"  请用 migrate_brief_schema.py 迁移。\n"
            f"  如确需强制重建,加 --force 参数(已有数据将被覆盖)。",
            file=sys.stderr,
        )
        sys.exit(1)


def write_csv_with_bom(path: Path, headers: list[str], rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="评分矩阵构建（阶段 2）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("brief_path", help="tender_brief.json 路径")
    parser.add_argument("--out", default="output", help="输出目录，默认 output/")
    parser.add_argument("--force", action="store_true",
                        help="强制覆盖已有 scoring_matrix.csv(已有数据将被覆盖)")
    args = parser.parse_args()

    # V3-3: timing hook
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _timing_hook import stage_timer
    # brief 在 project/output/tender_brief.json,推 project_dir
    _project_dir = Path(args.brief_path).resolve().parent.parent

    with stage_timer("build_scoring_matrix", _project_dir):
        _main_body(args)


def _main_body(args) -> None:
    brief_path = Path(args.brief_path)
    if not brief_path.exists():
        print(f"[错误] 找不到文件: {brief_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # V53: 未 review 则硬失败(--force 不绕过此 gate)
    ensure_reviewed(out_dir)

    csv_path = out_dir / "scoring_matrix.csv"
    check_existing_csv(csv_path, args.force)

    print(f"[信息] 正在读取: {brief_path}", file=sys.stderr)
    score_items, part_mode_map = load_score_data(brief_path)
    print(f"[信息] 读取了 {len(score_items)} 条评分项", file=sys.stderr)

    rows = build_matrix_rows(score_items, part_mode_map)
    write_csv_with_bom(csv_path, SCORING_MATRIX_COLUMNS, rows)

    # 归属分布统计
    from collections import Counter
    attr_dist = Counter(item["part_attribution"] for item in score_items)
    placeholder_dist = Counter(
        "待阶段 3 回填" if part_mode_map[item["part_attribution"]] == "A"
        else f"不适用(生产模式 {part_mode_map[item['part_attribution']]})"
        for item in score_items
    )

    print(f"[完成] 评分矩阵已写入: {csv_path}", file=sys.stderr)
    print(f"[信息] 评分项数量: {len(score_items)}", file=sys.stderr)
    print(f"[信息] 第 1 列归属分布: {dict(attr_dist)}", file=sys.stderr)
    print(f"[信息] 第 6 列 placeholder 分布: {dict(placeholder_dist)}", file=sys.stderr)
    print()
    print("=" * 60)
    print("阶段 2 脚本部分完成。下一步:")
    print(f"  1. AI 读取 {csv_path} 和 tender_brief.json")
    print("  2. AI 逐行填充第 2-5 列、第 7-9 列和第 10 列(必备要素)")
    print("  3. 用户 review CSV 后进入阶段 3")
    print("=" * 60)


if __name__ == "__main__":
    main()
