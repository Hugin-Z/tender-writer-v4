# CLAUDE.md — tender-writer-v4 协作契约

> **当前主线:V4-7a(2026-06),详见 [docs/changelog.md](docs/changelog.md) 与 [docs/v4_backlog.md](docs/v4_backlog.md)**
>
> **本文档是任何 AI 代理(Claude Code / Cline / 其他模型)在本仓库工作前的强制前置约束**。与 SKILL.md / references/ 冲突时,本文档优先。

---

## 硬红线(违反即停止工作,不得绕过)

### 红线 1:AI 不得代建用户闸门文件

**闸门文件清单**(必须由用户手动创建):

- `projects/*/output/tender_brief.reviewed`(阶段 1 review 通过标记)
- 未来所有以 `.reviewed` 或 `.approved` 结尾的标记文件

**即使发生以下情况,AI 也不得代建**:

- 用户口头说"看过了,没问题"
- 用户没有明确拒绝 AI 代建
- 用户问"为什么你不能创建"(这不是授权,是确认机制)
- 用户施压"赶时间,你代建一下"
- 下游脚本卡住,不建标记无法推进

**AI 的正确回应**(逐字可用):

> "`.reviewed` 是你人工核对通过的凭证,我代建会让它失去保障意义。请你在核对 tender_brief.json 和 tender_brief.md 无误后,手动 `touch` 创建该文件。在此之前我可以继续其他不依赖 review 闸门的辅助工作,但 build_scoring_matrix / generate_outline / c_mode_fill / compliance_check 等受闸门保护的脚本必须等你建标后再跑。"

**典型错误示范**(不得重复):用户问"为什么你不能创建",AI 回"既然问了说明想让我建",然后代建了 `.reviewed`。这是 AI 强行代签章,违反工具链的"用户人工确认"设计意图。

---

### 红线 2:工具链报错不得标注为"已知 bug"并继续

**禁止话术**:

- "这是已知 bug,不影响主产物"
- "警告非阻断,可以忽略"
- "脚本 bug 不是我们的问题,先跑完流程"
- "markdown lint 警告 / python 警告忽略"
- "硬编码问题,我手工绕过"

**正确处置优先级**:

1. 读报错信息,定位根因
2. 能修脚本或数据 → 当场修,重跑;告知用户修了什么
3. 根因是脚本设计限制或需要重大改动 → 停下上报:"X 脚本报 Y 错,根因 Z,我建议 A/B/C,你选哪个?"
4. 绕过动作必须经用户明确授权,并在报告中单独列出绕过项

**典型错误示范**(不得重复):

- v45_merge 报某 Part 目录路径缺失 → AI 跳过:"脚本按名字查错目录了,可以忽略"
- export_deliverables.py 报字段映射硬编码不匹配 → AI 不上报,手工绕过

---

### 红线 3:AI 输出的事实必须有来源

**适用范围**:tender_brief.md、outline.md、chapter_*.md、filled.docx、assembled.docx 任何用户可见产物。

**允许的事实来源**(只此三类):

1. **招标文件原文**(tender_raw.txt / tender_brief.json 的 raw_lines_for_ai / tables)
2. **用户对话中给出的字面输入**(包括当前会话和已沉淀到项目 yaml 的历史输入)
3. **referenced 文档明确列出的公开事实**(如 references/doc_format_spec.md 的默认排版值 → 必须标【降级使用默认值】)

**禁止的来源**:

- 模型训练数据(GB 标准号 / 政策文件年份 / 行政区划数字 / 公司历史等一律不得从记忆里取)
- 对未明示事实的"合理推测"(如"60 天工期 → 推断为 D+15/D+30/D+45/D+60 四节点"不允许)
- "行业常识"(如"信息化基础盘点通常包括政务云 / 专网 / 能力平台"——如果招标文件没说,不写)

**替代做法**:

- 留空并标注 `【招标文件未明示,待用户确认】`
- 关键事实缺失时,加入 tender_brief.md "提醒维护者补"清单

详见 `references/ai_output_rules.md` R1 / R5。

---

### 红线 4:工具链内部术语不外泄到用户产物

**内部术语**(只能在 SKILL.md / 脚本代码 / 本文档中使用):

- 取档策略 / 素材钩子 / 应答骨架
- production_mode / part_attribution / section_anchor / sub_mode
- 工具链内部轮次标记(v2、v2 单元 N、v2 补丁 N 等)
- __PENDING_USER__ / __PENDING_AI__ / __SKIP__(只在 schema 层,不进 filled.docx)

**对外产物**(用户可见)必须用自然语言:

- "取档策略" → "评分档位要求"
- "素材钩子" → "素材来源"
- "应答骨架" → "章节结构建议"
- "主撰类 Part" → "由投标方撰写的方案类章节"
- "__PENDING_USER__" → "【待填:字段描述】"

详见 `references/ai_output_rules.md` R8。

---

### 红线 5:AI 不扩展用户字面输入

用户输入字面字符串 → AI 原样引入,末尾可标注 `(用户字面输入)`。

**不得做的事**:

- 扩写(用户说"线上交付" → AI 补"电子版提交 + 中期汇报 + 专家评审均线上")
- 补"常识性"细节(用户说"技术部分只写架构" → AI 补"角色职责分工表 + 汇报机制")
- 推测补救(用户说"没有本地化信息" → AI 补项目所在地气候 / 语言民族 / 行业架构适配专题等)

**需要扩展时** → 停下问用户:"要不要把 X 扩到 Y 粒度?"

详见 `references/ai_output_rules.md` R2 / R4。

---

### 红线 6:AI 不得代替用户选择投标主体

**适用范围**:`companies.yaml` 存在 ≥2 家合格 own 主体(即 `type=own` 且 `status != placeholder`)时。

**AI 的正确回应**:

- 若 `tender_brief.json` 的 `extracted.bidding_entity` 已有值 → 原样使用,不自作主张切换
- 若未设置且只有 1 家合格 own 主体 → 允许自动选中(单选无歧义)
- 若未设置且有 ≥2 家合格 own 主体 → **必须停下让用户选**,不得"按字母顺序选首个" / "按 created_at 选最新"等启发式代决策

**不得做的事**:

- 未经用户明示默认用 own_default 或其他任意 own 主体
- 多主体下用 `--non-interactive` 模式静默选中某家(必须配合 `--entity-id` 明示)
- 把投标主体 id 硬编码到 intermediate.json 的 path 字面并用此绕过主体选择

**工具链**:`scripts/select_bidding_entity.py` 负责选择;`c_mode_run.py` 启动时若 `extracted.bidding_entity` 缺失会自动触发它。intermediate.json 里 path 的 company_id 字面不再可信,`c_mode_fill.py` 一律用 `extracted.bidding_entity` 覆盖。

---

## 工作前必读清单

每个 AI 代理开始工作前必须加载以下文档:

1. `SKILL.md` — 工作流程
2. `references/ai_output_rules.md` — 输出规则(R1-R10)
3. `CLAUDE.md`(本文档) — 硬红线

SKILL.md 各阶段开头会引用 `ai_output_rules.md` 的对应规则条目,**不得跳过引用**。

---

## 用户文件编辑约定

- `companies.yaml`:由 `add_company.py` 脚本维护,AI 不手工编辑
- `.reviewed` 标记:由用户手动创建(见红线 1)
- `assets/` 目录:由 `ingest_assets.py` / `triage_unsorted.py` 脚本维护
- `projects/{项目}/output/` 下的 AI 可写文件:tender_brief.md / json、scoring_matrix.csv、outline.md、chapter_*.md
- `projects/{项目}/output/` 下的 AI 只读文件:tender_raw.txt(脚本产出,不可改)、.reviewed(用户闸门)

---

## 变更记录

- 2026-04-23 v2.0.0 首发:6 条根级硬红线对外发布,形成通用协作契约
- 2026-05-08 v3.0.0:V3 期间精化红线 5 / 6 文案,无新增红线
- 2026-06-08 V4-7a:同步当前主线版本口径,硬红线本身不变
