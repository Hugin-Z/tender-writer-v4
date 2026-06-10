# -*- coding: utf-8 -*-
"""
make_test_pdf.py · 生成 parse_tender V3-6 测试用 PDF fixture

产出落到上一级目录:
- scanned_synthetic.pdf    : PIL 渲染中文文字到图片再合成的扫描版模拟 PDF
                              (pdfplumber.extract_text 输出 0 字符)

text_pdf_naturalsci.pdf 是手工拷贝的真实公开招标 PDF（来源见 README.md），
不在本脚本生成范围。如缺失请手工:
    cp "projects/test/input/国家自然科学基金委员会档案与服务外包项目（含人员驻场培训）.pdf" \\
       scripts/tests/fixtures/parse_tender/text_pdf_naturalsci.pdf

运行:
    ./run_script.bat tests/fixtures/parse_tender/_generators/make_test_pdf.py

产物 git track,无需每次跑测重新生成。仅 fixture 设计需更新时手工重跑。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent.parent


def _load_chinese_font(size: int = 22) -> ImageFont.ImageFont:
    """加载系统中文字体,失败兜底默认。"""
    for fp in [
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
    ]:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _make_scanned_page(text_lines: list[str], w: int = 850, h: int = 1100) -> Image.Image:
    """渲染一页"扫描版"图片(白底 + 黑字)。"""
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    font = _load_chinese_font(22)
    y = 80
    for line in text_lines:
        draw.text((80, y), line, fill="black", font=font)
        y += 30
    return img


def make_scanned_synthetic(out_path: Path) -> None:
    """合成扫描版 PDF: PIL 渲染中文文字到图片,多页合 PDF。

    pdfplumber.extract_text 在这种 PDF 上输出 0 字符(图片 PDF 无文字流),
    用于触发 V3-6 扫描版检测。
    """
    pages_text = [
        ["项目采购文件", "国家自然科学基金委员会档案外包",
         "采购编号:TC250E06T", "2025 年 6 月"],
        ["第一章 项目背景", "本项目旨在加强档案管理水平。"]
        + [f"第 {i} 段补充说明。" for i in range(15)],
        ["第二章 评分办法", "资质 30 分;业绩 30 分;方案 40 分"]
        + [f"附加说明 {i}。" for i in range(15)],
        ["第三章 资格要求", "★必备资质:CMMI 三级以上"]
        + [f"要求 {i}。" for i in range(15)],
    ]
    images = [_make_scanned_page(lines) for lines in pages_text]
    images[0].save(str(out_path), "PDF", save_all=True, append_images=images[1:])


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = {
        "scanned_synthetic.pdf": make_scanned_synthetic,
    }
    for name, maker in targets.items():
        path = OUT_DIR / name
        maker(path)
        print(f"[OK] {path} ({path.stat().st_size:,} bytes)")

    # 提示 text_pdf_naturalsci.pdf 是手工拷贝的
    text_pdf = OUT_DIR / "text_pdf_naturalsci.pdf"
    if not text_pdf.exists():
        print()
        print(f"[警告] {text_pdf} 缺失。请手工拷贝:")
        print(
            f'  cp "projects/test/input/国家自然科学基金委员会档案与服务外包项目'
            f'(含人员驻场培训).pdf" "{text_pdf}"'
        )
        print(f"  详见 {OUT_DIR}/README.md")
    else:
        print(f"[OK] {text_pdf} ({text_pdf.stat().st_size:,} bytes,手工拷贝)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
