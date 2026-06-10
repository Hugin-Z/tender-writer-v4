# tender-writer-v3

![License](https://img.shields.io/badge/License-MIT-blue.svg) ![Python](https://img.shields.io/badge/Python-3.11%2B-blue) ![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey) ![AI](https://img.shields.io/badge/AI-Claude%20Code%20%7C%20Cline-orange)

## 项目状态

**稳定可用(主开发环境)** — v3.0.0 已封板,完成 14 项改进(V3-1 至 V3-14)。Linux / macOS 未验证。

- **测试覆盖**: 12 个测试文件 / `./run_script.bat tests/run_all.py` 全 PASS
- **demo 项目**: `projects/demo_cadre_training/` 端到端可重跑(parse_tender → ... → export_deliverables 11 步)
- **主开发环境**: Windows 10+ + Python 3.11,Linux/macOS 未验证
- **维护状态**: 个人维护项目, issue / PR 响应可能不及时

> 把政府类项目技术标的首轮结构化拆解与初稿组装压缩到分钟级;正式投标仍需人工扩写、校核和审稿。

💡 完整端到端流程见 [projects/demo_cadre_training/](projects/demo_cadre_training/),clone 下来跑一遍即知工具链能力边界。

---

## 快速开始

```bash
# 1. clone
git clone https://github.com/Hugin-Z/tender-writer-v3.git
cd tender-writer-v3

# 2. 装依赖(Windows 双击即可)
install.bat

# 3. 打开 VSCode + Claude Code,告诉它:
#    "请读 SKILL.md,开始处理 projects/demo_cadre_training 的标书编制"
```

示范项目位于 [projects/demo_cadre_training/](projects/demo_cadre_training/),Clone 下来即可跑通端到端。

---

## 系统依赖

- **Python**: 3.11+(实测版本;3.10 未做兼容性验证)
- **OS**: Windows 10+(主开发环境);Linux / macOS 未在 CI 验证,社区贡献欢迎
- **git**: 必装(`scripts/demo_reset.py` 等运维工具依赖 git CLI)
- **Python 包**: 8 个核心包(pdfplumber / python-docx / docxtpl / PyYAML / docxcompose / opencc / lxml / pypinyin),完整清单 [requirements.txt](requirements.txt)
- **可选**: OCR 工具(扫描版 PDF 处理时按需,详见 [docs/FAQ.md Q4](docs/FAQ.md))

依赖通过 `install.bat` 自动装到隔离虚拟环境(`.venv/`),不污染系统 Python。

---

## 核心能力

- **五阶段主干工作流**:招标文件解析 → 评分矩阵 → 提纲 → 分章节撰写 → 合规终审,每阶段可 review;另含并列阶段 4-B(B 模式材料组装) / 4-C(C 模式模板填充) / 6(交付层导出)
- **评分矩阵追踪**:10 列 CSV 把每一分拆到应答章节,杜绝漏答
- **项目类型识别**:工程 / 平台 / 研究 / 规划 / 其他 5 类自动选 outline 模板
- **docx 渲染质量**:统一中文宋体、黑色标题、图占位区块、字号相对规则、空格自动清理
- **B 模式材料组装(当前为文本提取)**:从 assets 库按 asset_type / 公司 id 查找真实材料(CuratedLocalAssetsProvider),提取段落文本合并到 assembled.docx;表格 / 图片 / 公章 / 扫描件保真留 V4。无命中时产占位 + `.pending_marker`,V45 合并器列入 `pending_manual_work.md`
- **C 模式非交互填充**:一键跑完所有 C 模式 Part,变量缺失时 filled.docx 写入"【待填:变量描述】"显式占位
- **跨章节一致性检查**:团队成本 vs 预算、承诺时间 vs 工期等自相矛盾类错误自动捕获
- **Claude Code 深度协作契约**:CLAUDE.md 定义 6 条硬红线,AI 行为可预期

---

## 版本演进

**v3.0.0(当前)** — 在 v2.0.x 基础上完成 14 项改进(V3-1 至 V3-14):

- **测试覆盖**:从 1 个测试文件扩到 12 个文件,涵盖 parse_tender / build_scoring_matrix / generate_outline / b_mode / c_mode / compliance_check / check_chapter / check_cross_consistency 等核心模块
- **B 模式真实组装**:CuratedLocalAssetsProvider 默认走 `assets/<类别>/<company_id>/_raw/` 真实命中,不再纯占位
- **合规检查扩展**:V3-2 字体安全(段落级 + fontTable.xml 级)/ V3-4 正文级缝合句作弊检测 / V3-5 --section-only 跳封面目录 / V3-9 跨章节字段一致性 / 简历 vs 架构图人名一致性 / 章节交叉引用编号有效性
- **扫描版 PDF 处理(V3-6)**:`parse_tender.py` 自动检测扫描版 PDF(全文平均 < 50 字/页),提供 `--ocr-text` fallback 通道(用户外部 OCR 后塞回 txt 走后续解析)
- **工具链可重跑(V3-13)**:`scripts/demo_reset.py` 提供 demo 项目无破坏重跑的标准化路径
- **timing 埋点(V3-3)**:`_timing_hook.py` 给 7 个核心脚本加阶段耗时埋点 + `_timing_report.md` 产出
- **Word 直切集成(V3-7)**:c_mode_run 自动分流模板填充 vs 整段直切场景
- **文档口径统一(V3-10/V3-11/V3-12)**:五阶段主干 + 并列阶段措辞统一 / B 模式 README 诚实化 / SKILL.md description 关键词从 25 精简到 10

详见 [docs/v3_planning.md](docs/v3_planning.md) 和 [docs/changelog.md](docs/changelog.md)。

**v2.0.x** — 基于 v1.1 两轮迭代沉淀,核心变化:AI 输出规则常驻化(R1-R10)、docx 渲染质量总攻、非交互化、项目类型识别。详见 [docs/v2_design_notes.md](docs/v2_design_notes.md)。

---

## 与 AI 工具的兼容性

- **Claude Code(推荐)**:项目级协作深度最优,读取 `SKILL.md` + `CLAUDE.md` 走完整五阶段主干 + 并列阶段;进阶用户建议读 [CLAUDE.md](CLAUDE.md) 了解工具链协作契约
- **Cline / Cursor / 通义灵码 / 等其他 AI IDE 插件**:能读 `SKILL.md` 即可工作,部分硬红线靠 `references/ai_output_rules.md` 兜底
- **纯对话 AI(ChatGPT / DeepSeek Web 等)**:把 SKILL.md 和当前阶段文件发给 AI,按阶段手工推进

---

## 典型应用场景

- 政府采购公开招标 / 竞争性磋商 / 竞争性谈判 技术标(25-500 万元规模)
- 事业单位 / 国有企业公开采购 技术响应文件
- 外部专业咨询 / 培训服务 / 工程咨询 等服务类项目投标

---

## 深度文档

| 文档 | 面向 |
|---|---|
| [SKILL.md](SKILL.md) | 五阶段主干 + 并列阶段工作流细节,AI 入口,必读 |
| [CLAUDE.md](CLAUDE.md) | Claude Code 协作契约,6 条硬红线 |
| [docs/DESIGN.md](docs/DESIGN.md) | 设计哲学 / 为什么这么设计 |
| [docs/v3_planning.md](docs/v3_planning.md) | V3 改进路线图 + 完成判定(14 项) |
| [docs/manifest_schema.md](docs/manifest_schema.md) | manifest.yaml 字段定义(B 模式 assembly_order schema) |
| [docs/v2_design_notes.md](docs/v2_design_notes.md) | v2 设计决策记录 |
| [docs/v2_roadmap.md](docs/v2_roadmap.md) | v2 路线图(已完成,留作历史)|
| [docs/changelog.md](docs/changelog.md) | 版本变更日志 |
| [docs/FAQ.md](docs/FAQ.md) | 常见问题 |

---

## 许可证

[MIT](LICENSE) © 2026 Hugin-Z · 问题反馈:提 Issue
