# -*- coding: utf-8 -*-
"""
generate_outline.py · 提纲生成脚本（阶段 3）

输入:
    scoring_matrix.csv + tender_brief.json（同目录）

输出:
    outline.md + scoring_matrix.csv（第 6 列回填）

目标:
    1. 仅为 production_mode==A 的 Part 生成提纲（方向 C）
    2. 从采购需求章节提取整体方案主干
    3. 评分项响应章节独立段，待 AI 阶段 4 融合
    4. 回填 scoring_matrix.csv 第 6 列章节路径
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brief_schema import build_part_maps

# 采购需求章节内子标题正则（独立于 parse_tender.py，不复用）
# 匹配: "一、" / "(一)" / "1.1"（含小数点），不匹配裸 "1 "/"2 " 等表格行
_SUB_HEADING = re.compile(
    r"^([一二三四五六七八九十]+[、．.]"
    r"|[（(][一二三四五六七八九十]+[）)]"
    r"|\d+\.\d+)"
)


def load_matrix(csv_path: Path) -> list[dict]:
    """加载 scoring_matrix.csv，标注行号。"""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for idx, row in enumerate(csv.DictReader(f), start=1):
            row["_row_no"] = idx
            rows.append(row)
    return rows


def load_procurement_trunk(json_path: Path) -> list[str]:
    """从 tender_brief.json 读取采购需求章节，提取子标题作为主干条目。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))

    anchor = None
    for a in data.get("section_anchors", []):
        if a.get("section") == "采购需求":
            anchor = a
            break

    if not anchor:
        print("[警告] section_anchors 中未找到'采购需求'章节，"
              "主干提取跳过。", file=sys.stderr)
        return []

    raw_path = json_path.parent / "tender_raw.txt"
    if not raw_path.exists():
        print(f"[警告] 未找到 {raw_path}，主干提取跳过。", file=sys.stderr)
        return []

    lines = raw_path.read_text(encoding="utf-8").split("\n")
    start = anchor["start_line"]
    end = min(anchor["end_line"], len(lines))

    trunk = []
    for i in range(start, end):
        s = lines[i].strip()
        if s and _SUB_HEADING.match(s) and len(s) <= 80:
            trunk.append(s)

    if len(trunk) < 3:
        print(f"[警告] 采购需求章节子标题切分结果仅 {len(trunk)} 条（< 3），"
              "主干可能不完整。", file=sys.stderr)

    return trunk


def load_part_mode_map(json_path: Path) -> dict[str, str]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    part_name_map, _ = build_part_maps(data.get("response_file_parts", []))
    return {
        name: part["production_mode"]
        for name, part in part_name_map.items()
    }


# v2:类型化 outline 模板支持
VALID_PROJECT_TYPES = ("engineering", "platform", "research", "planning", "other")


def load_project_type(json_path: Path) -> str:
    """读 tender_brief.json 的 extracted.project_type;非法或空返回 ''。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    t = (data.get("extracted", {}).get("project_type") or "").strip().lower()
    return t if t in VALID_PROJECT_TYPES else ""


def load_outline_template(project_type: str) -> str | None:
    """加载 references/outline_templates/{type}/outline_skeleton.md。找不到返回 None。"""
    if not project_type:
        return None
    repo_root = Path(__file__).resolve().parent.parent
    tpl_path = repo_root / "references" / "outline_templates" / project_type / "outline_skeleton.md"
    if not tpl_path.exists():
        return None
    return tpl_path.read_text(encoding="utf-8")


def build_outline_from_template(
    template_text: str,
    part_name: str,
    score_rows: list[dict],
    project_type: str,
) -> str:
    """
    按类型模板填骨架。策略:
    - 把模板顶部标题换成 f"# {part_name} 提纲(project_type={project_type})"
    - 不改动中间章节主体(保留评分项嵌入位注释,由 AI 阶段 4 融合)
    - 在末尾"覆盖度自检"表格的空行下填入 score_rows
    """
    lines = template_text.splitlines()
    out: list[str] = []
    total_score = 0.0

    # 替换第一行大标题
    if lines and lines[0].startswith("# "):
        out.append(f"# {part_name} 提纲(方向 C;project_type={project_type})")
        lines = lines[1:]

    # 覆盖度自检表的表头后插入数据
    in_coverage_header = False
    coverage_header_seen = False
    for line in lines:
        out.append(line)
        # 识别覆盖度自检表的分隔行 "|---|---|..."
        if not coverage_header_seen and re.match(r"^\|[-|\s]+\|$", line):
            # 检查前一行是不是表头
            if len(out) >= 2 and "矩阵行号" in out[-2]:
                coverage_header_seen = True
                # 插入 score_rows
                for i, row in enumerate(score_rows, 1):
                    row_label = f"R{row['_row_no']:02d}"
                    item_name = _get_item_name(row)
                    score_str = (row.get("分值") or "").strip() or "?"
                    part = (row.get("评分项归属") or "").strip()
                    try:
                        total_score += float(score_str)
                    except ValueError:
                        pass
                    # 表头列序:矩阵行号 | 评分项 | 分值 | 归属 Part | outline 响应章节
                    out.append(
                        f"| {row_label} | {item_name} | {score_str} "
                        f"| {part} | 评分项 R{row['_row_no']:02d} 响应位 |"
                    )

    # 末尾补合计
    out.append("")
    out.append(f"合计覆盖分值:{total_score:g} 分(本模板类型={project_type};"
               f"共 {len(score_rows)} 条主撰类评分项,由投标方按章节撰写响应)")
    out.append("")
    out.append("> 撰写建议参考同目录下的 guidance.md 以及 references/ai_output_rules.md")
    out.append("")

    return "\n".join(out) + "\n"


def build_outline(
    part_name: str,
    trunk_items: list[str],
    score_rows: list[dict],
) -> str:
    """生成方向 C 的 outline.md。"""
    lines: list[str] = []
    lines.append(f"# {part_name} 提纲")
    lines.append("")
    lines.append("> 本提纲由 `generate_outline.py` 基于 "
                 "`scoring_matrix.csv` + `tender_brief.json` 自动生成。")
    lines.append("> 采用方向 C：整体方案主干 + 评分项逐条以独立标题响应。")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 一、整体方案主干
    lines.append("## 一、整体方案主干")
    lines.append("")
    cn_num_prefix = re.compile(r'^[一二三四五六七八九十]+[、．.]\s*')
    paren_prefix = re.compile(r'^[（(][一二三四五六七八九十]+[）)]\s*')
    if trunk_items:
        for i, item in enumerate(trunk_items, 1):
            clean = cn_num_prefix.sub('', item)
            clean = paren_prefix.sub('', clean)
            lines.append(f"### 1.{i} {clean}")
            lines.append("")
    else:
        lines.append("[采购需求主干自动提取失败，需 AI 阶段 4 手工补齐]")
        lines.append("")

    lines.append("[待 AI 阶段 4 重组]")
    lines.append('（本标记为占位，AI 阶段 4 撰写时将下方"评分项响应章节"'
                 '嵌入到主干对应位置，本占位标记届时移除）')
    lines.append("")
    lines.append("---")
    lines.append("")

    # 二、评分项响应章节
    lines.append("## 二、评分项响应章节（逐条响应，阶段 4 嵌入主干）")
    lines.append("")

    total_score = 0.0
    for i, row in enumerate(score_rows, 1):
        item_name = _get_item_name(row)
        score_str = (row.get("分值") or "").strip() or "?"
        keywords = (row.get("关键词") or "").strip()
        row_label = f"R{row['_row_no']:02d}"

        try:
            total_score += float(score_str)
        except ValueError:
            pass

        lines.append(f"### 二.{i} {item_name}（{score_str}分）")
        lines.append("")
        if keywords:
            lines.append(f"- 关键词：{keywords}")
        lines.append(f"- 撰写指引：见 scoring_matrix.csv 行 {row_label}")
        lines.append("")

    # 覆盖度自检
    lines.append("---")
    lines.append("")
    lines.append("## 覆盖度自检")
    lines.append("")
    lines.append("| 矩阵行号 | 评分项 | 分值 | 应答章节 | 归属 Part |")
    lines.append("|---|---|---:|---|---|")
    for i, row in enumerate(score_rows, 1):
        row_label = f"R{row['_row_no']:02d}"
        item_name = _get_item_name(row)
        score_str = (row.get("分值") or "").strip() or "?"
        part = (row.get("评分项归属") or "").strip()
        lines.append(f"| {row_label} | {item_name} | {score_str} "
                     f"| 二.{i} {item_name} | {part} |")

    lines.append("")
    lines.append(f"合计覆盖分值：{total_score:g} 分")
    lines.append("")

    return "\n".join(lines) + "\n"


def _get_item_name(row: dict) -> str:
    """取评分项名称：优先第 2 列，空则用行号占位。"""
    name = (row.get("评分项") or "").strip()
    return name if name else f"[评分项 R{row['_row_no']:02d}]"


def backfill_csv(
    csv_path: Path,
    score_rows: list[dict],
    part_name: str,
) -> tuple[int, int]:
    """回填 scoring_matrix.csv 第 6 列。返回 (changed, skipped)。"""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        all_rows = list(csv.reader(f))

    headers = all_rows[0]
    data = all_rows[1:]
    try:
        chapter_idx = headers.index("应答章节")
    except ValueError:
        print("[错误] scoring_matrix.csv 缺少 '应答章节' 列。",
              file=sys.stderr)
        sys.exit(1)

    # row_no → 章节路径
    chapter_map: dict[int, str] = {}
    for i, row in enumerate(score_rows, 1):
        item_name = _get_item_name(row)
        chapter_map[row["_row_no"]] = f"{part_name} / 二.{i} {item_name}"

    changed = 0
    skipped = 0

    for idx, csv_row in enumerate(data):
        row_no = idx + 1
        if row_no not in chapter_map:
            continue

        current = csv_row[chapter_idx] if len(csv_row) > chapter_idx else ""
        # v2 P13:识别新老两种"不适用"文案,保持向后兼容
        if ("[非 v1.1 范围]" in current) or ("不适用(归属非技术部分" in current):
            skipped += 1
            continue
        if current != chapter_map[row_no]:
            csv_row[chapter_idx] = chapter_map[row_no]
            changed += 1
        else:
            skipped += 1

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows([headers] + data)

    return changed, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description="提纲生成（阶段 3）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("matrix_csv", help="评分矩阵 CSV 路径")
    parser.add_argument("--out", default="output", help="输出目录，默认 output/")
    args = parser.parse_args()

    # V3-3: timing hook
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _timing_hook import stage_timer
    # matrix 在 project/output/scoring_matrix.csv,推 project_dir
    _project_dir = Path(args.matrix_csv).resolve().parent.parent

    with stage_timer("generate_outline", _project_dir):
        _main_body(args)


def _main_body(args) -> None:
    matrix_csv = Path(args.matrix_csv)
    if not matrix_csv.exists():
        print(f"[错误] 找不到评分矩阵: {matrix_csv}", file=sys.stderr)
        sys.exit(1)

    # V53: 未 review 则硬失败
    from brief_schema import ensure_reviewed
    ensure_reviewed(Path(args.out))

    brief_path = matrix_csv.parent / "tender_brief.json"
    if not brief_path.exists():
        print(f"[错误] 找不到 tender_brief.json: {brief_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 加载矩阵，按 brief 中 production_mode 过滤 mode A 行
    all_rows = load_matrix(matrix_csv)
    brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_parts = brief_data.get("response_file_parts", [])
    part_name_map, _ = build_part_maps(brief_parts)
    part_mode_map = {
        name: part["production_mode"]
        for name, part in part_name_map.items()
    }
    mode_a_parts = {name for name, mode in part_mode_map.items() if mode == "A"}
    score_rows: list[dict] = []
    skip_count = 0
    for row in all_rows:
        attr = (row.get("评分项归属") or "").strip()
        if attr and attr in mode_a_parts:
            score_rows.append(row)
        else:
            skip_count += 1

    print(f"[信息] 评分矩阵: {len(all_rows)} 行总计, "
          f"{len(score_rows)} 行 mode A, {skip_count} 行跳过",
          file=sys.stderr)

    if not score_rows:
        print("[警告] 无 mode A 评分项，outline.md 为空骨架。",
              file=sys.stderr)

    # Part 名称（mode A 行应同属一个 Part）
    part_names = set((r.get("评分项归属") or "").strip() for r in score_rows)
    if len(part_names) > 1:
        print(f"[警告] mode A 评分项归属多个 Part: {part_names}，"
              "取第一个。", file=sys.stderr)
    part_name = sorted(part_names)[0] if part_names else "技术响应方案"

    # v2:按 project_type 选模板
    project_type = load_project_type(brief_path)
    template_text = load_outline_template(project_type) if project_type else None

    if template_text:
        print(f"[信息] 检测到 project_type={project_type},使用 "
              f"references/outline_templates/{project_type}/outline_skeleton.md 作为骨架",
              file=sys.stderr)
        outline_text = build_outline_from_template(
            template_text, part_name, score_rows, project_type
        )
    else:
        # 向后兼容:project_type 为空或无效,走旧的"采购需求主干机械截取"逻辑
        if project_type == "":
            print("[警告] extracted.project_type 为空,建议 AI 在阶段 1 Step 2A "
                  "判定并写入(engineering/platform/research/planning/other)。"
                  "本次走旧版采购需求主干机械截取逻辑(向后兼容)。",
                  file=sys.stderr)
        trunk_items = load_procurement_trunk(brief_path)
        print(f"[信息] 采购需求主干: {len(trunk_items)} 条子标题",
              file=sys.stderr)
        outline_text = build_outline(part_name, trunk_items, score_rows)

    outline_path = out_dir / "outline.md"
    outline_path.write_text(outline_text, encoding="utf-8")
    print(f"[完成] 提纲已写入: {outline_path}", file=sys.stderr)

    # 回填 CSV 第 6 列
    changed, skipped = backfill_csv(matrix_csv, score_rows, part_name)
    print(f"[完成] scoring_matrix.csv 第 6 列回填: "
          f"{changed} 条改写, {skipped} 条跳过", file=sys.stderr)

    print()
    print("=" * 60)
    print("阶段 3 完成。下一步:")
    print("  1. 用户复核 outline.md 的主干条目 + 评分项响应章节")
    print("  2. 用户复核 scoring_matrix.csv 第 6 列回填结果")
    print("  3. 确认后进入阶段 4 分章节撰写")
    print("=" * 60)


if __name__ == "__main__":
    main()
