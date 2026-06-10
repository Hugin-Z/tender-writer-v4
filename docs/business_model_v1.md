# tender-writer business model (v1)

> ⚠️ **本文档定位(R10 诚实声明)**:
>
> 本文档是 V4-0 期间为解决 16 处显式 + 2 处隐含 `business_model §X #NXX` 空指针引用而从 SKILL.md + 脚本注释反推沉淀的"引用锚点集",**不是完整业务模型权威文档**。它只对被引用的 §X #NXX 字面负责,**不保证业务模型整体完整性**。`#N17` / `#N18` / `#N23` 等跳号在仓内无引用,留白不补造。文档化过程中若发现某 §X #NXX 字面跟代码行为不符,已在对应章节标注 `[字面-行为 gap]`,未自行裁定改字面还是改代码。

---

## §1 文档定位

本文档跟其他文档的边界:

- **SKILL.md** — 描述五阶段流程(怎么做)
- **docs/DESIGN.md** — 描述设计哲学(为什么这么设计)
- **docs/manifest_schema.md** — 描述 B 模式 manifest.yaml 字段(数据约定)
- **本文档(business_model_v1.md)** — 沉淀历史决策快照(§8)+ skill 模型声明(§9)

引用规约:

- 代码注释 / SKILL.md / print 文案中出现的 `business_model §X #NXX` 字面 → 指向本文档对应章节
- 单独出现的 `#NXX`(不带前缀)→ 同义,也指向本文档 §8 对应编号

---

## §8 历史决策快照(以 #NXX 编号沉淀)

> 说明:#NXX 编号是历史迭代中"重要决策"的连续编号,不连续是因为某些决策没在代码注释中沉淀引用。本节只收录代码 + SKILL.md 中实际引用过的编号。

### §8.3 #N16 · `__REGEX_DRAFT__` 机制删除

**字面源**:`scripts/brief_schema.py` L20-27 注释 + `scripts/parse_tender.py` L498-500 注释

**决策**:

原有的招标解析三层验证机制(脚本 regex 初提 → AI 校对带 `__REGEX_DRAFT__` 前缀的 draft 值 → 用户把关)在 v1 时代简化为**两层验证**:

1. AI 直接读原文(`raw_lines_for_ai` / `raw_text`)填充 `extracted` 字段
2. 用户 review 并创建 `tender_brief.reviewed` 标记

**已删除的工件**:

- `brief_schema.py` 中 `REGEX_DRAFT_PREFIX` 常量
- `brief_schema.py` 中 `has_unreviewed_drafts` 函数
- `parse_tender.py` 中 regex 初提路径

**保留的工件**:

- `extracted` 字段骨架(11 个字段,见 `parse_tender.py` L500-510)由脚本生成空值
- AI 在 SKILL.md 阶段 1 Step 2A 直接填充

**判据**:为什么删?三层验证机制中 "脚本初提的 draft 值需要 AI 清理前缀" 是冗余环节 — AI 直接读原文准确率不低于读 draft 后清理,且少一层失真。

---

### §8 #N19 · Part 完整重做触发条件

**字面源**:`SKILL.md` L763 + L770-771(阶段 4-C "执行者边界" 段)

**决策**:

`response_file_parts[i]` 中的字段按 **元信息层** vs **语义层** 分类:

- **元信息层**(允许就地修改,不触发完整重做):
  - `variables.yaml` 的 `source` / `path` / `description` / `required` 字段(V49bis)
  - 此类修改由用户显式决定后落地

- **语义层**(变更触发该 Part 完整重做):
  - `sub_mode` 字段变更
  - `production_mode` 字段变更
  - `source_anchor` 字段变更
  - 等其他影响 Part 产物形态的字段

**特例**:首次 `sub_mode` 写入(从 None / 缺失 → 'C-template' / 'C-reference' / 'C-attachment')属 V49bis 元信息层"从无到有",**不触发 #N19 的完整重做**。仅"已有值 → 改值" 才触发。

**执行者边界**:

- 执行者(Claude Code / 其他 AI 编辑器)**不得自行修改** 已产出的 `template.docx` / `filled.docx` / `instructions.md` / `intermediate.json` — 发现问题停下反馈给用户
- 用户显式决定后修改 `variables.yaml` 元信息层是合法操作

---

### §8 #N20 · sub_mode 判据 + C-attachment 挂档

**字面源**:`SKILL.md` L731-738(阶段 4-C "分流依据")+ L760-765("sub_mode 判定")+ `scripts/brief_schema.py` L96-103

**决策**:

`production_mode == 'C'` 的 Part 按 `sub_mode` 三分:

| sub_mode | 产物形态 | filled 产物去向 |
|---|---|---|
| **C-template** | `template.docx` + `variables.yaml` + `intermediate.json` + `filled.docx` 三件套 | filled.docx 作为 docx 片段供整标合并器并入主响应文件 |
| **C-reference** | `instructions.md`(YAML front matter + markdown 正文)单文件 | 由外部系统(电子采购平台)生成 filled 产物,工具链不产 docx 模板;见 §8 #N22 |
| **C-attachment** | **当前挂档** | 遇到真实用例时启封设计,目前 `c_mode_extract` / `c_mode_fill` / `migrate_brief_schema` 均 raise NotImplementedError |

**判据**(投标方视角):**filled 产物的最终去向**:

- 产物直接进入主响应文件(`final_response.docx` 的某一节)→ C-template
- 产物在外部系统(电子采购平台)生成,主响应文件不含此节 → C-reference
- 产物是独立附件,既不并入主文件也不在外部系统生成 → C-attachment

**非判据**(仅作 AI 判定时的上下文辅助,不作判定依据):

- 项目级是否要求 CA 证书
- 是否走电子采购平台
- 其他项目级特征

**AI 判定流程**:

- 新项目:`parse_tender.py` 阶段 1 由 AI 按本判据为每个 `production_mode='C'` 的 Part 判定 sub_mode,写入 `response_file_parts[i].sub_mode`
- 已有项目:走 `migrate_brief_schema.migrate_v10_to_v11` 迁移(首次 sub_mode 写入属 V49bis 元信息层"从无到有",不触发 #N19 的完整重做)

**C-attachment 挂档原因**:V60 落地时尚无真实 C-attachment 用例,工具链 schema 收 `'C-attachment'` 值但 extract/fill/merge/export 全部以 NotImplementedError / print "挂档跳过" 兜底。遇到真实用例时启封该挂档,实现 attachment 业务行为(留 V4-4)。

---

### §8 #N21 · B 模式 `assembly_order` 组织判据

**字面源**:`SKILL.md` L786-796(阶段 4-B "分流依据")+ `scripts/brief_schema.py` L145-150 注释

**决策**:

B 模式 Part 的 `manifest.yaml` 中 `assembly_order[i].source_type` 三类参考值(AI 在阶段 4-B Step 3 判定):

| source_type | 适用场景 | 当前行为 |
|---|---|---|
| **inline_template** | 招标文件给模板 + 变量占位(如基本情况表、信誉声明) | 当前产占位段落;未来由 `b_mode_fill` 自动调 `c_mode_fill` 完成填充(留 V4) |
| **asset_lookup** | 从 assets 库查供应商素材(如资质证明、业绩合同) | 走 `AssetsProvider.lookup + resolve`;V3-1 起 `CuratedLocalAssetsProvider` 默认扫 `assets/<类别>/<company_id>/_raw/` 真实命中,缺省走 `PlaceholderAssetsProvider` 占位 |
| **self_drafted** | 供应商自撰(如开放资料) | 产占位段落 `[本节需供应商自撰: <title>]` |

**扩展规则**:

- AI 遇到新形态可自造 source_type 值
- `b_mode_fill` 遇未知值 raise ValueError,由用户 review 决定是否扩展工具链

**B 模式 prompt 沉淀位置**:`B_MODE_EXTRACT_PROMPT` 常量在 v1(P2 清理)中从 `brief_schema.py` 删除,迁移到本节(§8 #N21)字面。主 agent 在阶段 4-B Step 3 直接读本节判据组织 `assembly_order`,不从脚本常量取 prompt。

---

### §8 #N22 · C-reference 不进 `final_response.docx`

**字面源**:`scripts/v45_merge.py` L1-15 模块 docstring + L271-281 主循环 c_reference 分支 + `SKILL.md` L735-736

**决策**:

C-reference Part 的产物 `instructions.md` **不并入主响应文件** `final_response.docx`,而是由整标合并器(`v45_merge.py`)读取后渲染为 `operations_checklist.md` 的一节,作为投标方对外部系统的操作指引。

**实现**:

- `v45_merge.py:build_merge_order` 把 sub_mode='C-reference' 的 Part 归类为 `'c_reference'` kind
- 主循环对 `'c_reference'` kind 不调 `composer.append`,改调 `_render_c_reference_section` 把 instructions 转 markdown 段落
- markdown 段落追加到 `operations_lines`,最终写入 `operations_checklist.md`

**判据**:为什么不进?C-reference 的最终交付物在外部系统(电子采购平台)生成,主响应文件包含该节会重复 / 矛盾 / 误导投标专家。`operations_checklist.md` 作为操作指引,告知投标方"这一项去 X 平台填",边界清晰。

---

### §8 #N24 · 交付层独立于工具链内部

**字面源**:`scripts/export_deliverables.py` L1-13 模块 docstring + `SKILL.md` 阶段 6 段(L885-910)

**决策**:

工具链有**两套产物路径**,严格分离:

- **工具链内部**(英文命名 + 原 schema 格式):
  - `projects/<项目>/output/{c_mode,b_mode}/<part_dir>/...`
  - `projects/<项目>/final_tender_package/{final_response.docx, operations_checklist.md, pending_manual_work.md}`
  - 路径名 / 文件名按 schema 字段定,**给工具链消费**

- **交付层**(中文命名 + Office 原生格式):
  - `projects/<项目>/投标交付物/`
  - 路径名 / 文件名按业务语义定,**给评标专家看**

**核心原则**:

- 交付层独立于工具链内部 — `export_deliverables.py` 单向从内部映射到交付层,**不反向回写**
- 每次执行覆盖上次产出(幂等)
- 交付层**不进 tracked_outputs**,不参与 baseline 追踪
- 用户**手工修改交付层不污染工具链** — 改完工具链照常重跑会再次覆盖

**判据**:为什么分两层?工具链内部用 schema 字段命名(如 `c_mode/不参与围标串标承诺书/filled.docx`),给下游脚本消费;评标专家看的文件需要业务命名(如 `投标交付物/C 模式产出/不参与围标串标承诺书.docx`)。两层不混 → 工具链可重构 schema 不影响交付层稳定 / 用户改交付层不影响工具链回溯。

---

## §9 skill 模型声明

**字面源**:散落在 `scripts/brief_schema.py` L24-27 / L102-103 / L149-151 注释 + `scripts/parse_tender.py` L300-301 / L498-500 注释 + `scripts/export_deliverables.py` L188-193 docstring + `scripts/migrate_brief_schema.py` L148-153 docstring

**核心声明**:

**(1) 脚本做纯数据处理,语义判断交 AI**

- 脚本职责:格式转换 / 字段校验 / 文件读写
- 不做:任何语义推断(`production_mode` / `sub_mode` / `part_attribution` / `source_type` 的判定全部交 AI)
- 缺失字段时脚本硬失败(退出码 1),不静默兜底

**(2) 业务模型 prompt 不沉淀为脚本常量**

历史上 `brief_schema.py` 中曾有:

- `SUB_MODE_JUDGE_PROMPT` 常量(sub_mode 判定 prompt)
- `B_MODE_EXTRACT_PROMPT` 常量(B 模式 assembly_order 组织 prompt)
- `REGEX_DRAFT_PREFIX` 常量(三层验证机制遗存)

v1(P2 清理)中**全部删除**,prompt 字面迁移到本文档对应章节(§8 #N20 / §8 #N21 / §8.3 #N16):

- **主 agent 直接读本文档判据组织 prompt**
- **不再从脚本常量取 prompt**

**(3) 用 SKILL.md 描述流程,用 business_model 描述判据**

- `SKILL.md` 各阶段:**步骤** + **触发** + **产物** + **完成标志**
- 本文档 §8:**判据** + **决策原因** + **判据的非判据(易混项)**

两层职责互补,不互相替代。

**(4) 主 agent 做语义结构化,脚本做机械写入**

典型例子(`export_deliverables.py` L188-195):`md_to_xlsx` 转换不由脚本解析 markdown(语义切分属红线),改由主 agent 读 md 内容 → 按 schema 组织 rows(list of dict)→ 调 `_write_xlsx_from_rows(dst, headers, rows)` 完成确定性写入。

---

## §A 字面回溯映射表(R10 留底)

本附录用于 R10 扫描脚本对账 —— 列出本文档每节 vs 仓内引用位置的精确映射。

| 本文档节 | 仓内引用位置 |
|---|---|
| §8.3 #N16 | `brief_schema.py:27` / `parse_tender.py:301` / `parse_tender.py:500` |
| §8 #N19 | `SKILL.md:763` / `SKILL.md:771` |
| §8 #N20 | `brief_schema.py:102` / `brief_schema.py:121` / `c_mode_extract.py:346` / `c_mode_fill.py:325` / `migrate_brief_schema.py:152` / `migrate_brief_schema.py:174` / `migrate_brief_schema.py:185` / `parse_tender.py:849` / `v45_merge.py:84`(隐含) |
| §8 #N21 | `brief_schema.py:149` |
| §8 #N22 | `v45_merge.py:276`(隐含,不带 `business_model` 前缀) |
| §8 #N24 | `export_deliverables.py:10` |
| §9 | `brief_schema.py:27` / `brief_schema.py:103` / `brief_schema.py:150` / `parse_tender.py:301` / `parse_tender.py:500` / `parse_tender.py:847` / `export_deliverables.py:193` / `migrate_brief_schema.py:152` |

跳号说明:`#N17` / `#N18` / `#N23` 等编号在仓内无引用,留白不补造(见本文档头 R10 诚实声明)。

---

## 变更记录

- 2026-05-28 v1 首发(V4-0.1):为解决 16 处显式 + 2 处隐含 `business_model §X #NXX` 空指针引用而沉淀。本文档对引用字面负责,不对业务模型整体完整性负责。
