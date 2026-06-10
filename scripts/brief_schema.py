# -*- coding: utf-8 -*-
"""
brief_schema.py · tender_brief.json 字段规范化工具

职责:纯数据格式转换,不做语义推断。
- normalize_part_id: 中文数字/裸数字 → part_NN 格式
- normalize_response_parts: 字段重命名(part_name→name, part_id→id)
- build_part_maps: 构建 name→part / id→part 索引

production_mode / part_attribution 的语义判断是 AI 职责,
脚本只负责校验字段完整性和格式规范性。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


REVIEW_MARKER_FILENAME = 'tender_brief.reviewed'


# v1 (V74/V52/V53 清理): 删除 REGEX_DRAFT_PREFIX 常量 + has_unreviewed_drafts 函数。
# 原因: __REGEX_DRAFT__ 机制是三层验证的遗存,v1 简化为两层验证(AI 读原文直接
#       填 extracted + 用户把关),不再有"脚本初提的 draft 值需要 AI 清理前缀"环节。
# 详见 business_model §8.3 #N16 改写 + §9 skill 模型声明。


def ensure_reviewed(output_dir) -> bool:
    """
    检查 tender_brief 是否已 review。未 review 硬失败。
    下游脚本启动时调用(CLI 入口闸门)。

    v1 后只校验两件事:
    - tender_brief.json 存在
    - tender_brief.reviewed 标记存在

    不再校验 __REGEX_DRAFT__ 前缀(机制已删除)。
    """
    output_dir = Path(output_dir)
    tender_brief_path = output_dir / 'tender_brief.json'
    marker_path = output_dir / REVIEW_MARKER_FILENAME

    if not tender_brief_path.exists():
        raise RuntimeError(
            f"未找到 tender_brief.json: {tender_brief_path}\n"
            f"请先执行阶段 1(parse_tender)。"
        )

    if not marker_path.exists():
        raise RuntimeError(
            f"未找到 review 标记文件: {marker_path}\n"
            f"用户 review 未完成。请按 SKILL.md 阶段 1 Step 3 的 checklist "
            f"逐项核对 tender_brief.json,确认无误后创建此标记文件。\n"
            f"创建命令(PowerShell):\n"
            f"  echo $null > \"{marker_path}\"\n"
            f"创建命令(bash):\n"
            f"  touch \"{marker_path}\""
        )

    return True


# v2 单元 7 P16:函数级闸门(从 CLI 闸门提升)
# 凡调用 brief_schema 内部函数且会读/依赖 brief 数据的路径,都经过这一道闸门,
# 不只依赖 CLI 入口的 ensure_reviewed。

def require_reviewed_for_brief(brief_path) -> bool:
    """
    函数级闸门:由任何读 tender_brief.json 的内部函数在入口调用。
    从 brief_path 推出 output_dir,调 ensure_reviewed。
    """
    brief_path = Path(brief_path)
    # output_dir = brief 文件的父目录
    output_dir = brief_path.parent
    return ensure_reviewed(output_dir)


def load_brief_guarded(brief_path):
    """
    带 review 闸门的 brief 读取 helper。
    所有 brief_schema 内部需要读 brief 的操作,应调此函数而非直接 json.loads。
    """
    import json
    require_reviewed_for_brief(brief_path)
    return json.loads(Path(brief_path).read_text(encoding='utf-8'))


SCORING_MATRIX_COLUMNS = [
    "评分项归属", "评分项", "分值", "评分标准", "关键词",
    "应答章节", "证据材料", "风险提示", "撰写指引", "必备要素",
]


# ──────────────────────────────────────────────────────────
# V60: C 模式 sub_mode 三类
# ──────────────────────────────────────────────────────────

SUB_MODE_VALUES = ['C-template', 'C-reference', 'C-attachment']

# v1 (P2 清理): SUB_MODE_JUDGE_PROMPT 常量迁移到 business_model §8 #N20
# 主 agent 直接读 business_model 判据,不再从脚本常量取 prompt。详见 §9 skill 模型声明。


def validate_sub_mode(part: dict) -> None:
    """
    校验 sub_mode 与 production_mode 的关联约束:
    - production_mode='C' → sub_mode 必须 ∈ SUB_MODE_VALUES
    - production_mode!='C' → sub_mode 必须为 None / 缺失
    不合规 raise ValueError。
    """
    pm = part.get('production_mode')
    sm = part.get('sub_mode')
    name = part.get('name', '<no name>')

    if pm == 'C':
        if sm is None:
            raise ValueError(
                f"Part '{name}' production_mode=C 但 sub_mode 缺失或为 None。"
                f"请按 business_model §8 #N20 判据补齐。"
            )
        if sm not in SUB_MODE_VALUES:
            raise ValueError(
                f"Part '{name}' sub_mode='{sm}' 不在合法值 {SUB_MODE_VALUES} 内。"
            )
    else:
        if sm is not None:
            raise ValueError(
                f"Part '{name}' production_mode='{pm}' 但 sub_mode='{sm}' 非 None。"
                f"sub_mode 仅在 production_mode=C 时有意义。"
            )


def resolve_sub_mode(part: dict) -> str | None:
    """
    下游脚本读取 sub_mode 的统一接口。
    返回 sub_mode 字符串(C 模式 Part)或 None(非 C 模式 Part)。
    校验失败 raise ValueError。
    """
    validate_sub_mode(part)
    return part.get('sub_mode')


# ──────────────────────────────────────────────────────────
# V61: B 模式(材料组装)字段校验
# ──────────────────────────────────────────────────────────

# v1 (P2 清理): B_MODE_EXTRACT_PROMPT 常量迁移到 business_model §8 #N21
# 主 agent 直接读 business_model 组织 assembly_order,不从脚本常量取 prompt。
# 详见 §9 skill 模型声明。


def validate_response_part_b(part: dict) -> None:
    """
    V61: 校验 production_mode='B' 的 Part 字段完整性。
    复用现有 source_anchor schema,不新增字段。
    不合规 raise ValueError。
    """
    pm = part.get('production_mode')
    name = part.get('name', '<no name>')

    if pm != 'B':
        return  # 非 B 模式不做 B 校验

    # B 模式必须有 source_anchor
    sa = part.get('source_anchor')
    if not isinstance(sa, dict):
        raise ValueError(
            f"B 模式 Part '{name}' 缺少 source_anchor 字段(或非 dict)。"
        )

    # source_anchor 必须有 type(V56 引入)
    if sa.get('type') not in ('text', 'table'):
        raise ValueError(
            f"B 模式 Part '{name}' 的 source_anchor.type='{sa.get('type')}'"
            f" 不在合法值 ['text', 'table'] 内。"
        )

    # B 模式不允许有 sub_mode(sub_mode 仅在 C 模式用)
    if 'sub_mode' in part and part.get('sub_mode') is not None:
        raise ValueError(
            f"B 模式 Part '{name}' 不允许 sub_mode 字段"
            f"(当前 sub_mode='{part['sub_mode']}')。sub_mode 仅 C 模式适用。"
        )


# ──────────────────────────────────────────────────────────
# V56: tables 字段 + source_anchor.type 分流
# ──────────────────────────────────────────────────────────

# Table 对象的键清单(文档式 schema,不强制校验)
TABLE_OBJECT_KEYS = [
    'table_id',
    'page_num',
    'headers',
    'rows',
    'evidence',
]

# source_anchor 的 type 取值
SOURCE_ANCHOR_TYPES = ['text', 'table']

# source_anchor 的必填字段随 type 而变化
SOURCE_ANCHOR_REQUIRED = {
    'text': ['type', 'start_line', 'end_line', 'evidence'],
    'table': ['type', 'table_ids', 'evidence'],
}


def validate_source_anchor(anchor: dict) -> str:
    """
    校验 source_anchor 的 type 和必填字段。不合规抛 ValueError。
    返回 anchor 的 type 字符串(兼容旧 schema:缺 type 字段默认 text)。
    """
    anchor_type = anchor.get('type', 'text')
    if anchor_type not in SOURCE_ANCHOR_TYPES:
        raise ValueError(f"unknown source_anchor type: {anchor_type}")

    required = SOURCE_ANCHOR_REQUIRED[anchor_type]
    missing = [k for k in required if k not in anchor]
    # 兼容旧数据:缺 type 但其他必填齐全,只把 type 从 missing 中剔除
    if 'type' in missing and 'type' not in anchor:
        missing = [k for k in missing if k != 'type']
    if missing:
        raise ValueError(
            f"source_anchor (type={anchor_type}) 缺少必填字段: {missing}"
        )
    return anchor_type


def resolve_source_anchor(tender_brief: dict, anchor: dict):
    """
    根据 source_anchor 提取对应内容(V56 下游脚本统一入口)。

    type=text → 返回 [(line_no, text), ...]
    type=table → 返回 [TableObject, ...]
    """
    anchor_type = validate_source_anchor(anchor)

    if anchor_type == 'text':
        start = anchor['start_line']
        end = anchor['end_line']
        raw_lines = tender_brief.get('raw_lines_for_ai', [])
        return [
            (item['line_no'], item['text'])
            for item in raw_lines
            if start <= item.get('line_no', 0) <= end
        ]

    elif anchor_type == 'table':
        table_ids = anchor['table_ids']
        tables = tender_brief.get('tables', [])
        table_map = {t['table_id']: t for t in tables}
        resolved = []
        for tid in table_ids:
            if tid not in table_map:
                raise ValueError(
                    f"source_anchor 引用的 table_id 不存在: {tid}"
                )
            resolved.append(table_map[tid])
        return resolved


_CN_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def normalize_part_id(raw_id: Any, order: int) -> str:
    """将各种 Part ID 格式统一为 part_NN。纯格式转换。"""
    if raw_id is None:
        return f"part_{order:02d}"
    if isinstance(raw_id, int):
        return f"part_{raw_id:02d}"
    text = str(raw_id).strip()
    if re.fullmatch(r"part_\d{2}", text):
        return text
    if re.fullmatch(r"\d+", text):
        return f"part_{int(text):02d}"
    if text in _CN_NUM_MAP:
        return f"part_{_CN_NUM_MAP[text]:02d}"
    return f"part_{order:02d}"


def normalize_response_parts(parts: list[dict]) -> list[dict]:
    """字段重命名(part_name→name, part_id→id)。不填默认 production_mode。"""
    normalized: list[dict] = []
    for idx, part in enumerate(parts, start=1):
        order = int(part.get("order") or idx)
        name = (part.get("name") or part.get("part_name") or "").strip()
        part_id = normalize_part_id(part.get("id") or part.get("part_id"), order)
        production_mode = part.get("production_mode")  # 可能为 None
        entry: dict = {
            "id": part_id,
            "name": name,
            "order": order,
            "production_mode": production_mode,
        }
        # V60: sub_mode 透传(C 模式 Part 必填)
        if "sub_mode" in part:
            entry["sub_mode"] = part["sub_mode"]
        # 透传其他字段(source_anchor 等)
        for key in ("source_anchor", "production_mode_evidence"):
            if key in part:
                entry[key] = part[key]
        normalized.append(entry)
    return normalized


def build_part_maps(
    parts: list[dict],
) -> tuple[dict[str, dict], dict[str, dict]]:
    """构建 name→part 和 id→part 索引。输入可以是原始或已规范化的 parts。"""
    norm = normalize_response_parts(parts)
    name_map: dict[str, dict] = {}
    id_map: dict[str, dict] = {}
    for part in norm:
        if part["name"]:
            name_map[part["name"]] = part
        id_map[part["id"]] = part
    return name_map, id_map
