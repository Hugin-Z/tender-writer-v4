# -*- coding: utf-8 -*-
"""
count_words.py · markdown 章节字数统计工具

用法:
    run_script.bat count_words.py <markdown文件路径>

统计口径:
    中文字符([\u4e00-\u9fff]) + 英文单词([a-zA-Z]+)
    排除: HTML注释 / 标题行(# 开头) / 表格分隔行(|---|) /
          图占位符行(**【图 开头) / 分隔线(---) / 空行
    表格内容行(| xxx | yyy |)纳入统计
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# HTML 注释(可能跨行)
COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
# 中文字符
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
# 英文单词
ENGLISH_RE = re.compile(r"[a-zA-Z]+")
# 表格分隔行
TABLE_SEP_RE = re.compile(r"^\s*\|[\s\-:|]+\|\s*$")
# 图占位符行
FIGURE_RE = re.compile(r"^\s*\*\*【图")
# 分隔线
HRULE_RE = re.compile(r"^-{3,}\s*$")


def count_markdown(text: str) -> dict:
    """统计 markdown 文本的字数。"""
    # 去掉 HTML 注释
    clean = COMMENT_RE.sub("", text)
    lines = clean.split("\n")

    content_lines: list[str] = []
    table_lines = 0
    figure_count = 0
    excluded = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            excluded += 1
            continue
        if TABLE_SEP_RE.match(stripped):
            excluded += 1
            continue
        if FIGURE_RE.match(stripped):
            figure_count += 1
            excluded += 1
            continue
        if HRULE_RE.match(stripped):
            excluded += 1
            continue
        # 表格内容行(含 |)纳入统计
        if "|" in stripped and stripped.startswith("|"):
            table_lines += 1
        content_lines.append(stripped)

    joined = "\n".join(content_lines)
    chinese_chars = len(CHINESE_RE.findall(joined))
    english_words = len(ENGLISH_RE.findall(joined))

    total_content_lines = len(content_lines)
    table_ratio = table_lines / total_content_lines * 100 if total_content_lines else 0

    return {
        "chinese_chars": chinese_chars,
        "english_words": english_words,
        "total": chinese_chars + english_words,
        "table_lines": table_lines,
        "total_content_lines": total_content_lines,
        "table_ratio": table_ratio,
        "figure_count": figure_count,
    }


def main() -> None:
    if len(sys.argv) < 2:
        print("用法: count_words.py <markdown文件路径>", file=sys.stderr)
        sys.exit(1)

    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"[错误] 找不到文件: {md_path}", file=sys.stderr)
        sys.exit(1)

    text = md_path.read_text(encoding="utf-8")
    stats = count_markdown(text)

    print(f"文件: {md_path.name}")
    print(f"中文字符: {stats['chinese_chars']}")
    print(f"英文单词: {stats['english_words']}")
    print(f"合计(中文字符+英文单词): {stats['total']}")
    print(f"表格行占比: {stats['table_ratio']:.0f}%")
    print(f"图占位符: {stats['figure_count']} 个")


if __name__ == "__main__":
    main()
