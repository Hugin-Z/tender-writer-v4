# scripts/tests/fixtures · 测试数据来源声明

本目录所有 fixture(招标文本片段、brief json、scoring matrix csv、docx 等)的来源声明。

## R10 来源声明

**所有 fixture 数据均为人工合成或工具链 demo 项目脱敏改写,不来自模型训练数据。**

具体规则:

- fixture 内涉及的"项目名 / 采购单位 / 公司名"统一使用占位字符(如 `示例采购单位 A` / `示范项目 X` / `投标方 ALPHA`),**禁用真实公司名 / 政府机关名 / 真实项目编号**
- fixture 内涉及的金额、人数、日期等数字用易识别的虚构值(如预算 50万元、工期 60 天、团队 15 人)
- 所有 PASS / FAIL 断言基于 fixture 内**字面字符串**,不依赖外部网络、数据库、模型记忆
- 任何 fixture 修改后,关联的 test case 期望值同步更新

## 子目录与来源类型

| 子目录 | fixture 类型 | 来源 |
|---|---|---|
| `parse_tender/` | `.txt` 招标文本片段 | 人工合成最小语料 |
| `check_cross_consistency/` | (无文件 fixture) | 全部 inline 字符串在测试文件里 |
| `v45_merge/` | `.json` brief 形态 | 人工合成最小 brief 结构 |
| `generate_outline/` | `.json` brief + `.csv` matrix | 人工合成,5 类 project_type 各一份 |
| `export_deliverables/` | `.json` brief 形态 | 人工合成 |
| `compliance_check/` | `.docx` + `.csv` | 由 `_generators/make_test_docx.py` 程序化生成 |

## compliance_check docx 生成器

`compliance_check/_generators/make_test_docx.py` 是 fixture 生成器:

- 用 python-docx 程序化构造 `clean_response.docx` / `missing_keywords.docx` / `font_unsafe.docx`
- 生成产物 git track(避免每次跑测都重跑)
- 只在 fixture 设计需要更新时手工重跑,产物和生成器代码同 commit 入库

## 与 ai_output_rules R10 的关系

R10 要求 AI 不得引入训练数据中的事实。本目录 fixture 全部满足 R10:

- 字面字符串都在 git tracked 文件里,可被审核位查证
- 没有 fixture 引用未在文件中出现的"行业事实"(如真实 GB 标准号、政策文件年份等)
