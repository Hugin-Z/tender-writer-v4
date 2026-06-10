# -*- coding: utf-8 -*-
"""
check_chapter.py · 章节自检脚本（阶段 4 撰写后必跑）

用法:
    run_script.bat check_chapter.py <章节markdown路径>
        --brief <tender_brief.json路径>
        --matrix <scoring_matrix.csv路径>

检查项:
    [1] Part 边界声明
    [2] 标题关键词覆盖
    [3] 字数自检（硬约束）
    [4] 图占位符规范
    [5] 履约前置条件句式
    [6] 必备要素覆盖
    [7] AI 输出空格规范(v2 单元 2,ai_output_rules.md R3)
    [8] 正文级缝合句检测(V3-4,扩展 [2] 标题级 cheat 到正文)
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
from count_words import count_markdown


# ─────────────────────────────────────────────
# 检查 1: Part 边界声明
# ─────────────────────────────────────────────

def check_part_declaration(
    text: str,
    md_path: Path,
    brief_parts: list[dict],
) -> tuple[str, str]:
    """返回 (status, detail)。status: pass/fail/warn"""
    if "<!-- Part" not in text and "<!-- part" not in text.lower():
        return "fail", "缺失 Part 边界声明注释块"
    part_id_match = re.search(r"part_id:\s*(part_\d+)", text)
    if not part_id_match:
        return "warn", "Part 边界声明存在但 part_id 格式异常"

    part_name_match = re.search(r"本章属于:([^(<\r\n]+)\(part_id:", text)
    declared_part_name = part_name_match.group(1).strip() if part_name_match else ""
    declared_part_id = part_id_match.group(1)

    _, part_id_map = build_part_maps(brief_parts)
    part = part_id_map.get(declared_part_id)
    if not part:
        return "fail", f"part_id: {declared_part_id} 不存在于 tender_brief.json"
    if part["production_mode"] != "A":
        return "fail", f"part_id: {declared_part_id} 属于 {part['production_mode']}，阶段 4 不应写正文"
    if declared_part_name and declared_part_name != part["name"]:
        return "warn", (f"part_id: {declared_part_id} 对应 Part 名应为 "
                        f"'{part['name']}'，当前注释写为 '{declared_part_name}'")

    parent_part_id = md_path.parent.name
    if parent_part_id.startswith("part_") and parent_part_id != declared_part_id:
        return "fail", (f"章节目录位于 {parent_part_id}/，但声明的 part_id 为 "
                        f"{declared_part_id}")

    if "语言体系:技术语言" not in text:
        return "warn", f"part_id: {declared_part_id} 已匹配，但缺少技术语言声明"
    return "pass", f"part_id: {declared_part_id} -> {part['name']}"


# ─────────────────────────────────────────────
# 检查 2: 标题关键词覆盖
# ─────────────────────────────────────────────

def check_title_keywords(
    text: str,
    md_name: str,
    matrix_rows: list[dict],
) -> tuple[str, str]:
    """从文件名模糊匹配评分项，检查关键词在标题中的命中。"""
    # 提取文件名中文部分
    name_match = re.search(r"chapter_\d+_(.+)\.md$", md_name)
    cn_name = name_match.group(1) if name_match else ""

    # 找匹配的评分项行
    matched_row = None
    for row in matrix_rows:
        item = (row.get("评分项") or "").strip()
        if not item and not cn_name:
            continue
        # 模糊匹配：文件名中文 ⊆ 评分项名 或 评分项名 ⊆ 文件名中文
        if cn_name and (cn_name in item or item in cn_name):
            matched_row = row
            break
    # 也尝试用关键词反查
    if not matched_row and cn_name:
        for row in matrix_rows:
            kws = (row.get("关键词") or "").strip()
            if kws and any(k.strip() in cn_name for k in re.split(r"[;；、/]+", kws)):
                matched_row = row
                break

    if not matched_row:
        return "warn", f"未能从文件名 '{cn_name}' 匹配到评分项，跳过关键词检查"

    keywords_str = (matched_row.get("关键词") or "").strip()
    if not keywords_str:
        return "warn", "匹配到评分项但关键词列为空"

    kws = [k.strip() for k in re.split(r"[;；、/]+", keywords_str) if k.strip()]

    # 收集标题行
    headings = []
    for line in text.splitlines():
        if line.startswith("#"):
            headings.append(line.lstrip("#").strip())

    hit = []
    miss = []
    for kw in kws:
        if any(kw in h for h in headings):
            hit.append(kw)
        else:
            miss.append(kw)

    if not hit:
        return "fail", f"0/{len(kws)} 关键词命中标题: {'/'.join(kws)}"

    # v2:缝合句作弊检测(标题级)
    # 如果某一行标题里同时命中 ≥ 3 个关键词,且这些关键词挤在 ≤ 20 字窗口内,
    # 判定为"缝合句作弊"——AI 为凑覆盖率把多个关键词硬塞在同一短句里,
    # 不是有实义的段落标题。
    #
    # TODO(v2.1 候选):正文级缝合句检测尚未覆盖。
    # 当前只检测 # 开头的标题行;正文段落里如果出现"审核质量控制措施风险管理制度工作程序标准方法"
    # 这种 8 关键词 ≤30 字的缝合句,不会被本检查抓到。
    # 扩展方案:扫所有段落,对 scoring_matrix 第 5 列所有关键词做滑窗统计;
    # 但需要考虑列表项、表头的"枚举式堆叠"误判率,阈值需要更保守。
    cheat_hits = []
    for h in headings:
        matched = []
        for kw in kws:
            idx = h.find(kw)
            if idx >= 0:
                matched.append((idx, kw, idx + len(kw)))
        if len(matched) >= 3:
            sorted_by_start = sorted(matched, key=lambda m: m[0])
            span = sorted_by_start[-1][2] - sorted_by_start[0][0]
            title_len = len(h)
            # 短标题(≤20 字)内塞 ≥3 关键词,且窗口跨度 ≤ 20,视为作弊
            if span <= 20 and title_len <= 30:
                cheat_hits.append((h[:60], [m[1] for m in matched], span))

    detail = f"{len(hit)}/{len(kws)} 命中: {'/'.join(hit)}"
    if miss:
        detail += f" | 未命中: {'/'.join(miss)}"

    if cheat_hits:
        cheat_lines = [f"L'{h}' 挤入 {'/'.join(kws_in)} 跨度 {span} 字"
                       for h, kws_in, span in cheat_hits]
        detail += ("\n        [缝合句作弊告警] " + " | ".join(cheat_lines[:2]) +
                   "\n        见 ai_output_rules.md R7")
        return "fail", detail

    if len(hit) <= 2 and len(kws) > 2:
        return "pass", detail + "(覆盖率偏低)"
    return "pass", detail


# ─────────────────────────────────────────────
# 检查 3: 字数自检
# ─────────────────────────────────────────────

def check_word_count(
    text: str,
    md_name: str,
    matrix_rows: list[dict],
    total_tech_score: float = 50.0,
    total_pages: float = 80.0,
) -> tuple[str, str]:
    """按篇幅基准分档检查字数。"""
    stats = count_markdown(text)
    actual = stats["total"]
    table_ratio = stats["table_ratio"]

    # 判断章节类型
    if table_ratio >= 60:
        ch_type = "表格密集"
        words_per_page = 250
    elif table_ratio >= 30:
        ch_type = "图表"
        words_per_page = 350
    else:
        ch_type = "偏文字"
        words_per_page = 500

    # 找匹配的评分项分值
    name_match = re.search(r"chapter_\d+_(.+)\.md$", md_name)
    cn_name = name_match.group(1) if name_match else ""
    score_val = 0.0
    for row in matrix_rows:
        item = (row.get("评分项") or "").strip()
        kws = (row.get("关键词") or "").strip()
        if cn_name and (cn_name in item or item in cn_name):
            try:
                score_val = float(row.get("分值") or 0)
            except ValueError:
                pass
            break
        if cn_name and kws and any(k.strip() in cn_name for k in re.split(r"[;；、/]+", kws)):
            try:
                score_val = float(row.get("分值") or 0)
            except ValueError:
                pass
            break

    if score_val <= 0:
        return "warn", f"未找到对应分值，跳过字数检查（实际 {actual} 字）"

    target_pages = score_val / total_tech_score * total_pages
    target_words = int(target_pages * words_per_page)
    lower = int(target_words * 0.8)
    upper = int(target_words * 1.2)

    detail = (f"实际 {actual}，目标 {target_words}"
              f"（{score_val}分/{total_tech_score}分 x {total_pages}页"
              f" = {target_pages:.0f}页 x {words_per_page}字/页）"
              f"\n        表格行占比: {table_ratio:.0f}%（{ch_type}章节）")

    if actual < lower:
        return "fail", f"字数不达标，必须扩写。{detail}"
    if actual > upper:
        return "warn", f"字数超标，建议精简。{detail}"
    return "pass", detail


# ─────────────────────────────────────────────
# 检查 4: 图占位符规范
# ─────────────────────────────────────────────

FIGURE_PATTERN = re.compile(r"^\s*\*\*【图\s+\d+\.\d+[:：].+】\*\*\s*$")


def check_figures(text: str, table_ratio: float) -> tuple[str, str]:
    """
    v2:检查图占位符**格式**。

    变更:取消了原来的"数量硬指标"(期望 3-15 张),改为只要求:
    - 每个 `**【图 N.M:标题】**` 标记格式合法
    - 真正的"图占位区块渲染"在单元 4 docx_builder 落地,check 这里只管 markdown 层
    """
    lines = text.splitlines()
    figures = []
    bad_format = []

    for i, line in enumerate(lines, 1):
        if "【图" in line and "**" in line:
            figures.append((i, line.strip()))
            if not FIGURE_PATTERN.match(line):
                bad_format.append(f"L{i}: {line.strip()[:60]}")

    count = len(figures)
    details = [f"{count} 个图占位符"]
    status = "pass"

    if bad_format:
        details.append(f"格式异常 {len(bad_format)} 处(应为 `**【图 N.M:标题】**`)")
        status = "warn"

    return status, ",".join(details)


# ─────────────────────────────────────────────
# 检查 5: 履约前置条件免责句式
# ─────────────────────────────────────────────

DISCLAIMER_PATTERNS = [
    re.compile(r"前提是.{0,30}提供"),
    re.compile(r"如.{0,20}未提供.{0,30}"),
    re.compile(r"若甲方.{0,30}不"),
    re.compile(r"由.{0,10}承担相应"),
]


def check_disclaimer(text: str) -> tuple[str, str]:
    """检查免责句式。"""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat in DISCLAIMER_PATTERNS:
            if pat.search(line):
                hits.append(f"L{i}: {line.strip()[:60]}")
                break

    if hits:
        detail = f"{len(hits)} 处免责句式: " + " | ".join(hits[:3])
        if len(hits) > 3:
            detail += f" ...+{len(hits) - 3}"
        return "warn", detail
    return "pass", "0 处免责句式"


# ─────────────────────────────────────────────
# 检查 7: AI 输出空格规范(v2 单元 2,实现 ai_output_rules.md R3)
# ─────────────────────────────────────────────
#
# 中文标书内文中,中文-数字、中文-英文、数字-中文、英文-中文之间不得加空格。
# 特例:代码块、HTML 注释、markdown 表格分隔符 |、列表项引导符、公式/URL 不检查。

SPACE_PATTERNS = [
    (re.compile(r"[一-鿿][ \t]+\d"), "中文后接空格后接数字"),
    (re.compile(r"\d[ \t]+[一-鿿]"), "数字后接空格后接中文"),
    (re.compile(r"[一-鿿][ \t]+[A-Za-z]"), "中文后接空格后接英文"),
    (re.compile(r"[A-Za-z][ \t]+[一-鿿]"), "英文后接空格后接中文"),
]


def _strip_non_prose(line: str) -> str:
    """去除一行里不应该参与空格检查的片段:
    - markdown 内联代码 `...`
    - markdown 链接/图片 url 片段
    - 全英文/纯代码/公式片段(简化处理:不做)
    """
    line = re.sub(r"`[^`]+`", "", line)
    line = re.sub(r"\[[^\]]*\]\([^\)]+\)", "", line)
    return line


def check_whitespace_rule(text: str) -> tuple[str, str]:
    """
    ai_output_rules.md R3 实现:中文-数字/中文-英文等之间不允许空格。

    返回(v2 反馈后调整阈值):
      - pass  : 命中 0 处
      - warn  : 命中 1-2 处(个别疏漏)
      - fail  : 命中 ≥ 3 处(阻塞;3 处是"AI 排版失守"的下限信号)

    跳过:代码块(```)、HTML 注释(<!-- -->)、markdown 表格行(以 | 开头或分隔符行)、
    列表引导符附近的空格。
    """
    lines = text.splitlines()
    in_code_block = False
    hits: list[tuple[int, str, str]] = []

    for i, line in enumerate(lines, 1):
        # 跳过代码块
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        # 跳过 HTML 注释
        if line.strip().startswith("<!--") and line.strip().endswith("-->"):
            continue
        stripped = line.strip()
        # 跳过 markdown 表格行(含 |)和分隔符行
        if stripped.startswith("|") or re.match(r"^\|?\s*:?-+", stripped):
            continue
        # 跳过 ATX heading(# 开头) — 章节编号和中文标题之间的空格习惯允许
        if stripped.startswith("#"):
            continue
        # 跳过图/表占位符行 "**【图 X.X:xxx】**" / "**【表 X.X:...】**"
        if re.match(r"^\*\*【图表]\s*[\d.]+[:：]", stripped):
            continue
        if stripped.startswith("**【") and stripped.endswith("】**"):
            continue

        probe = _strip_non_prose(line)
        # 跳过列表引导符的空格("- 内容" / "1. 内容" 的空格是 markdown 语法)
        probe = re.sub(r"^\s*[-*+][ \t]+", "", probe)
        probe = re.sub(r"^\s*\d+\.[ \t]+", "", probe)
        # 跳过行首 "**粗体开头** " 后的空格(强调修饰符)
        probe = re.sub(r"^\s*\*\*[^*]+\*\*[ \t]*[:：]?[ \t]*", "", probe)
        # 跳过 "N.N.N 子小节" 的章节编号起始(无 # 前缀的"编号+标题"结构,如"1.5.1 核心难点")
        probe = re.sub(r"^\s*\d+(\.\d+)+[ \t]+", "", probe)

        for pat, kind in SPACE_PATTERNS:
            m = pat.search(probe)
            if m:
                hits.append((i, kind, probe[max(0, m.start() - 5):m.end() + 5]))
                break  # 每行只记一条

    if not hits:
        return "pass", "0 处空格规范违反"

    detail_lines = [f"L{ln}: {kind}  ...{snippet}..."
                    for ln, kind, snippet in hits[:5]]
    detail = f"{len(hits)} 处空格规范违反:\n" + "\n".join(detail_lines)
    if len(hits) > 5:
        detail += f"\n...+{len(hits) - 5} 处未列出"
    detail += "\n规则:references/ai_output_rules.md R3"

    if len(hits) >= 3:
        return "fail", detail
    return "warn", detail


# ─────────────────────────────────────────────
# 检查 8: 正文级缝合句检测(V3-4)
# ─────────────────────────────────────────────
#
# 扩展 [2] 标题级 cheat 检测到正文段落。算法:
# 1. 收集 scoring_matrix 第 5 列所有关键词
# 2. 对正文段落(跳过表格/列表/标题/代码块/图占位/nolint 注释下一段)做滑窗
# 3. window 字内含 ≥threshold_fail 个不同关键词 → fail
#    含 ≥threshold_warn 个不同关键词 → warn
#
# 默认阈值 warn=5 / fail=6 / window=30 字(plan 初值 4/5,demo 烟测调到 5/6
# 消除误报 fail。护栏未触发,1 档自动调整)。误报处置:
# - 单点忽略:在段落上方加 <!-- nolint:stitching --> 注释
# - 全局调阈值:--stitching-threshold-warn / --stitching-threshold-fail
# - 调窗口:--stitching-window


def check_content_keyword_stitching(
    text: str,
    matrix_rows: list[dict],
    window: int = 30,
    threshold_warn: int = 5,
    threshold_fail: int = 6,
) -> tuple[str, str]:
    """V3-4: 正文级缝合句检测。

    阈值演化:plan 初值 4 warn / 5 fail,demo 5 章烟测 1 章误报 fail
    (chapter_01 自然介绍句 5 关键词压一句)→ 1 档调整到 5 warn / 6 fail。
    护栏未触发(误报 fail 1/5=20% 在 ≥3/6 阈值下)。
    """
    # 收集关键词
    all_kws: set[str] = set()
    for row in matrix_rows:
        kws_str = (row.get("关键词") or "").strip()
        if kws_str:
            for kw in re.split(r"[;；、/]+", kws_str):
                kw = kw.strip()
                if len(kw) >= 2:
                    all_kws.add(kw)

    if not all_kws:
        return "warn", "scoring_matrix 无关键词,跳过缝合句检测"

    lines = text.splitlines()
    hits: list[tuple[int, str, str, list[str]]] = []
    in_code_block = False
    skip_next_prose = False  # nolint:stitching 触发的"跳过下一段"状态

    for ln_no, line in enumerate(lines, 1):
        stripped = line.strip()

        # 代码块开关
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # nolint 标记:消费当前行 + 设置下一段跳过
        if stripped == "<!-- nolint:stitching -->":
            skip_next_prose = True
            continue

        if not stripped:
            continue

        # 其他 HTML 注释
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            continue

        # 表格行 / 表格分隔符
        if stripped.startswith("|") or re.match(r"^\|?\s*:?-+", stripped):
            continue

        # 标题(# 开头)— [2] 标题级 cheat 已覆盖
        if stripped.startswith("#"):
            continue

        # 列表(- / * / 1.)— 枚举式堆叠是合理用法
        if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+\.\s", line):
            continue

        # 图占位符 **【图 X.X:...】**
        if stripped.startswith("**【") and stripped.endswith("】**"):
            continue

        # nolint 触发的"跳过下一非空非结构段"
        if skip_next_prose:
            skip_next_prose = False
            continue

        # 找当前行所有关键词命中
        matched: list[tuple[int, str]] = []
        for kw in all_kws:
            start = 0
            while True:
                idx = stripped.find(kw, start)
                if idx < 0:
                    break
                matched.append((idx, kw))
                start = idx + 1

        if len(matched) < threshold_warn:
            continue

        # 按位置排序
        matched.sort(key=lambda m: m[0])

        # 滑窗:任意起点 a 找最远 b,使 (b.start - a.start) ≤ window;
        # 该 [a, b] 区间含的不同关键词数即该窗口的命中数
        max_count = 0
        max_subset: list[str] = []
        for a in range(len(matched)):
            seen: set[str] = set()
            for b in range(a, len(matched)):
                if matched[b][0] - matched[a][0] > window:
                    break
                seen.add(matched[b][1])
            if len(seen) > max_count:
                max_count = len(seen)
                max_subset = sorted(seen)

        if max_count >= threshold_fail:
            hits.append((ln_no, "fail", stripped[:60], max_subset))
        elif max_count >= threshold_warn:
            hits.append((ln_no, "warn", stripped[:60], max_subset))

    if not hits:
        return (
            "pass",
            f"0 处缝合句嫌疑(阈值 warn={threshold_warn}/fail={threshold_fail},窗口 {window} 字)"
        )

    fail_count = sum(1 for h in hits if h[1] == "fail")
    warn_count = sum(1 for h in hits if h[1] == "warn")

    detail_lines = []
    for ln_no, status, snippet, kws in hits[:5]:
        icon = "失败" if status == "fail" else "警告"
        kw_str = "/".join(kws[:5]) + ("..." if len(kws) > 5 else "")
        detail_lines.append(f"L{ln_no} [{icon}]: 命中 {len(kws)} 关键词 ({kw_str}) 在 ≤{window} 字窗口")

    detail = (
        f"{fail_count} 失败 + {warn_count} 警告(阈值 warn={threshold_warn}/"
        f"fail={threshold_fail})\n        "
        + "\n        ".join(detail_lines)
    )
    if len(hits) > 5:
        detail += f"\n        ... +{len(hits) - 5} 处未列出"
    detail += (
        "\n        见 ai_output_rules.md R7 缝合句作弊扩展;如属合理段落,"
        "加 `<!-- nolint:stitching -->` 单点忽略,或调 "
        "`--stitching-threshold-fail` / `--stitching-window`"
    )

    if fail_count > 0:
        return "fail", detail
    return "warn", detail


# ─────────────────────────────────────────────
# 检查 6: 必备要素覆盖
# ─────────────────────────────────────────────

def check_mandatory_elements(
    text: str,
    md_name: str,
    matrix_rows: list[dict],
    strict: bool = False,
) -> tuple[str, str]:
    """检查章节是否包含评分项绑定的必备要素。"""
    name_match = re.search(r"chapter_\d+_(.+)\.md$", md_name)
    cn_name = name_match.group(1) if name_match else ""

    matched_row = None
    for row in matrix_rows:
        item = (row.get("评分项") or "").strip()
        if cn_name and (cn_name in item or item in cn_name):
            matched_row = row
            break
    if not matched_row and cn_name:
        for row in matrix_rows:
            kws = (row.get("关键词") or "").strip()
            if kws and any(k.strip() in cn_name for k in re.split(r"[;；、/]+", kws)):
                matched_row = row
                break

    if not matched_row:
        return "warn", "未匹配到评分项，跳过必备要素检查"

    elements_str = (matched_row.get("必备要素") or "").strip()
    if not elements_str or elements_str == "__PENDING_AI__":
        return "warn", "必备要素列为空或待填充，跳过检查"

    elements = [e.strip() for e in re.split(r"[;；、/]+", elements_str) if e.strip()]
    if not elements:
        return "warn", "必备要素解析为空列表"

    hit = [e for e in elements if e in text]
    miss = [e for e in elements if e not in text]

    if not miss:
        return "pass", f"{len(hit)}/{len(elements)} 必备要素全部命中"

    rate = len(hit) / len(elements) * 100
    detail = f"{len(hit)}/{len(elements)} 命中({rate:.0f}%)"
    if miss:
        detail += f"\n        未命中: {'; '.join(miss)}"

    threshold = 100.0 if strict else 80.0
    if rate < threshold:
        return "fail", f"必备要素覆盖不足({threshold:.0f}% 门槛)。{detail}"
    return "pass", detail


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="章节自检脚本（阶段 4 撰写后必跑）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("md_path", help="章节 markdown 文件路径")
    parser.add_argument("--brief", required=True, help="tender_brief.json 路径")
    parser.add_argument("--matrix", required=True, help="scoring_matrix.csv 路径")
    parser.add_argument("--tech-score", type=float, default=50.0,
                        help="技术评分总分(默认 50)")
    parser.add_argument("--pages", type=float, default=80.0,
                        help="技术响应方案目标总页数(默认 80)")
    parser.add_argument("--strict-elements", action="store_true",
                        help="必备要素检查使用严格模式(100%% 命中才通过)")
    parser.add_argument("--legacy-mode", action="store_true",
                        help="向后兼容模式:v2 新增的严格检查(字数 fail/缝合句 fail/"
                             "空格 fail)降级为 warn。老项目复检时启用,避免突然不通过。")
    # V3-4: 正文级缝合句检测阈值
    parser.add_argument("--stitching-window", type=int, default=30,
                        help="V3-4 正文缝合检测的滑窗字数(默认 30)")
    parser.add_argument("--stitching-threshold-warn", type=int, default=5,
                        help="V3-4 正文缝合检测 warn 阈值(默认 5 关键词;"
                             "plan 初值 4,demo 烟测调到 5 消除误报 fail)")
    parser.add_argument("--stitching-threshold-fail", type=int, default=6,
                        help="V3-4 正文缝合检测 fail 阈值(默认 6 关键词;"
                             "plan 初值 5,demo 烟测调到 6 消除误报 fail)")
    args = parser.parse_args()

    md_path = Path(args.md_path)
    if not md_path.exists():
        print(f"[错误] 找不到: {md_path}", file=sys.stderr)
        sys.exit(1)
    brief_path = Path(args.brief)
    if not brief_path.exists():
        print(f"[错误] 找不到 tender_brief.json: {brief_path}", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")
    md_name = md_path.name
    stats = count_markdown(text)
    brief_data = json.loads(brief_path.read_text(encoding="utf-8"))
    brief_parts = brief_data.get("response_file_parts", [])

    # 加载 matrix
    matrix_rows: list[dict] = []
    matrix_path = Path(args.matrix)
    if matrix_path.exists():
        with open(matrix_path, "r", encoding="utf-8-sig", newline="") as f:
            matrix_rows = list(csv.DictReader(f))

    print(f"章节自检报告: {md_name}")
    print()

    checks = []

    # [1] Part 边界声明
    s1, d1 = check_part_declaration(text, md_path, brief_parts)
    checks.append(("Part 边界声明", s1, d1))

    # [2] 标题关键词覆盖
    s2, d2 = check_title_keywords(text, md_name, matrix_rows)
    checks.append(("标题关键词覆盖", s2, d2))

    # [3] 字数自检
    s3, d3 = check_word_count(text, md_name, matrix_rows,
                              args.tech_score, args.pages)
    checks.append(("字数自检", s3, d3))

    # [4] 图占位符规范
    s4, d4 = check_figures(text, stats["table_ratio"])
    checks.append(("图占位符规范", s4, d4))

    # [5] 履约句式检查
    s5, d5 = check_disclaimer(text)
    checks.append(("履约句式检查", s5, d5))

    # [6] 必备要素覆盖
    s6, d6 = check_mandatory_elements(text, md_name, matrix_rows,
                                       strict=args.strict_elements)
    checks.append(("必备要素覆盖", s6, d6))

    # [7] AI 输出空格规范(v2 单元 2)
    s7, d7 = check_whitespace_rule(text)
    checks.append(("AI 输出空格规范", s7, d7))

    # [8] 正文级缝合句检测(V3-4)
    s8, d8 = check_content_keyword_stitching(
        text, matrix_rows,
        window=args.stitching_window,
        threshold_warn=args.stitching_threshold_warn,
        threshold_fail=args.stitching_threshold_fail,
    )
    checks.append(("正文级缝合句", s8, d8))

    # 输出(legacy-mode:v2 新增的严格检查降级为 warn)
    # v2 严格检查索引:1=Part 边界(pre-B,不降)
    # 2=标题关键词(缝合句作弊:v2 新,可降) 3=字数(v2 升级 fail:可降)
    # 4=图占位符 5=履约句式 6=必备要素 7=空格规范(v2 新,可降)
    # 8=正文缝合(V3-4 新,可降)
    roundb_strict_indices = {2, 3, 7, 8}
    fail_count = 0
    warn_count = 0
    pass_count = 0
    for i, (name, status, detail) in enumerate(checks, 1):
        # legacy 模式下,把 v2 新增/升级的 fail 降级为 warn
        effective_status = status
        if args.legacy_mode and status == "fail" and i in roundb_strict_indices:
            effective_status = "warn"
            detail = (detail or "") + "\n        [legacy-mode] 已从 fail 降级为 warn"
        icon = {"pass": "通过", "warn": "警告", "fail": "失败"}[effective_status]
        print(f"[{i}] {name:14s}  {icon}")
        if detail:
            for line in detail.split("\n"):
                print(f"        {line}")
        if effective_status == "fail":
            fail_count += 1
        elif effective_status == "warn":
            warn_count += 1
        else:
            pass_count += 1

    print()
    legacy_note = " (legacy-mode)" if args.legacy_mode else ""
    print(f"总结{legacy_note}: {fail_count} 失败 / {warn_count} 警告 / {pass_count} 通过")

    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
