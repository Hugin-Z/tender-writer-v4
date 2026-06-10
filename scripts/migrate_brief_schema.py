# -*- coding: utf-8 -*-
"""
migrate_brief_schema.py · tender_brief.json 旧→新 schema 迁移

用法:
    ./run_script.bat migrate_brief_schema.py <tender_brief.json 路径> [--backup]

检测旧 schema 特征:
    response_file_parts 含 part_id/part_name/responsibility 字段
    但无 name/production_mode 字段

迁移操作:
    - part_id(中文数字) → id(part_NN 格式)
    - part_name → name
    - source_location 字符串 → source_anchor{start_line, end_line, evidence}
    - 新增 production_mode = "__PENDING_AI__"
    - 每条 score_items_raw_positions 新增 part_attribution = "__PENDING_AI__"
    - 保留 responsibility/internal_structure_hint 等旧字段(不删)

迁移后 AI 需要:
    1. 按 SKILL.md 阶段 1 Step 5 补齐 production_mode
    2. 按 SKILL.md 阶段 1 Step 6 补齐 part_attribution
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brief_schema import (
    normalize_part_id,
    SCORING_MATRIX_COLUMNS,
    SUB_MODE_VALUES,
    validate_sub_mode,
)


def _parse_source_location(loc: str) -> dict:
    """尝试将 source_location 字符串解析为 source_anchor。"""
    m = re.search(r"L(\d+)\s*[-–—]\s*L(\d+)", loc)
    if m:
        return {
            "start_line": int(m.group(1)),
            "end_line": int(m.group(2)),
            "evidence": loc.strip(),
        }
    return {"start_line": 0, "end_line": 0, "evidence": loc.strip()}


def detect_old_schema(parts: list[dict]) -> bool:
    """检测是否为旧 schema（含 part_id/part_name 但无 production_mode）。"""
    if not parts:
        return False
    sample = parts[0]
    has_old = "part_name" in sample or "part_id" in sample or "responsibility" in sample
    has_new = "production_mode" in sample and sample["production_mode"] not in (None, "", "__PENDING_AI__")
    return has_old and not has_new


def migrate(data: dict) -> dict:
    """就地迁移 tender_brief.json。返回迁移统计。"""
    parts = data.get("response_file_parts", [])
    stats = {"renamed": 0, "pending": 0, "preserved": []}

    for idx, part in enumerate(parts):
        order = int(part.get("order") or (idx + 1))

        # id 规范化
        raw_id = part.get("id") or part.get("part_id")
        new_id = normalize_part_id(raw_id, order)
        if "part_id" in part and "id" not in part:
            part["id"] = new_id
            stats["renamed"] += 1
        elif "id" not in part:
            part["id"] = new_id

        # name 规范化
        if "part_name" in part and "name" not in part:
            part["name"] = part["part_name"]
            stats["renamed"] += 1
        elif "name" not in part:
            part["name"] = ""

        # source_anchor
        if "source_location" in part and "source_anchor" not in part:
            part["source_anchor"] = _parse_source_location(str(part["source_location"]))
            stats["renamed"] += 1

        # production_mode
        if not part.get("production_mode") or part.get("production_mode") == "__PENDING_AI__":
            part["production_mode"] = "__PENDING_AI__"
            stats["pending"] += 1

        # order
        if "order" not in part:
            part["order"] = order

        # 记录保留的旧字段
        for old_key in ("part_id", "part_name", "responsibility",
                        "internal_structure_hint", "source_location"):
            if old_key in part:
                if old_key not in stats["preserved"]:
                    stats["preserved"].append(old_key)

    # score_items_raw_positions 补 part_attribution
    for item in data.get("score_items_raw_positions", []):
        if not item.get("part_attribution") or item.get("part_attribution") == "__PENDING_AI__":
            item["part_attribution"] = "__PENDING_AI__"
            stats["pending"] += 1

    return stats


def migrate_tender_brief(tender_brief: dict) -> bool:
    """
    V56: 把旧版 tender_brief.json(baseline v7 schema)迁移到新版。

    迁移动作:
    1. 新增 tables 字段(空列表,真实填充由重跑 parse_tender 完成)
    2. 遍历 response_file_parts,为每个 source_anchor 补 type='text'

    返回 True = 有修改, False = 无需迁移(幂等)。
    本函数仅定义,不被自动调用——作为手动修复脱钩状态的应急工具。
    """
    changed = False

    # 步骤 1: tables 字段
    if 'tables' not in tender_brief:
        tender_brief['tables'] = []
        changed = True

    # 步骤 2: source_anchor.type 补齐
    parts = tender_brief.get('response_file_parts', [])
    for part in parts:
        anchor = part.get('source_anchor')
        if isinstance(anchor, dict) and 'type' not in anchor:
            anchor['type'] = 'text'
            changed = True

    return changed


def migrate_v10_to_v11(tender_brief: dict, sub_mode_judgments: dict[int, str]) -> bool:
    """
    V60: 为 production_mode='C' 的 Part 写入 sub_mode 字段(终值,无 draft 前缀)。

    sub_mode_judgments: {part_index: sub_mode_value}
        由调用方(AI 角色)提供。AI 应基于 business_model §8 #N20 判据判定每个
        production_mode='C' 的 Part 的 sub_mode 取值。

    幂等:已迁移过的 json 再跑一次,如果 judgments 与现状一致则不变化。
    返回 True = 有修改, False = 无变化。

    硬约束:
    - production_mode='C' 的 Part 必须在 sub_mode_judgments 中
    - production_mode 非 C 的 Part 不允许有 sub_mode
    - 判定为 C-attachment 的 raise NotImplementedError(挂档)
    - 判定值必须 ∈ SUB_MODE_VALUES
    """
    parts = tender_brief.get('response_file_parts', [])
    changed = False

    for idx, part in enumerate(parts):
        pm = part.get('production_mode')
        if pm == 'C':
            if idx not in sub_mode_judgments:
                raise ValueError(
                    f"Part[{idx}] '{part.get('name')}' production_mode=C 但 "
                    f"sub_mode_judgments 中缺少 part_index={idx} 的判定值。\n"
                    f"请按 business_model §8 #N20 判据判定 sub_mode"
                )
            new_sm = sub_mode_judgments[idx]
            if new_sm not in SUB_MODE_VALUES:
                raise ValueError(
                    f"Part[{idx}] sub_mode 判定值 '{new_sm}' 不在合法值"
                    f" {SUB_MODE_VALUES} 内"
                )
            if new_sm == 'C-attachment':
                raise NotImplementedError(
                    f"Part[{idx}] '{part.get('name')}' 判定为 C-attachment, "
                    f"当前挂档,见 business_model §8 #N20。请用户决定如何处理。"
                )
            if part.get('sub_mode') != new_sm:
                part['sub_mode'] = new_sm
                changed = True
        else:
            # 非 C 模式 Part 不允许有 sub_mode
            if 'sub_mode' in part and part['sub_mode'] is not None:
                raise ValueError(
                    f"Part[{idx}] '{part.get('name')}' production_mode='{pm}'"
                    f" 但已有 sub_mode='{part['sub_mode']}'。"
                    f"非 C 模式 Part 不允许 sub_mode。"
                )

    # 校验所有 Part 都通过 validate_sub_mode
    for part in parts:
        validate_sub_mode(part)

    return changed


def migrate_scoring_matrix(csv_path: Path, *, backup: bool = False,
                           target_columns: list[str] | None = None) -> dict | None:
    """
    将 scoring_matrix.csv 从旧 schema 迁移到当前 schema,保留所有已有
    列数据。按列名匹配回填,不按位置匹配。

    返回迁移统计 dict,若无需迁移返回 None。
    """
    import csv as csv_mod

    if not csv_path.exists():
        return None

    if target_columns is None:
        target_columns = SCORING_MATRIX_COLUMNS

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv_mod.DictReader(f)
        existing_headers = reader.fieldnames or []
        existing_rows = list(reader)

    if not existing_rows:
        return None

    missing_cols = [c for c in target_columns if c not in existing_headers]
    extra_cols = [c for c in existing_headers if c not in target_columns]

    if not missing_cols and not extra_cols:
        return None

    if backup:
        bak = csv_path.with_suffix(".csv.bak")
        shutil.copy2(csv_path, bak)

    if extra_cols:
        print(f"[warn] 发现当前 schema 不包含的列:{extra_cols},保留原值",
              file=sys.stderr)

    # 构造新行:按列名匹配,缺失列填 __PENDING_AI__
    output_headers = list(target_columns) + list(extra_cols)
    new_rows = []
    for old_row in existing_rows:
        new_row = {}
        for col in output_headers:
            if col in existing_headers:
                new_row[col] = old_row.get(col, "")
            else:
                new_row[col] = "__PENDING_AI__"
        new_rows.append(new_row)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=output_headers)
        writer.writeheader()
        writer.writerows(new_rows)

    return {
        "rows_migrated": len(new_rows),
        "old_cols": len(existing_headers),
        "new_cols": len(output_headers),
        "added_cols": missing_cols,
        "extra_cols": extra_cols,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="tender_brief.json 旧→新 schema 迁移",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("json_path", help="tender_brief.json 路径")
    parser.add_argument("--backup", action="store_true",
                        help="迁移前备份原文件为 .bak")
    args = parser.parse_args()

    json_path = Path(args.json_path)
    if not json_path.exists():
        print(f"[错误] 找不到: {json_path}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    parts = data.get("response_file_parts", [])

    if not parts:
        print("[信息] response_file_parts 为空,无需迁移。")
        return

    if not detect_old_schema(parts):
        # 检查是否已经有 __PENDING_AI__
        pending = sum(1 for p in parts if p.get("production_mode") == "__PENDING_AI__")
        if pending > 0:
            print(f"[信息] 已迁移过（{pending} 个 __PENDING_AI__ 待 AI 补齐）。")
        else:
            print("[信息] 已是新 schema,无需迁移。")
        return

    if args.backup:
        bak = json_path.with_suffix(".json.bak")
        shutil.copy2(json_path, bak)
        print(f"[信息] 已备份到: {bak}")

    stats = migrate(data)

    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[完成] 迁移成功:")
    print(f"  字段重命名: {stats['renamed']} 处")
    print(f"  __PENDING_AI__ 占位: {stats['pending']} 处")
    if stats["preserved"]:
        print(f"  保留的旧字段: {', '.join(stats['preserved'])}")
    print()
    print("下一步:")
    print("  1. 按 SKILL.md 阶段 1 Step 5 由 AI 补齐 production_mode")
    print("  2. 按 SKILL.md 阶段 1 Step 6 由 AI 补齐 part_attribution")


if __name__ == "__main__":
    main()
