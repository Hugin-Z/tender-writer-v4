# -*- coding: utf-8 -*-
"""
update_score_positions.py · 评分项粗位置重算（独立于 parse_tender.py）

用法:
    run_script.bat update_score_positions.py <tender_brief.json 路径>

功能:
    读已有 tender_brief.json 的 section_anchors（需已由 AI 填充），
    从同目录 tender_raw.txt 重算 score_items_raw_positions，
    精准写回 JSON 只改 score_items_raw_positions 键。

前置条件:
    - tender_brief.json 已存在（parse_tender.py 首次运行产出）
    - section_anchors 非空（AI 阶段 1 Step 2 已标注）
    - tender_raw.txt 存在于同目录
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 复用 parse_tender.py 的评分项切片函数
sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse_tender import extract_score_items_raw_positions


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: update_score_positions.py <tender_brief.json 路径>",
              file=sys.stderr)
        sys.exit(1)

    json_path = Path(sys.argv[1])
    if not json_path.exists():
        print(f"[错误] 找不到 {json_path}。请先跑 parse_tender.py 首次运行。",
              file=sys.stderr)
        sys.exit(1)

    # V53: 未 review 则硬失败(json_path 父目录即 output 目录)
    from brief_schema import ensure_reviewed
    ensure_reviewed(json_path.parent)

    data = json.loads(json_path.read_text(encoding="utf-8"))

    if not data.get("section_anchors"):
        print("[错误] section_anchors 为空。请先完成 Step 2 section_anchors 标注。",
              file=sys.stderr)
        sys.exit(1)

    raw_path = json_path.parent / "tender_raw.txt"
    if not raw_path.exists():
        print(f"[错误] 同目录缺 tender_raw.txt: {raw_path}",
              file=sys.stderr)
        sys.exit(1)

    raw_text = raw_path.read_text(encoding="utf-8")

    print("[信息] 正在重算 score_items_raw_positions...", file=sys.stderr)
    new_positions = extract_score_items_raw_positions(
        raw_text, data["section_anchors"]
    )

    data["score_items_raw_positions"] = new_positions
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[完成] score_items_raw_positions 已更新（{len(new_positions)} 条切片）")


if __name__ == "__main__":
    main()
