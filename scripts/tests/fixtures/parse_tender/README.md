# parse_tender fixture 来源说明

本目录的 fixture 文件覆盖 V3-2（基础测试）和 V3-6（扫描版 PDF 检测）需求。

## 文件清单

| 文件 | V3 版本 | 类型 | 来源 | 是否可重新生成 |
|---|---|---|---|---|
| `clean_minimal.txt` | V3-2 | 文本 | 手写 | 是（手工编辑）|
| `with_marks.txt` | V3-2 | 文本 | 手写 | 是（手工编辑）|
| `text_pdf_naturalsci.pdf` | V3-6 | PDF | 拷贝自 `projects/test/input/` | 见下方"text_pdf_naturalsci.pdf 来源" |
| `scanned_synthetic.pdf` | V3-6 | PDF | `_generators/make_test_pdf.py` | 是（重跑 generator）|
| `scanned_fallback.txt` | V3-6 | 文本 | 手写（模拟用户外部 OCR 结果）| 是（手工编辑）|

## text_pdf_naturalsci.pdf 来源

- 原始文件名：`国家自然科学基金委员会档案与服务外包项目（含人员驻场培训）.pdf`
- 来源：公开招标公告（采购编号 TC250E06T），用户已确认非敏感
- 原始位置：`projects/test/input/`（用户准备的测试样本目录，git tracked）
- 拷贝命令：
  ```bash
  cp "projects/test/input/国家自然科学基金委员会档案与服务外包项目（含人员驻场培训）.pdf" \
     scripts/tests/fixtures/parse_tender/text_pdf_naturalsci.pdf
  ```
- 重命名理由：fixture 引用使用短英文文件名，避免代码里的中文路径转义
- 实测字符密度：59 页 / 27,492 字符 / 平均 466 字/页（V3-6 文字版正例）

## scanned_synthetic.pdf 生成方式

用 `_generators/make_test_pdf.py` 内 PIL 渲染中文文字到白底图片（850×1100），多页合成 PDF。

- 实测字符密度：4 页 / 0 字符 / 平均 0 字/页（V3-6 扫描版反例）
- pdfplumber 在这种 PDF 上完全无法 extract_text（图片 PDF 无文字流）
- PIL 版本敏感：如果 PIL 大版本升级导致 PDF 输出格式有差异，需重跑 generator 验证

## scanned_fallback.txt 设计

模拟用户走"扫描版处理路径 2"（外部多模态 AI / 商业 OCR）后产出的纯文本，
作为 `--ocr-text` flag 测试的 fallback 输入。

内容是浓缩版的 text_pdf_naturalsci.pdf 文本，含:

- 项目封面字段（编号 / 采购人 / 时间）
- 三章核心内容（背景 / 评分 / 资格）
- ★ 实质性条款 + ▲ 加分项标记

下游 parse_tender 在 fallback 模式下应能从这份 txt 抽出 raw_lines / 章节锚点 /
extracted 字段，与文字版 PDF 路径殊途同归。

## V3-6 极简 PDF 边界（30 字/页封面）

V3-6 接受这个误报边界，**不为它做 fixture 验证**。具体说明见 `plans/v3-6.md` §6
风险表 + `docs/FAQ.md` Q4。

## 维护约定

- 上述文件 git tracked，不需每次跑测重新生成
- 仅 fixture 设计需要更新时手工重跑 generator / 重新拷贝 / 改写 txt
- `_generators/` 子目录是产能源（不参与测试运行），重跑后产物落到本目录
