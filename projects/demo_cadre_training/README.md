# Demo 项目:A 市直属单位 2026 年度干部综合能力提升培训服务采购

这是 tender-writer-v3 的**端到端演示项目**,供首次使用者理解工具链全流程。

## 项目虚构信息

| 字段 | 值 |
|---|---|
| 项目名称 | A 市直属单位 2026 年度干部综合能力提升培训服务采购项目 |
| 项目编号 | DEMO-2026-001 |
| 预算 | 500000 元 |
| 工期 | 60 日历日 |
| 采购方式 | 竞争性磋商 |
| 采购方(虚构) | A 市机关事务服务中心 |
| 采购代理(虚构) | 示范咨询有限责任公司 |
| 投标主体(虚构) | 示例科技有限公司(`own_demo`) |
| 项目类型 | `other`(培训类,按工具链五类分类归入 other;参见 `references/outline_templates/README.md`) |

所有人名、公司名、地名均为虚构,与任何真实项目无关。

## ⚠️ 章节篇幅说明

**本 demo 的技术部分 5 个章节均为 500 字级 stub**(stub = 骨架/占位),用于演示工具链端到端能力**不代表真实标书篇幅**。实际投标中:

- 按 SKILL.md 的"投标金额(万元)× 1 页 A4"篇幅基准,50 万项目技术部分应 ≈ 50 页
- 本 demo 5 章合计约 2500 字 ≈ 5 页,仅占 10%
- 目的:跑通工具链 → `compliance_check` 通过 → `check_cross_consistency` 通过 → 整标合并 → 导出交付层。**证明工具链可用,而非证明文字质量**

真实投标前,请按 [scoring_matrix.csv](output/scoring_matrix.csv) 的"撰写指引"(第 9 列)与"必备要素"(第 10 列)**扩写**每个章节至目标字数。工具链 `check_chapter.py` 会用字数阻塞保护你(不达标直接 fail)。

## 产出清单

| 产物 | 路径 | 说明 |
|---|---|---|
| 招标文件原稿 | [input/tender_demo.docx](input/tender_demo.docx) | 虚构招标文件(2 页,纯文本) |
| 招标文件解读 | [output/tender_brief.md](output/tender_brief.md) / [output/tender_brief.json](output/tender_brief.json) | 阶段 1 产出 |
| 评分矩阵 | [output/scoring_matrix.csv](output/scoring_matrix.csv) | 6 行(报价 20 分 + 课程设计 25 + 师资配置 20 + 实施方案 15 + 保障措施 12 + 服务承诺 8 = 100 分)|
| 提纲 | [output/outline.md](output/outline.md) | 按 `other` 类型生成 |
| 技术部分 docx | [output/tender_response.docx](output/tender_response.docx) | 5 章追加合并 |
| 章节 markdown | [output/chapters/part_09/](output/chapters/part_09/) | 5 个 stub 章节源文件 |
| 合规终审报告 | [output/compliance_report.md](output/compliance_report.md) | 漏答 0 / 弱覆盖 0 / 模板残留 0 |
| 交叉一致性报告 | (stdout)| 0 失败 / 0 警告 |
| C 模式 filled.docx | [output/c_mode/](output/c_mode/) | 6 个 Part(封面/资格声明/法代证明/围标承诺/开标一览表/磋商申请)|
| B 模式 assembled.docx | [output/b_mode/](output/b_mode/) | 2 个 Part(其他资格证明文件 [含中小企业声明函 inline_template] / 商务部分)|
| 整标合并 | [final_tender_package/final_response.docx](final_tender_package/final_response.docx) | 合并 9 片段 |
| 中文交付层 | [投标交付物/](投标交付物/) | 最终对外交付,含 README、最终投标文件、评分矩阵.xlsx、C 模式产出/、B 模式产出/ |

## Part 分布(9 个)

| # | Part | 生产模式 |
|---|---|---|
| part_01 | 投标文件封面 | C-template |
| part_02 | 供应商资格声明 | C-template |
| part_03 | 法定代表人身份证明或授权书 | C-template |
| part_04 | 其他资格证明文件(含营业执照/财务报告/税务社保/中小企业声明函 4 项 assembly_order)| B |
| part_05 | 不参与围标串标承诺书 | C-template |
| part_06 | 开标一览表 | C-template |
| part_07 | 磋商申请 | C-template |
| part_08 | 商务部分(业绩+团队简历) | B |
| part_09 | 技术部分(AI 撰写主体,承载技术商务 80 分中的主要部分) | A |

**总计**:A=1 / B=2 / C=6,覆盖政府采购竞争性磋商项目的典型 Part 结构。

## 如何基于本 demo 自跑(照着重跑一次)

`output/tender_brief.reviewed` 闸门标记**不入 git**(见根 `.gitignore` 的 `*.reviewed`),首次跑前请手动创建:

```bash
touch projects/demo_cadre_training/output/tender_brief.reviewed
```

然后即可顺序跑下游 `build_scoring_matrix.py` / `generate_outline.py` / `c_mode_run.py --all` 等脚本。

## 改造为你自己的项目

```bash
# 1. 克隆仓库并安装依赖
git clone <repo-url>
cd tender-writer-v3
./install.bat

# 2. 以 demo 为起点,改造为你自己的项目
cp -r projects/demo_cadre_training projects/your_project
# 替换 input/ 下的招标文件为你的真实招标文件 PDF/docx
# 删除 output/ 下所有产物(保留 _inbox/_raw 的 .gitkeep)
rm -rf projects/your_project/output/*
rm -rf projects/your_project/final_tender_package
rm -rf projects/your_project/投标交付物

# 3. 按 SKILL.md 五阶段主干 + 并列阶段流程,在 Claude Code 里:
# "请读取 SKILL.md,处理 projects/your_project/ 的标书编制"
```

## 问题反馈

本 demo 用于演示工具链能力。若发现工具链 bug,欢迎在主仓库提 issue。
