# tender-writer 变更日志

## V4-skel · 2026-06 · 三待办结构层补全(占位喊话地图)

把 V4 剩余三待办(V4-2b / V4-1b / V4-7)做到结构层 —— 字段、接口、调用链、占位接住,让完整跑一次能全程不断流;实现层留待真实输入暴露后再修。**核心交付不是代码骨架本身,而是一张"哪里真 / 哪里占位"的地图**:每个占位都自己喊出"我是占位、实线未做、看某 sidecar",完整跑时铺成产物里的占位标记,Hugin 据此一次性定三待办的实线该怎么填。

- **V4-2b 结构层(C1-C3)**:`enumerate_inventory()` 每条候选加 4 个 frontmatter 字段(`review_status` / `valid_until` / `issuer` / `applicable_scope`)值留 `None` 不读、CLI 喊"未消费值 None";`asset_query.rationale` 字段定义 + 未填透传并喊话 + `selection_rationale.json` sidecar schema;`lookup_priority` 非默认档(`name_match_first` / `review_status_first`)命中时 fallback `latest_year_first` 并 emit 警告(把"选了没生效"从静默变显式)。实现层(frontmatter 解析 / rationale 详略 / 多档判据)留待真实投标手感驱动。

- **V4-1b 结构层(C4-C6)**:含图段落只读检测(不碰 `<w:drawing>` 剥离) → 整段跳过 → 原位插可见占位段「此处缺 N 张证书图,投标前人工放入原件」+ 产 `missing_elements.yaml`(含图段计数 / 表内含图粗粒度 / sections 数)。**R10 红线**:不静默丢图,Hugin WPS 打开产物看得见缺图位置。实现层(图片 OXML 拷贝 + media part 复制 + relationship 注册)留待真实含图 anchor + 人工目检,与 V4-1a 表格保真同类深度。公章红线不变(签章是用户法律动作,工具不代生成)。

- **V4-7 结构层(C7-C9)**:`v45_merge` 在 `composer.append` 后、`composer.save` 前接入 `_post_merge_normalize` hook(当前 noop)+ 产 `merge_normalize.log` 记录四维协调状态(`font` / `table_width` / `section` / `page_number` 全 `"noop"` 字符串)。实现层(cross-doc 协调规则)留待真实多 Part 合并的视觉冲突驱动,深度与 V4-1a 同类。

- **验证**(沿 V4-1a "验生效不验存在"教训):`test_v4_skeleton_e2e.py` 8 case 验占位喊话**真的喊出来了**(stderr 喊话行 / 产物可见占位段 / sidecar `"noop"` 字面),不只验"字段加了"。完整跑全程不断流。

- **R10**:V4-skel 任务性质(大量 plan 落盘 + stderr 喊话)必然涌入 plan-style lookalike(未来文件 / 符号引用 / 示例路径 / 历史 plan / gitignored)。13 处逐条登记进 `r10_allowlist.yaml`(各带性质说明),基线语义保持"allowlist 外零违规"(仍是干净的回归探针,不放宽基线数字)。此 allowlist 是过渡桥,根治见 `docs/v4_backlog.md` 候选项 #2(扫描器规则识别 plans/ lookalike),届时应被规则替代移除。

- **静态占位点清单**见 `plans/v4-structure-completion.md` §4.5(不另立单独文件,Hugin Phase 1 裁定);完整跑产出的运行时地图 `final_tender_package/v4_placeholders_map.md` 不入仓(运行时产物)。

---

## V4-1 · 2026-05-29 B asset 表格 + 段落样式保真·V4-1a

V4-1(B asset 完整保真)拆为 V4-1a(段落 OXML + 表格)+ V4-1b(图片/页眉页脚,押后)。本次完成 V4-1a:B 模式 asset 注入 assembled.docx 由「仅提取段落文本(`add_run(para.text)`)」升级为「OXML element 拷贝 + 跨 part ref name-based rebind」,表格 / 段落样式 / 字体保真。

- 实现:遍历源 docx body 的 `<w:p>` / `<w:tbl>` element 整体 deepcopy 入 assembled.docx,表格(含 `tblGrid` 列宽)、段落级样式、run 级字体/加粗随 element 自带。跨 part ref 按 `w:name` 映射 rebind —— `tblStyle` / `pStyle` 的源 styleId(WPS 数字 id)映射到 master 同名标准样式(`Table Grid` / `Heading 2`),视觉零损失、不复制 style 定义、不处理 id 冲突。
- `numId`(自动编号)注入时 strip + warning:依据 anchor 实测(段落字面无编号前缀 + 孤立单段 + master 无多级 decimal 可复用),strip 丢「1.1」装饰前缀但标题语义由 `pStyle` rebind 保留,warning 提示用户可手补编号字面。已知降级,非静默。
- anchor(用户提供 / fixture-first):`assets/公司资质/own_demo/_raw/1.docx`,WPS 导出真实业绩证明表(脱敏,9×7 表格 + `numId`)。7 个测试 case 真验:列宽 7 个 dxa 值逐值对照(招牌目标)/ `tblStyle`+`pStyle` rebind 成功 / `numId` strip / Heading2 加粗经 `pStyle` 保留。
- 公章:整个 tender-writer 不做(原则级红线,非待办)。签章是用户的法律动作(物理盖章 / 电子签章),工具不代为生成,投标时公章页由用户手工处理。详见 business_model §8 #N21。
- V4-1b 待做项登记(不在本次):图片 / inline_shape 注入(media part 复制 + relationship 注册)、页眉页脚 / section 保真。扫描件保真待定。
- 字体 fallback 修复(V4-1a.6/.7):deepcopy 搬入的表格 run 原仅靠主题字体(`rFonts` 只 `w:hint` 无字体名),注入 master 后中文 fallback 到 MS 明朝(L4 灾难复现)、西文走 theme Cambria。修法:注入 run 补显式 `rFonts`(中文宋体 / 西文 Times New Roman / cs Times New Roman,跟 master `apply_default_styles` 一致),断主题 fallback 路径;仅补「无字体名」的 run,源已显式指定字体的尊重不覆盖。
- fixture 对齐 + 字号归化(V4-1a.8/.9):(1) 测试夹具 `_inject_anchor_to_tmp_doc` 原未调 `apply_default_styles`,致目检产物标题显 python-docx 默认 Heading2 蓝(`4F81BD`);生产路径本调了、标题实为黑。夹具补 `apply_default_styles` 对齐生产,消除目检假象。(2) 字号归化:剥源 run 级 `sz`/`szCs` 让字号回落 master Normal,统一注入内容字号;段间距/缩进(中文排版)、字体(V4-1a.6 显式宋体/Times New Roman)、加粗/斜体强调均保留不剥。
- 表格字号固化到 master(V4-1a.10/.11):此前"表格比正文小一号(14→12pt)"约定只活在 `docx_builder.add_table` 的 per-run set,没固化到 style 系统 —— 注入表格(deepcopy 绕过 `add_table`)拿不到约定,V4-1a.9 剥 run 级 `sz` 后回落 docDefaults 11pt。修法:新增单一事实源常量 `DEFAULT_TABLE_SIZE_PT=12`,TableNormal style 加 `sz=24`(12pt)、`add_table` per-run set、`_body_size_to_table_size` 三处均派生自该常量。TableGrid basedOn TableNormal,注入表格 `sz` 被剥后回落 TableNormal 的 12pt(V4-1a.9 剥 `sz` 反成正确路径)。per-run set 保留为双层(避免改 `set_run_font` 接口的 ripple,值由单一常量保证一致,非 bug)。所有表格路径(`add_table` 生产 / 注入 / 手贴)字号统一 12pt。
- 表格 cell 字号 per-run 真修(V4-1a.12/.13):V4-1a.10 给 master TableNormal style 加 `sz=24` 期望兜底表格字号,Hugin WPS 目检发现 cell 文字仍 14pt。实测根因 = OXML 字号继承优先级:cell 段落无 pStyle 隐式走 Normal(`sz=28=14pt`),段落 style 优先级高于表格 style(TableNormal `sz=24`),TableNormal 永远被覆盖,对 cell 文字无效(`add_table` 表格 12pt 实际靠 per-run set,非靠 TableNormal style)。修法:删 TableNormal `sz=24`(实测无效的死代码),按 `add_table` 同款给注入 cell 内 run per-run set `sz=24`+`szCs=24`(run-level rPr 是继承链最高层,XML 有则 WPS 必取,不赌继承)。`DEFAULT_TABLE_SIZE_PT` 常量保留为真单一事实源(被 `add_table` per-run + cell per-run 两条真实路径派生)。测试同步从"验设置写入"改为"验 cell run 最终字号生效"(case_10 验表内 run `sz=24`、case_9 验表外段落剥 `sz` 走 Normal 14pt),纠正 V4-1a.10 自检 PASS 但渲染不符的验证盲区。

人工目检项(docx 保真自动化兜不住的视觉项,Phase 3 由用户打开注入产物核对):表格边框完整不变形 / 列宽视觉正确 / Heading2 标题样式 / 跨 WPS 渲染无字体 fallback / 单元格内多段落 + 中文换行。XML 断言验「结构/数值对」,视觉验「渲染对」,两者互补。

本次零图片/页眉页脚/公章/provider 改动(V4-1a.10 显式扩 scope 改 master `docx_builder` 加 TableNormal sz 固化,乙裁定);`run_all.py` 14→15 PASS(新增 `test_b_mode_v4_1a` 10 case,含 V4-1a.7 字体 fix case_8 + V4-1a.9 字号归化 case_9 + V4-1a.10 表格字号固化 case_10);R10 scan 基线持平(2 处 pre-existing false positive,V4-1a 零新增)。

---

## V4-2 · 2026-05-29 B 智能匹配·V4-2a 链路打通

V4-2(B 智能匹配)拆为 V4-2a(链路打通)+ V4-2b(元数据精化 + rationale)。本次完成 V4-2a:让 AI 在 B 模式 extract 阶段写 intermediate.json 时 awareness 库内候选 + 本 Part 关联评分项,据三件源选材,消除此前"库空仍盲写 asset_query"的行为。

- 机制(裁定甲):脚本扫候选 + AI 选。新增 `CuratedLocalAssetsProvider.enumerate_inventory()` 扫 assets 文件系统产候选清单(仅 `category` / `company_id` / `filename` / `year`,不读 frontmatter);`b_mode_extract.cmd_extract_text` 产两个 sidecar(`scoring_matrix_excerpt.md` 本 Part 评分项关键词 + 证据材料 / `assets_inventory.json` 候选清单);`SKILL.md` 阶段 4-B 加 Step 3 选材约束,要求 AI 读三件源、`asset_query.inventory_match` 选真实候选。脚本只产候选清单,AI 做语义选择(沿 R10 + 决策 #5)。
- 占位(裁定甲 / 复用 V4-4 范本):库内无匹配候选时 `inventory_match` 标占位(`__PENDING_USER__`),不盲写库内不存在的条目。字段定义在 `docs/manifest_schema.md`。
- 边界:V4-2a 只扫文件系统可见信息,frontmatter 14 字段 0 消费;下游 `b_mode_fill` / `resolve` 已通,本次不动;设计意图是用户按目录结构丢文件进 `assets/` 即可用,零元数据负担。

V4-2b 待做项登记(不在本次):`asset_query.rationale` 字段 + `selection_rationale` 产物(为什么选 / 可回查);frontmatter 元数据(`review_status` / 有效期 / 适用范围 / 颁证机构)参与匹配;`lookup_priority` 的 `name_match_first` + `review_status_first` 两档。

R10 / PER 流程登记(本次 Phase 3 发现,非 V4-2a 引入):

- `r10_consistency_check` 报 `plans/v4-3.md:28`(指向 handbook 未建的 `ISC.md`)与 `plans/v4-4.md:24`(描述 fixture 改名前的 FROM 名)2 处路径引用为违规。经判定二者均为 false positive 非真违规:plan 作为过程文档正确描述「指向未来文件」「改名来源」,路径不存在是预期且正确的。V4-2a 守 scope 不修(不加 allowlist 不动 plan)。
- 待办 1:扫描器应以规则识别 `plans/` 内「未来文件 / 改名来源」类路径引用(合法 lookalike),而非逐条 allowlist;沿 V4-0.2「能规则识别的用规则、真个案才 allowlist」原则。
- 待办 2:R10 scan 纳入 PER Phase 3 自检标准动作(V4-0 建了 `r10_consistency_check` 但未进 Phase 3 三件,V4-3/V4-4 Phase 3 均未跑、V4-4 已确认是疏漏);以后 Phase 3 自检含「跑 R10 scan + 基线持平或解释新增」。

本次零下游改动(`b_mode_fill` / `resolve` 未碰)、零 frontmatter 消费、零其他 sub_mode 影响;14/14 测试 PASS(含 V4-2a 6 新 case)。

---

## V4-4 · 2026-05-29 C-attachment 真实现

C-attachment(扫描件附件,整份文件单独挂,不进主响应文件文本流)从挂档状态真实现:schema 层原已收值,本次把 migrate / extract / fill / merge / export 五个执行端的 NotImplementedError / skip 改为真实业务分支,端到端跑通。

- 边界:与 B 模式区分明确 —— B 模式素材内容融进 assembled.docx 文本流,C-attachment 整份文件作为独立附件单独挂,不进任何文本流。附件源复用本仓库 assets(CuratedLocalAssetsProvider 同型),不接外部源。
- 占位策略:附件源文件缺失时产占位(`__PENDING_USER__`)不硬失败(部分附件本就需用户人工放置);占位状态显式可见 —— attachments 清单标占位 + operations_checklist 列出待人工放置项 + export 透传,不静默产空附件。
- 测试:原 `case_5` / `ok_skip_cattach` 的"验整项跳过"断言改造为真行为断言(入 `merge_order` + `attachments` 产出 + `ops_checklist` 附件段 + 占位路径);fixture 去 `_skip` 后缀对齐真实现语义;新增 e2e case 覆盖 extract→fill→merge→export 全链路含占位条目。
- 候选项登记(不在 V4-4 范围):招标文件「投标文件构成与装订」要求的结构化抽取 + 下游消费 —— 当前 parse_tender 仅以 section_anchors 标位置、未抽内容、无结构化字段、无下游消费,demo 实测该段全部【待补充】。附件目录布局现采用工具自定默认(`attachments/<part>/`),未消费招标文件装订要求。此项留 V4 后期评估。

本次零 schema 层改动(C-attachment 在 brief_schema 已完整)、零 C-template/C-reference/A/B 模式现有逻辑改动;新增业务分支均参照同型 sub_mode 实现。

---

## V4-3 · 2026-05-29 C-reference 诚实化收尾

V4-3 经两轮 Phase 0 实测确认 C-reference 决策层已在 fixture 层验证(brief 解析 / v45_merge 分流 / export 映射三处纯函数断言),范围收敛为诚实化收尾,非功能实现。

- C-reference 执行端样例(真实 instructions.md 渲染落盘 + 合并器读取转 ops_checklist)在 fixture 层零覆盖;V4-3 评估后决定不建,推迟到 V4 整体完成后由真实使用场景驱动。理由:demo_cadre_training 无单独提交件需求,现阶段造样例需虚构 anchor,违背「样例由真实场景长出」原则。
- build_baseline.py C-reference 首例 entry 同步推迟(注释已诚实化);export / v45_merge 两处测试 case 加防误读注释,明确为函数级映射断言非端到端。
- 本条债 + `_workspace/audit-2026-05-27.md` 共同作为 V4 整体完成时 handbook 一次性 distill 的输入。

本次零业务代码逻辑改动:仅注释 / 测试注释 / changelog / plan 文档。

---

## V4-0.2 · 2026-05-29 R10 扫描升级 + 修剩余违规 + 误报率盲区 fixture

V4-0.1 文档化完成后,V4-0.2 升级 R10 一致性扫描脚本,把"注释/文档里的文档引用 / 字面引用的常量 / 字面引用的文件路径"三类纳入扫描,并修剩余 audit §5 违规 + 扫描新发现的真违规。

**新增 / 修复**(7 commits 顺序):

| # | commit | 内容 |
| --- | --- | --- |
| 2 | `f053221` | `scripts/tests/r10_consistency_check.py` 新增(扫描脚本)+ clean/dirty fixtures + `r10_allowlist.yaml` + `run_all.py` 注册 |
| 3 | `cd7c224` | `scripts/build_baseline.py:106-107` stale `C-reference` 注释 + dict entry 修(audit §5 #2) |
| 4 | `37b4025` | `SKILL.md:762` 引用已删常量 `brief_schema.SUB_MODE_JUDGE_PROMPT` → 改引 `docs/business_model_v1.md` §8 #N20(audit §5 #3) |
| 5 | `b81063b` | `templates/README.md` 首句对齐当前状态(audit §5 #6;主体不动) |
| 6a | `93b70f6` | **1 真违规修** `scripts/b_mode_extract.py:105` 引用已删常量 `B_MODE_EXTRACT_PROMPT` → `§8 #N21`(audit §5 漏的) + 扫描脚本 3 项质量(emoji Windows GBK crash → ASCII / exit code 被 print 副作用污染 → 单独 wrap / 自身 docstring 4 处自指误报 → EXCLUDE_FILENAMES + 自指 allowlist) |
| 6b | `9d53d70` | 扫描规则升级(元变量识别 `* / ? / {} / <> / -N / -X / your_project` + `EXCLUDE_PATH_PREFIXES` 排除 fixtures/)+ allowlist 扩 C/E/F 三类 + `legitimate_lookalikes.py` clean fixture + `case_8` 验误报率盲区 + `_r10_report.md` 写 v1→v2 演化教训 footer |
| 7 | (本 commit) | `plans/v4-0.md` 入仓(Phase 1 plan 定稿)+ changelog 总账 |

**真违规一例**(audit §5 漏的):`b_mode_extract.py:105` 跟 `SKILL.md:762` 同型(都引用已删常量),audit 抓 L762 漏了 L105。是 V4-0.2 扫描升级价值的实证 —— 升级前 v1 全仓扫 66 处,**实际 1 真违规 + 65 误报**;v2 加元变量识别 + allowlist 扩后归 0。

**误报率盲区教训**(进 handbook):扫描类工具的 fixture **不能只验"抓得全真违规"**,还要验"不误抓合法样本"(元变量占位 / 合法自指 / 跨仓引用)。这是 fixture-first clean+dirty 配对的一个盲区维度 —— clean fixture 必须包含"看起来像违规但其实合法"的样本(commit 6b 新增 `clean/scripts/legitimate_lookalikes.py` + `case_8` 即此用途),才能在脚本规则收紧/放宽时立刻暴露误报率退化。

**追溯**:延续 V4-0.1 追溯说明,V4-0.2 补齐扫描升级面 —— v3.0.1 / v3.0.2 changelog "已对账 doc-code consistency" 只覆盖了 print/raise 文案,**没覆盖注释/文档引用 / 字面常量 / 字面路径** 三类。V4-0.2 起这三类纳入 R10 扫描标准范围,后续维护者跑 `r10_consistency_check.py` 即可全覆盖。

**验证**:

- `scripts/tests/test_r10_consistency_check.py` · 8 case / 8 PASS
- `scripts/tests/run_all.py` · 13 文件 / 13 PASS
- `scripts/tests/r10_consistency_check.py --quiet` · EXIT=0,0 违规

**不动**:任何业务代码逻辑 / `production_mode` / `sub_mode` 分流路径 / 测试 fixture 之外的 JSON / DOCX。

---

## V4-0.1 · 2026-05-28 business_model_v1.md 文档化(解 16 + 2 处空指针)

V4-0 启动前 audit 发现 `scripts/` + `SKILL.md` 共 16 处显式 `business_model §X #NXX` 引用 + 2 处隐含 `#NXX` 引用,但 `docs/business_model_v1.md` 不存在,全为空指针。本次落地该文档,把散落在 SKILL.md 阶段 4-C / 4-B / 6 + `brief_schema.py` / `c_mode_extract.py` / `c_mode_fill.py` / `parse_tender.py` / `migrate_brief_schema.py` / `export_deliverables.py` / `v45_merge.py` 注释里的字面整理成独立文档。

**沉淀章节**(只对应仓内实际引用,不补造跳号):

- §8.3 #N16 — `__REGEX_DRAFT__` 机制删除
- §8 #N19 — Part 完整重做触发条件
- §8 #N20 — sub_mode 判据 + C-attachment 挂档
- §8 #N21 — B 模式 `assembly_order` 组织判据
- §8 #N22 — C-reference 不进 `final_response.docx`
- §8 #N24 — 交付层独立于工具链内部
- §9 — skill 模型声明

**R10 诚实声明**:本文档是字面回溯沉淀的"引用锚点集",**不是完整业务模型权威文档**;只对被引用的 §X #NXX 字面负责,不保证业务模型整体完整性。`#N17` / `#N18` / `#N23` 等跳号在仓内无引用,留白不补造。

**追溯**:v3.0.1 / v3.0.2 changelog 字面 "已对账 doc-code consistency",但 R10 扫描漏了 `business_model` 引用一片(16+2 处)。本次清理 + V4-0.2 扫描升级补齐该漏网,后续 R10 扫描覆盖"注释/文档里的文档引用 / 字面引用的常量 / 字面引用的文件路径"三类。

**不动**:16+2 处引用注释保留原文不改,只让引用从空指针变实指针。

---

## v3.0.2 · 2026-05-08 CLI 提示文案对齐(Codex 二次审视 + 扩展扫描)

V3.0.1 发布后 Codex 二次审视抓到 2 项必修代码问题,叠加全脚本 doc-code-consistency
扩展扫描另外抓到 1 项,三处都是 user-facing print 文案与代码实际控制流不符,对齐 R10
(诚实化,不夸大)。

| # | 问题 | 修复 |
|---|---|---|
| #1 | `parse_tender.py` L803 `--force` 警告误指 ".reviewed 标记因 hash 漂移失效",实际 `ensure_reviewed` 只查文件存在性 | 显式说明 "ensure_reviewed 只检查 .reviewed 文件存在性,不校验 hash,下游会放行空骨架,重跑前请手动删除 .reviewed" |
| #2 | `v45_merge.py` L364 C-reference 统计是 `merge_order` 声明数,与实际写入成功数脱钩(`instructions.md` 缺失 `continue` 不计) | 主循环维护 `c_ref_written` counter,仅成功路径递增;print 改为 "C-reference: {written}/{declared}(成功写入/声明数量)" |
| #3 | `demo_reset.py` L131-135 警告误指 ".reviewed 不存在则不能跑 parse_tender",实际 parse_tender 不调 `ensure_reviewed`,`.reviewed` 是下游脚本的闸门 | 显式列出 `build_scoring_matrix / generate_outline / b_mode / c_mode / compliance_check / v45_merge` 等下游脚本会被拦住,parse_tender 不在其中 |

扩展扫描覆盖 33 个 `scripts/*.py`(非测试),逐条核对 `print` / `raise` / `sys.stderr`
文案 vs 实际控制流,32 个对齐 + 1 个真问题(#3)已含本版本。

实测验证:`./run_script.bat tests/run_all.py` 12 文件全 PASS,无回归。

---

## v3.0.1 · 2026-05-08 缺依赖 + 路径穿越 + 硬编码统计(Codex 外部审视)

V3.0.0 发布后 Codex 外部审视抓到 5 项问题(3 项必修代码 + 2 项文档措辞)。

| # | 问题 | 修复 |
|---|---|---|
| #1 | `requirements.txt` 缺 `openpyxl`,`export_deliverables.py` 写 xlsx 在 clean install 后会 ImportError | 加 `openpyxl>=3.1.0` |
| #2 | SKILL.md 暗示 .reviewed 重跑会"自动失效",实际 `ensure_reviewed` 只查文件存在性 | 明示限制:"⚠️ 当前闸门只检查 .reviewed 文件存在性,不校验 hash,用户必须手动删除标记。hash 校验机制留 V4 实现" |
| #3 | SKILL.md / README.md B 模式描述暗示完整文档复制(含表格/图片/公章),实际 V3-1 仅文本提取 | README L56 标题加"(当前为文本提取)" + 末尾"表格/图片/公章/扫描件保真留 V4";SKILL L793 加详细限制 + "投标前需手工核对原件" |
| #4 | `export_deliverables.py` 解析 `args.project` 后无校验直接拼路径,`--project ../../../etc` 可逃逸到 `projects/` 之外 | `args.project` 必须是单个目录名,不含 `..` `/` `\`,否则 `sys.exit(1)`(注:用户原 plan 写 `startswith("projects/")` 不适用,改为更准确的 `..` + 路径分隔符 双重检查) |
| #5 | `v45_merge.py` 写死 "C-reference: 1",与实际项目 sub_mode 数量脱钩 | 改为 `sum(1 for ... if kind == 'c_reference')` 真实统计(后 V3.0.2 #2 进一步精化为 written/declared 对比) |

实测验证:`./run_script.bat tests/run_all.py` 12 文件全 PASS,无回归。

---

## v3.0.0 · 2026-04-30 14 项改进

v3 在 v2.0.x 基础上完成 14 项改进(V3-1 至 V3-14)。详见 [docs/v3_planning.md](v3_planning.md)。

### 主要改进项(V3-1 至 V3-14)

| # | 项 | 核心交付 |
|---|---|---|
| V3-1 | B 模式真实 asset 查询 | `CuratedLocalAssetsProvider` 默认走 `assets/<类别>/<company_id>/_raw/` 真实命中,缺省回 placeholder |
| V3-2 | 测试覆盖扩展 | 测试文件 1 → 12,涵盖 parse_tender / generate_outline / b_mode / c_mode / compliance_check / check_chapter / check_cross_consistency / 等 |
| V3-3 | timing hook 埋点 | `_timing_hook.stage_timer` 给 7 核心脚本加阶段耗时埋点,产 `_timing_report.md` |
| V3-4 | 正文级缝合句检测 | `check_chapter.py` 新增滑窗算法(30 字内 ≥6 关键词标 fail / ≥5 警告),抓 AI 写作时关键词堆砌 |
| V3-5 | --section-only 跳封面/目录 | `compliance_check.py` 加 `--section-only` flag,自动文件名识别 + 显式覆盖 |
| V3-6 | 扫描版 PDF 检测 + fallback | `parse_tender.py` 自动检测扫描版 PDF(全文平均 < 50 字/页),提供 `--ocr-text <txt>` fallback |
| V3-7 | Word 直切集成 c_mode_run | c_mode_run 自动分流模板填充 vs 整段直切场景 |
| V3-8 | docx 字体安全深度检查 | `compliance_check.py` `check_font_safety` 扩到 fontTable.xml 级 warn(白名单 + boilerplate 容忍 + 中文别名归一化 SimSun=宋体)|
| V3-9 | 跨章节一致性扩充 | `check_cross_consistency.py` 加 3 项:项目名/采购方字段一致性 / 简历 vs 架构图人名一致性 / 章节交叉引用编号有效性 |
| V3-10 | 五阶段口径统一 | "五阶段" 措辞全仓统一为"五阶段主干 + 并列阶段(4-B/4-C/6)",对齐 `docs/DESIGN.md` ground truth |
| V3-11 | B 模式 README/SKILL 诚实化 | 措辞从"占位红字"改为"真实 asset 查询 + 占位 fallback",对齐 V3-1 实际能力 |
| V3-12 | SKILL.md description 精简 | 触发关键词 25 → 10(招标文件/招标公告/投标/技术标/响应文件/评分办法/废标条款/实质性响应/政府采购/竞争性磋商) |
| V3-13 | demo 重跑工具 | `scripts/demo_reset.py` 提供 demo 项目无破坏重跑标准化路径(默认 dry-run + --yes 执行)|
| V3-14 | 开源前最终审计(四层结构)| 机器扫(敏感信息/死链/TODO)+ 行为验证(回归/端到端/命令示例/schema 一致)+ 语义一致性(三文件互对/plans/docs)+ 新文件(LICENSE/CONTRIBUTING/README 升级)|

### 关键文件新增

- `docs/DESIGN.md` — 设计哲学(为什么这么设计)
- `docs/v3_planning.md` — V3 改进路线图 + 完成判定
- `docs/manifest_schema.md` — manifest.yaml 字段定义
- `scripts/demo_reset.py` — demo 项目无破坏重跑工具
- `scripts/tests/test_*.py` — 12 个测试文件全套
- `plans/v3-*.md` — V3-1 至 V3-14 plan 历史快照(13 份 + V3-14 收尾)

---

## v2.0.0 · 2026-04-23 首发

v2 在 tender-writer v1.1 基础上经过两轮迭代沉淀而来,包含**项目类型识别、AI 输出规则常驻化、docx 渲染质量总攻、非交互批量化、跨章节一致性检查、工具链 bug 清扫**等十项改进。

### v1.1 → v2.0.0 主要变化

| 模块 | v1.1 | v2.0.0 |
|---|---|---|
| outline 模板 | 单一模板,手工重组 | 按 `extracted.project_type` 五选一(工程/平台/研究/规划/其他),自动选骨架 |
| AI 输出规则 | 散落在 SKILL.md 各章节 | 常驻文档 `references/ai_output_rules.md`,R1-R10 十条红线 |
| docx 渲染 | 默认灰色字体,中英混排空格不清理 | 统一黑色 RGB(0,0,0) + 中文宋体 + 相对字号 + `**bold**` 内联解析 + 图占位区块 + 中英空格后处理 |
| C 模式填充 | 交互式 `input()`,多 Part 需 10 次手动回答 | 非交互,变量缺失时写入"【待填:xxx】"红色占位;`c_mode_run.py --all` 一键批量 |
| B 模式组装 | 单 Part 单次手动 | `b_mode_run.py --all` 一键批量 |
| 跨章节一致性 | 无(只能靠 compliance 粗查) | 新增 `check_cross_consistency.py` 抓团队成本 vs 预算、承诺时间 vs 工期等矛盾 |
| 投标主体选择 | 硬编码或无支持 | `select_bidding_entity.py` 显式选择,写入 `extracted.bidding_entity`,多主体场景停下让用户选 |
| v45_merge 合并顺序 | 硬编码某项目 Part 顺序 | 从 `response_file_parts` 动态推导,任何项目通用 |
| export_deliverables 映射 | 硬编码某项目 Part 名 | 动态生成交付物清单 |
| check_chapter 检查项 | 6 项 | 新增 [7] AI 输出空格规范(R3 落地),≥3 处 fail |
| 协作契约 | 隐含在 SKILL.md | `CLAUDE.md` 6 条硬红线,任何 AI 代理工作前必读 |

### 新增文件

- `CLAUDE.md` — Claude Code 协作契约(6 条红线)
- `references/ai_output_rules.md` — AI 输出常驻约束(R1-R10)
- `references/outline_templates/{engineering,platform,research,planning,other}/` — 5 类 outline 模板
- `scripts/c_mode_run.py` / `scripts/b_mode_run.py` — 一键批量运行器
- `scripts/check_cross_consistency.py` — 跨章节一致性检查
- `scripts/c_mode_docx_passthrough.py` — Word 上游原样切用(beta)
- `scripts/select_bidding_entity.py` — 投标主体选择
- `scripts/tests/test_budget_parsing.py` — 预算解析 fixture
- `docs/v2_design_notes.md` — 设计决策记录
- `docs/v2_roadmap.md` — 未来路线图

### 示范项目

`projects/demo_cadre_training/` — 虚构"A 市 2026 年度干部综合能力提升培训服务采购项目",预算 500000 元,工期 60 日历日,Clone 下来可直接跑通端到端。

---

## v1.1 及之前

v1.1 及之前的变更记录未迁入 v2 对外版。v1 是内部迭代期,对外公开从 v2.0.0 起步。

### v2 补丁 2(字体安全回归,2026-04-24)

**背景**:demo 重跑后 WPS 打开 final_response.docx 提示"2 个文档字体缺失:Courier、MS 明朝",标题与正文部分 fallback 到日文字体 MS 明朝。属于 v2(二轮迭代)docx 渲染质量总攻本该覆盖但漏了的回归,补作 v2 补丁 2。

**根因**:

- `c_mode_extract.render_template_docx`、`b_mode_fill.main`、`v45_merge._create_part_divider`、`v45_merge._create_inapplicable_doc` 四处用裸 `Document()` 创建 docx,**未调 `apply_default_styles(doc)`**
- `styles.xml` 的 `Normal` 样式留空,`docDefaults` 里是 `<w:rFonts w:eastAsiaTheme="minorEastAsia">`(主题字体引用)
- Office/WPS 遇到 `minorEastAsia` 主题但主题文件缺失或 `themeFontLang` 为日语时,fallback 到系统日文字体 MS 明朝
- C/B 模式所有片段 run 级 100% 无 `rFonts`,全部 fallback;v45_merge 的 divider 又成为合并 master,把空 Normal 样式传染给 final_response.docx

**修复**(最小改动):

- `scripts/c_mode_extract.py::render_template_docx`:`Document()` 后加 `apply_default_styles(doc)`
- `scripts/b_mode_fill.py::main`:同上
- `scripts/v45_merge.py::_create_inapplicable_doc` + `_create_part_divider`:同上
- 共 4 处 `Document()` 裸调用改为 `Document() + apply_default_styles(doc)`

**回归检查(补强 docx 渲染质量总攻)**:

- `scripts/compliance_check.py` 新增 `check_font_safety(docx_path)`:
  - Normal 样式必须有 `<w:rFonts>` 且 `eastAsia` 在白名单(宋体/仿宋/仿宋_GB2312/黑体/微软雅黑)
  - run 级 `<w:rFonts>` 的 `eastAsia` / `ascii` 属性须在白名单
  - 异常字体(如 `MS Mincho` / `Arial Unicode`)报 `format_issues`
- 接入 `main()` 的 format_issues 扩展,不改报告结构

**回归验证**(demo 项目):

| 指标 | 修复前 | 修复后 |
|---|---|---|
| C 模式 filled.docx(6 个)run 级 rFonts | 0/9 / 0/18 / 0/12 / 0/8 / 0/12 / 0/12 | Normal 样式继承宋体 |
| B 模式 assembled.docx(2 个)run 级 rFonts | 0/19 / 0/9 | Normal 样式继承宋体 |
| final_response.docx Normal 样式 | `<w:style ...>` 内**无** `<w:rFonts>` | `<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="宋体"/>` |
| compliance_check 字体检查 | (不存在该检查项)| 0 issue |
| WPS 打开 | 提示"2 个文档字体缺失" + 渲染日文 MS 明朝 | (待用户 WPS 重开确认) |

**baseline**:v3 → v4(4 个脚本改动,工具链指纹刷新)。

