# V4 剩余工作清单 (跨会话 snapshot)

> 本文档是 V4 期间未完成事项的快照,**不是 PER plan**(没有 commit 序列 / scope / 自检)。
> 用途:跨会话起手时直接捞,不用重新盘 git log 和 changelog。
>
> 跟现有 `docs/changelog.md` / `plans/v4-*.md` 不重复内容,能引用就引用。
>
> 最后核对:2026-05-29(V4-1a 13 commit 收口当日,HEAD = 563e037)。

---

## §1 V4 主线待办(都卡在等条件,不在代码里)

### V4-1b · B asset 图片 / 页眉页脚 / 扫描件保真

**状态**: **结构层已补(V4-skel,2026-06)** — 含图段落只读检测 + 整段跳过 + 原位插可见占位段「此处缺 N 张证书图,投标前人工放入原件」+ 产 `missing_elements.yaml`(R10 红线:不静默丢图)。实现层(图片 OXML 拷贝 + media part 复制 + relationship 注册)**待真实含图 anchor + 人工目检驱动**。
**卡在**: 实线图片保真等真实需求触发(demo 当前 anchor `assets/公司资质/own_demo/_raw/1.docx` 不含图片,缺真实样本)
**范围**(实现层): 图片 / `<w:drawing>` / inline_shape 注入(media part 复制 + relationship 注册)、页眉页脚 / section 保真、扫描件保真(待定)
**字面源**: `docs/changelog.md` V4-skel entry V4-1b bullet + V4-1 entry "V4-1b 待做项登记" bullet
**前置**: 用户提供含图片 / 公章扫描件 / 页眉页脚的脱敏真实 anchor。**没真实样本不能开工实现层**(V4-1a 13 commit 教训:docx 深度保真假设→撞→修成本高,必须 fixture-first)

### V4-2b · B 模式元数据精化 + rationale

**状态**: **结构层已补(V4-skel,2026-06)** — `enumerate_inventory()` 加 4 frontmatter 字段(值 None)+ CLI 喊"未消费";`asset_query.rationale` 字段定义 + 未填透传并喊话 + `selection_rationale.json` sidecar schema;`lookup_priority` 非默认档 fallback 并 emit 警告。实现层(frontmatter 解析 / rationale 详略 / 多档判据)**待真实投标手感驱动**。
**卡在**: 用户拿 V4-2a (`asset_query.inventory_match` 链路) 跑真实投标有手感后,才拍 3 个设计裁定
**范围**(实现层):

- `asset_query.rationale` 详略 + `selection_rationale.json` 内容填(为什么选 / 可回查)
- frontmatter 元数据(`review_status` / 有效期 / 适用范围 / 颁证机构)实际读取 + 参与匹配
- `lookup_priority` 的 `name_match_first` + `review_status_first` 两档真实判据(当前 fallback `latest_year_first` + emit warning)

**字面源**: `docs/changelog.md` V4-skel entry V4-2b bullet + V4-2 entry "V4-2b 待做项登记" bullet
**前置**: 用户拿 V4-2a 跑真实项目 → 确定 frontmatter 哪些字段值钱 / rationale 写多详 / 多档 lookup_priority 的判据是什么。**没真实手感前定的裁定可能像 V4-1a.10 那样走错**

### V4-7 · V45 合并器格式协调(多 Part 合并的字体 / 表格 / 页码 / 图片一致)

**状态**: **V4-7a 浅做完(2026-06,V4-7a.1/.1b/.2/.3)** —— `_post_merge_normalize` 浅做两维:`font_normalize: done (style-level)`(解 docxcompose 后到优先导致的 anchor Heading 蓝色)+ `table_cell_size: done`(整篇 cell run sz=24,复用 V4-1a.12 helper)。`merge_normalize.log` 五维诚实摊开(2 done / 3 noop)。**V4-7b 深押后 3 维**(run-level normalize 整篇 + section 收敛 + 页码 reset):待真实多 Part 合并产物视觉冲突驱动,与 V4-1a 同量级 cost,且做不做取决于 V4-7a 浅做完视觉是否够好 —— **不可假设 V4-7 整个完成**。
**卡在**: 重新评估投入产出后才定要不要做 / 做到什么保真度
**范围**(实现层): cross-doc 表格列宽统一 / section break 收敛(全局单 section 或 section restart numbering 显式控制)/ 段前段后规整 fragment pass / 跨 part 字体一致
**字面源**: `docs/changelog.md` V4-skel entry V4-7 bullet + V4-1a 收口实测后判断 — "docx 深度格式保真比 V4-1a 还深,假设→撞→修方式做大概率比这条线还长(13 commit / 6 轮 bug)"
**前置**: 评估投入产出 — V4-7 跟 V4-0/2a/4 那种几轮就闭环的链路类活不同,**单 Part 注入字号一项就 4 个 commit (V4-1a.9/.10/.12/.13)**,V4-7 跨 Part 协调可能更深。值不值做 / 做多深由维护者评估

---

## §2 V4 之后待决策(更靠后)

### V4-5 · templates 库

**卡在**: V4-7 之后决策,**现在连要不要做都没到时点**
**audit 定性**: "架构错位"(`handbook/_workspace/audit-2026-05-27.md` §4),当前不存在"模板库"概念,所有 C 模式 Part 从招标文件原文动态提取
**两个选项**: A 建库(新增 `templates/<category>/<name>/manifest.yaml` schema + 复用机制)/ B 改任务名为"招标文件原文承诺函识别准确率提升"

### ~~V4-6 · D 模式~~ (已挪 §5 已决策不做)

(原 V4-6 D 模式待决策, 2026-06 评估决策不做, 已挪至 §5 "已完成 / 已决策不做" 段。)

---

## §3 handbook distill 队伍(V4 全部完成后一次性 distill,期间不动)

**约定**: V4 期间不写 handbook,所有 lesson 沉淀在 `docs/changelog.md` 对应 entry 内,V4 完成后一次性 distill。下列锚点全部在 changelog / commit message / `scripts/tests/_r10_report.md` footer 里有现成字面,distill 时不用重写。

| # | 锚点 | 字面所在 |
|---|---|---|
| 1 | **docx 保真两条教训**(招牌)— 别赌 OXML 继承链用 per-run 最高优先级 + 测试验生效不验存在 | `docs/changelog.md` V4-1 entry 内 V4-1a.12/.13 bullet 末段 |
| 2 | **占位 R10 正向样板** `__PENDING_USER__` | `docs/changelog.md` V4-4 entry "占位策略" bullet |
| 3 | **attachments.yaml 模式**(占位状态结构化载体 vs 裸目录) | `docs/changelog.md` V4-4 entry 内"attachments.yaml"提及 |
| 4 | **反盲写范本**(fixture 验"AI 据真实候选选材,非凭原文盲写";V4-2a case_6 抓盲写 fail→pass) | `docs/changelog.md` V4-2 entry + V4-2a Phase 3 审评 |
| 5 | **R10 scan 进 PER Phase 3 标准动作**(V4-2a 起既成事实) | V4-2a Phase 3 评审 + 后续每个 V4-N task plan §自检方式 |
| 6 | **name-based rebind**(跨 part style 引用按 `w:name` 映射,不复制定义) | `docs/changelog.md` V4-1 entry 内 V4-1a.2 描述 |
| 7 | **R10 扫描精度演化 v1→v2**(fixture-first 误报率盲区:不能只验"抓得全真违规",还要验"不误抓合法样本") | `scripts/tests/_r10_report.md` footer + `docs/changelog.md` V4-0.2 entry |
| 8 | **fixture 与生产路径脱节**(测试夹具必须跟生产 helper 同序,V4-1a.8 蓝色误判教训) | `docs/changelog.md` V4-1 entry 内 V4-1a.8/.9 bullet |
| 9 | **Windows GBK 终端 emoji crash**(同 handbook pending-lessons #21 #24 同根,扫描脚本自身 R10) | `docs/changelog.md` V4-0.2 entry 内 commit 6a 描述 |
| 10 | **函数级断言诚实化**("happy path" 措辞防误读成端到端,V4-3.2 给 test_export_deliverables case_2 加注释) | `docs/changelog.md` V4-3 entry + V4-3.2 commit message |

**骨架核对**: "表格字号继承层级教训" = "docx 保真两条教训"第一条(别赌继承链),不重复列(条目 1 已含)。

---

## §4 候选项(登记未排期,需要时再捞)

| # | 候选项 | 字面源 |
|---|---|---|
| 1 | **招标文件「投标文件构成与装订」要求结构化抽取 + 下游消费** | `docs/changelog.md` V4-4 entry 末"候选项登记" |
| 2 | **R10 扫描器识别 plans/ 内"未来文件 / 改名来源"类路径引用**(合法 lookalike,目前手工 allowlist 2 处) | `docs/changelog.md` V4-2 entry 末"R10 待办 1" + V4-2a Phase 3 评审 |
| 3 | **C-reference 执行端样例 entry**(`build_baseline.py:106-112` 注释明示推迟到 V4 完成后由真实场景驱动补) | `scripts/build_baseline.py` L106-112 注释 + V4-3 changelog |
| 4 | **SKILL.md V45 整标合并器无独立流程节**(散在 L595 / L839 / L908 多处提及,V4-skel.9 把 V4-7 占位贴到 4-B L839 V45 现有备注块就近落,语义归属对但位置欠佳。将来 SKILL.md 整理时给合并器建独立"阶段 5.5: V45 整标合并"节,V4-skel 不动章节结构) | V4-skel.9 期实测发现 + Phase 1 裁定登记 |
| 5 | **MCPExternalAssetsProvider**(对接企业内部统一材料平台,通过 MCP 协议接外部材料库) | `scripts/assets_provider.py:14-17` docstring 预留意图 + `docs/v3_planning.md:334` "V3 不做留 V4" + `SKILL.md:837` "未来工作 V4+";V4 全期没接、连本 backlog 都没登记 — **本次顺手登记,只备查不做,状态:docstring 预留意图,未实现未排期**(跟 V4-6 信用中国不同:前者企业内部材料平台聚合,后者公网信用查询;用户关心"统一材料平台"需求时再捞) |
| 6 | **`.reviewed` 闸门 hash 校验机制**(`SKILL.md:62` 明示"hash 校验机制留 V4 实现",当前 `ensure_reviewed` 只查文件存在性不校验 hash,用户改 tender_brief.json 后必须手动删 `.reviewed` 标记否则下游脚本仍放行) | `SKILL.md:62` V3.0.1 changelog #2 期诚实化字面 + V4 全期没做;影响:重跑保护机制有缝,人工纪律兜底 — **登记备查,真出现误用再修** |

---

## §5 已完成 / 已决策不做(防误以为还要做)

V4 已落地或已决策关闭的活,跨会话起手时不要重新做:

### 已决策不做

- **V4-6 · D 模式 / "线上查资质"类自动化**(2026-06 决策不做):D 模式(信用中国类"无违法记录"查询截图)**不做**。理由:低频(一个标查一两次指定公司)、人工查+过验证码+截图两分钟、半自动化省的时间 < 搭浏览器自动化+处理验证码+截图存档的工程成本,性价比不高;这类合规材料人工查截图处理(同"证书图人工放原件"的人机分工)。**注意**:这跟资质证书是两码事(信用记录截图是独立合规材料,官网截图本就是其合法形态),不是被"工具不代为生成签章"红线覆盖的对象,纯粹是性价比决策。

### 已完成 (工程实现)

- **V4-0** (V4-0.1 + V4-0.2): business_model_v1.md 文档化 + R10 扫描升级 — 见 changelog
- **V4-2a**: B 模式智能匹配·链路打通(scoring_matrix → assets 选材 awareness)— 见 changelog
- **V4-3**: C-reference 诚实化收尾(代码已端到端,demo 实测推迟由真实场景驱动)— 见 changelog
- **V4-4**: C-attachment 真实现(5 处 raise/skip → 真分支 + e2e 跑通 + 占位 R10) — 见 changelog
- **V4-1a**(13 commit / 6 轮 bug): B asset 表格 + 段落样式 + 字体 + 字号 + cell 字号 真修 — 见 changelog V4-1 entry
- **V4-skel**(10 commit): V4-2b/V4-1b/V4-7 结构层补全 + 占位喊话地图 — 见 changelog V4-skel entry + plans/v4-structure-completion.md §4.5(静态占位点清单)
- **V4-7a**(3 commit + 1 子 fix): 合并器浅做接 master 规范(font + cell sz 两维 done)— 见 changelog V4-7a entry + plans/v4-7a.md;V4-7b 深(run-level normalize + section + 页码)仍占位押后

---

## §6 骨架核对纠正记录

**为透明,记下本 snapshot 对原始内容骨架的 3 处纠正**(以仓里实际为准):

1. **漏列 V4-1b**(骨架 §一只列 V4-2b + V4-7)。V4-1b 在 V4-1 changelog 末"V4-1b 待做项登记"明确登记为 V4-1a 押后项,跟 V4-7 是不同维度的 docx 保真:
   - **V4-1b** = 单 asset 内部(图片 / 公章 / 页眉页脚 / 扫描件)— V4-1a 没做,等真实样本
   - **V4-7** = 多 Part 合并时跨 doc 格式协调(字体 / 表格列宽 / 页码 / section)
   本 snapshot §1 补 V4-1b 为主线待办。

2. **"master 表格小一号已用 per-run 实现"** 不是候选项(骨架 §四列了)。这是 **V4-1a.10/.11/.12/.13 已完成事项**:
   - V4-1a.10/.11 加 `DEFAULT_TABLE_SIZE_PT` 常量 + TableNormal sz 兜底(后实测无效)
   - V4-1a.12/.13 删 TableNormal sz 死代码 + 改 cell per-run set(run-level 优先级最高真生效)
   已闭合,不在候选项里。本 snapshot 把这条挪到 §5 已完成,加 §6 此条纠正记录。

3. **"表格字号继承层级教训"**(骨架 §三列)= "docx 保真两条教训"第一条(别赌继承链,用 per-run 最高优先级),不必单列。本 snapshot §3 条目 1 已含此教训,不重复。

如本 snapshot 漏列其他待办,以 `docs/changelog.md` 末三个 entry(V4-1 / V4-2 / V4-4 末"待做项登记"和"候选项登记")为准。
