# tender-writer V3 规划

本文档是 V3 开发期的路线图 + 进度看板。每完成一项,回来更新该项状态(待开始 → 进行中 → 已完成)。本文档自身在 V3 启动元提交里建立,V3 任何代码改动都不应早于本文档的 commit。

## V3 定位

v2 是"工具链可用,B 模式占位实现"的版本。V3 的核心命题:让 v2 的所有口径诚实,补齐 B 模式真实材料组装能力,把测试覆盖率从 1 提到 ≥10,确认所有"未来工作"标注的 TODO 兑现。

V3 不是新功能版本,是完成度版本。

## 与 v2.0.x 的关系

v2.0.0 / v2.0.1 已封板,v2.0.x 不再打补丁。所有 v2.0.x 期间登记但未做的内容(docs/v2_roadmap.md 候选 1/2/3 + 已知噪音警告)迁入本文档,作为 V3 任务项。docs/v2_roadmap.md 收尾,只保留指向本文档的指针。

## 任务清单(按优先级)

### V3-1 · B 模式 CuratedLocalAssetsProvider 真实实现

**状态**:已完成

**优先级**:🔴 必做(否则 B 模式名不副实)

**现状**:scripts/assets_provider.py 当前只有 PlaceholderAssetsProvider,所有 lookup 返回占位 AssetRef,resolve 产出占位 docx。scripts/b_mode_fill.py 三种 source_type(inline_template / asset_lookup / self_drafted)全部产出占位段落。assets_provider.py 注释里登记 CuratedLocalAssetsProvider 和 MCPExternalAssetsProvider 为未来工作,V3 兑现前者。

**做什么**(详见 plans/v3-1.md,Path A):

- 新增 CuratedLocalAssetsProvider 类,实现 lookup 和 resolve
- 扫现有结构 `assets/<类别>/<company_id>/`(类别 = 公司资质/团队简历/标准话术/类似业绩/通用图表 五类),沿用现有 `_inbox / _raw / curated .md` 三层模型,不引入新目录约定
- 候选优先级:`_raw/<timestamp>_<original>.docx` 主选 → `_raw/<...>.pdf` 走 pdf2docx 转换 → `<resource>.md` 转段落兜底
- 新建 `references/asset_type_mapping.yaml`,把 spec.asset_type / asset_query.type 映射到现有 5 类
- lookup 多命中时停下让用户选(stdin 交互 + 对齐 CLAUDE.md 红线 6;非 tty 报错退出)
- resolve 真实从 docx 复制段落文本(本期不保留格式/图片,留 V4)
- PDF asset 走 pdf2docx 在线转换,失败降级 placeholder + 日志告警
- 在 manifest.yaml 增加 lookup_priority / year_filter 字段(向后兼容,无字段走默认)
- b_mode_fill.py `_handle_asset_lookup` 改造:真实命中时去掉占位文字(`_handle_inline_template` / `_handle_self_drafted` 留 V4)
- 给 demo own_default 摄入最小 fixture asset(2-3 份 demo docx 入 `_raw`,git track),让 demo 重跑能验证 lookup 命中

**完成判定**:

- demo 重跑 part_04 / part_08 后,assembled.docx 中含至少 1 段真实 asset 内容(来自 demo own_default 的 fixture asset),不再全是 PlaceholderAssetsProvider 的"[此处插入 X 材料]"占位
- 多命中场景能交互停下让用户选
- 单元测试覆盖 lookup 边界(0 命中 / 1 命中 / 多命中 / 年份过滤)≥10 case
- manifest.yaml 新字段向后兼容(旧 manifest 不需回填)
- references/asset_type_mapping.yaml 覆盖 demo 用到的所有 asset_type(无"无法映射"告警)

**预估**:8-12 小时(含 asset 映射表 + demo fixture 摄入)

**依赖**:V3-2(测试基础设施已就位 ✓)

### V3-2 · 测试覆盖从 1 → ≥10

**状态**:已完成

**优先级**:🔴 必做

**现状**:scripts/tests/test_budget_parsing.py 是仓库唯一测试,覆盖 1 个边界 case。9901 行代码无测试是 V3 进入生产前的硬阻塞。

**做什么**:

- test_parse_tender.py:5-10 个不同结构的招标文件 fixture,断言 extracted 字段
- test_compliance_check.py:fixture docx 测漏答 / 弱覆盖 / 字体安全
- test_check_cross_consistency.py:测 D+N 节点抽取、团队人数过滤、金额一致性
- test_v45_merge.py:测 build_merge_order 在不同 part 配置下的输出
- test_generate_outline.py:测 5 类 project_type 各跑一遍模板
- test_export_deliverables.py:测 build_deliverable_mapping 动态生成

**完成判定**:

- tests/ 下 ≥6 个新测试文件 + budget_parsing 共 ≥7 个,test case 总数 ≥10
- ./run_script.bat tests/run_all.py(新增)能一键跑全部
- 每个核心脚本(parse_tender / compliance_check / check_cross_consistency / v45_merge / generate_outline / export_deliverables)至少有一个 happy path 测试

**预估**:8-12 小时(主要时间在准备 fixture)

**依赖**:无(V3 第一项做)

### V3-3 · timing hook 精确耗时埋点

**状态**:已完成

**优先级**:🟡 高

**现状**:docs/v2_roadmap.md 候选 3 已登记。当前"X 分钟"是墙钟估算,误差 ±30 分钟。

**做什么**:

- 新增 scripts/_timing_hook.py 上下文管理器
- 各阶段脚本主入口包一层 with stage_timer("parse_tender"):
- 累积写到 output/_timing.json
- 新增 scripts/timing_report.py 生成 markdown 报表

**完成判定**:demo 重跑后 output/_timing.json 包含每阶段耗时,误差 < 1 秒

**预估**:3-4 小时

### V3-4 · 正文级缝合句检测

**状态**:已完成

**优先级**:🟡 高

**现状**:docs/v2_roadmap.md 候选 1。scripts/check_chapter.py L132-139 留有 TODO 注释。

**做什么**:

- 新增 check_content_keyword_stitching(text, matrix_rows) ≈40 行
- 滑窗算法:30 字窗口内出现 ≥4 个评分项关键词 → 缝合句嫌疑
- 标记到 chapter_check_report.md

**完成判定**:用一段已知缝合句的文本(类似 "审核质量控制措施风险管理制度工作程序标准方法")测,被正确标记

**预估**:2-3 小时

### V3-5 · compliance_check --section-only 开关

**状态**:已完成

**优先级**:🟡 顺手做

**现状**:docs/v2_roadmap.md 已知噪音警告第 1 条。对 tender_response.docx 跑会假阳性报封面/目录缺失。

**做什么**:

- 加 --section-only 开关
- 文件名含 tender_response 时自动启用 section_only,跳过封面/目录检查
- 文件名含 final_response 时全项检查

**完成判定**:demo 重跑 compliance_check projects/demo_cadre_training/output/tender_response.docx,不再报"missing 封面 keywords"

**预估**:1 小时

### V3-6 · 扫描版 PDF 自动 OCR

**状态**:已完成 ✅ (2026-04-29)

**优先级**:🟢 中(FAQ Q4 已兜底)

**现状**:parse_tender.py::read_pdf 直接调 pdfplumber.extract_text(),扫描版 PDF 输出空文本,不报错也不提示。

**做什么**:

- read_pdf 检测:text 长度 / 页数 < 阈值(50 字/页)→ 判定扫描版
- 自动调用 ocrmypdf -l chi_sim input.pdf temp_ocr.pdf
- 失败时退到当前 FAQ Q4 文档化的手动流程,清晰报错
- requirements.txt 加 ocrmypdf 注释(不强加依赖,标注"扫描版 PDF 才需要")

**完成判定**:用一份扫描版 PDF fixture 跑 parse_tender,自动 OCR 后产出非空 raw_text

**预估**:3-4 小时(含 tesseract 中文包安装文档)

### V3-7 · Word 直切集成 c_mode_run 自动分流

**状态**:已完成

**优先级**:🟢 中

**现状**:scripts/c_mode_docx_passthrough.py 存在但 c_mode_run 没集成。

**做什么**:c_mode_run.py --all 内部判断 source 类型,docx 走 passthrough,不走 jinja。

**完成判定**:demo 跑 c_mode_run --all,日志区分"模板填充"和"docx 直切"两种路径

**预估**:1-2 小时

### V3-8 · docx 字体安全深度检查

**状态**:已完成 ✅ (2026-04-29)

**优先级**:🟢 中

**现状**:v2 补丁 2 修过 WPS 字体 fallback(MS 明朝 / Courier 缺失),但 compliance_check::check_font_safety 只扫段落 run.font 字段,不查 docx 内嵌的 fontTable.xml。

**做什么**:解压 docx zip → 解析 word/fontTable.xml → 列出所有声明字体 → 对照白名单(宋体/黑体/仿宋/Times New Roman/Arial)

**完成判定**:用一份故意嵌入 MS 明朝字体的 fixture docx 测,被正确标记

**预估**:2-3 小时

### V3-9 · check_cross_consistency 扩充检查项

**状态**:已完成 ✅ (2026-04-30)

**优先级**:🟢 低

**现状**:当前只有 3 项检查(D+N 节点 / 团队成本 / 金额数量级)。README 写"等自相矛盾类错误自动捕获"暗示有更多。

**做什么**:

- 项 4:同字段在不同章节的措辞一致性(如项目名、采购方名)
- 项 5:人名/职称在简历章节和组织架构图之间的一致性
- 项 6:引用编号正确性(章节交叉引用)

**完成判定**:每项有单元测试 + demo 重跑通过

**预估**:4-6 小时

### V3-10 · README + SKILL 阶段口径统一

**状态**:已完成 ✅ (2026-04-30)

**优先级**:🟢 低(累积要做)

**现状**:docs/DESIGN.md 已经改成"主干 5 + 并列(4-B/4-C/6)",但 README L31 / L49 / L67 + SKILL.md description 字段 / L44 标题 还是单口径"五阶段"。

**做什么**:

- README 三处 + SKILL.md description 字段 + SKILL.md L44 标题改为"五阶段主干 + 并列阶段(4-B/4-C/6)"
- SKILL.md description 字段顺手砍 40+ 关键词堆砌的一半,让触发精度提高(参见 V3-12)

**完成判定**:全仓 grep "五阶段" 命中均与"主干 + 并列"语义匹配

**预估**:1 小时

### V3-11 · B 模式 README + SKILL 口径诚实化(V3-1 配套)

**状态**:已完成

**优先级**:🔴 必做

**现状**:README 核心能力第 5 条"非交互批量化:一键跑完所有 C/B 模式 Part,占位红字标记'待填'"措辞像 B 模式产出真实内容、只是未填字段标红。实际 v2 的 B 模式整段是占位。

**做什么**:

- 与 V3-1 同步落地。V3-1 完成后,README 改成"B 模式真实材料组装"
- 措辞从"非交互批量化"改为更精确的"B 模式材料组装:从 assets 库按 asset_type 命名约定查找真实材料,合并到 assembled.docx;无命中时产占位 + .pending_marker"

**完成判定**:与 V3-1 一致

**预估**:1 小时

**依赖**:V3-1

### V3-12 · SKILL.md description 字段精简

**状态**:已完成 ✅ (2026-04-30)

**优先级**:🟢 低

**现状**:SKILL.md description 字段堆 40+ 触发关键词,可能导致 Claude Code 过触发(无关问题也被拉进来)。

**做什么**:

- 把"或提到 X / Y / Z 等关键词时触发"那段砍一半,只留核心 10 个最强相关词
- 在 V3 里观察实际触发体验,后续可继续微调

**完成判定**:SKILL.md description 字段触发关键词 ≤ 10 个,且保留的关键词覆盖招标/投标/技术标/评分/政府采购等核心场景

**预估**:1 小时

**依赖**:V3-10 顺带做更省事

### V3-13 · demo 项目无破坏重跑工具(parse_tender state reset)

**状态**:已完成 ✅ (2026-04-30)

**优先级**:🟢 中

**现状**:V3-3 baseline 跑 parse_tender 时,采用"`--force` 重跑 → `git restore` brief.json/md/raw 三件 tracked 文件"的手动组合恢复 demo 状态。`.reviewed` 没被 parse_tender 删,且 `ensure_reviewed` 只查文件存在不查 hash,所以 parse 后 .reviewed 仍 pass 下游闸门——但这是利用实现细节,方法论不干净。后续 V3-N+ 若需重跑 parse_tender 取真实数据(如 V3-6 OCR 后看耗时变化、性能优化前后 timing 对比),手动组合脆弱:容易漏 restore 某文件,容易污染 demo 状态。

**做什么**:

- 新增 `scripts/demo_reset.py`:一键回到 demo 项目"可干净重跑 parse_tender" 的状态
- 步骤:`git restore projects/demo_cadre_training/output/<tracked files>` + 校验 `.reviewed` 仍存在 + 提示"现可跑 parse_tender --force"
- CLAUDE.md 红线 1 仍生效:脚本不创建 .reviewed,只 restore tracked files
- 文档化:在 SKILL.md 阶段 1 / docs/FAQ.md 提一句"demo 重跑 parse_tender 用 demo_reset.py 而不是手动 git restore"

**完成判定**:

- 跑 `demo_reset.py` 后 `git status projects/demo_cadre_training/output/` 全干净
- 接着跑 `parse_tender --force` + 任意下游脚本(如 build_scoring_matrix),`ensure_reviewed` 闸门 pass
- 单元测试 ≥1 case(demo_reset 恢复后 brief.json hash 与 HEAD 一致)

**预估**:1-2 小时

**依赖**:无

**来源**:V3-3 baseline run 衍生的运维工具债,V3-3 Phase 3 review 由用户登记。

### V3-14 · 开源前最终审计(四层结构)

**状态**:已完成 ✅ (2026-04-30)

**优先级**:🟢 中(V3 收尾时做,push 前必做 a+b+c1-3+d)

**现状**:V3 期间所有 commit 留本地 main,未 push 远程。开源前需做四层审计,机器扫 + 行为验证 + 语义一致性 + 新文件准备。原 V3-14 范围(仅敏感信息扫描)过窄,实际开源前需覆盖代码行为与文档语义一致性等更深层问题。

**做什么**:

V3-14a · 机器可扫(grep / 工具搞定):
- 敏感信息扫描(真实公司名 / 人名 / API key / 内网 IP / 硬件路径)
- 死链接扫描(README/SKILL/docs 里指向的文件 / URL 是否存在)
- TODO / FIXME / XXX 残留扫描
- commit log 里临时调试措辞("wip" / "test commit" 等)
- 文件大小异常扫描(>5MB 单文件人工复核)

V3-14b · 代码行为验证(Claude Code 跑代码确认):
- 每个 V3-N(N=1..13)完成判定重跑一遍,验证至今未回归
- demo_cadre_training 端到端跑通(parse_tender → ... → export_deliverables)
- README 里所有命令示例真实可跑
- docs/manifest_schema.md 和 b_mode_extract.py 实际产出 schema diff
- SKILL.md 里所有"举例如:..."的例子真实可复现

V3-14c · 语义一致性(审核位分批审):
- 批次 1:README.md + SKILL.md + DESIGN.md 三文件互相口径对得上
- 批次 2:所有 plans/v3-*.md + v3_planning.md 承诺与完成判定对得上
- 批次 3:docs/FAQ.md + docs/manifest_schema.md + docs/ 其他文件内部交叉引用
- 批次 4(push 后做):所有 commit message 整体审
- 批次 5(push 后做):scripts/ 顶部 docstring 整体审

V3-14d · 开源所需新文件:
- LICENSE(license 选型用户决策)
- CONTRIBUTING.md(开源协作约定)
- README 顶部加 badge / 系统依赖说明 / 快速开始 / 项目状态

**完成判定**:

push 前必过:
- V3-14a 全跑,敏感 grep 报告 0 命中(或人工确认每个命中是误报)
- V3-14b 全跑,demo 端到端 0 报错,所有 V3-N 完成判定 PASS
- V3-14c 批次 1-3 审完,所有不一致已修
- V3-14d LICENSE / CONTRIBUTING.md / README 升级就位

push 后可做:
- V3-14c 批次 4-5 polish

**预估**:5-8 小时(原 2-3h 估算偏低,四层拆分后实际负担)

**依赖**:V3-1 至 V3-13 全部完成 ✓

**来源**:V3-6 路径讨论时由用户登记,V3-13 完成后用户提出"代码与文档一致性等深层审计"扩展为四层结构。

## 不做项(显式记录)

- MCPExternalAssetsProvider:assets_provider.py 注释登记的另一个未来工作。需要外部材料库 + MCP 协议对接,V3 不做,留 V4
- changelog 补 v2.0.1 条目:用户确认不做(自用项目,git log 够)
- GitHub About 字段改口径:用户确认不做
- README Python badge 3.11→3.10:实际 3.11+ 也能跑,标 3.11 不是错

## 开发节奏

- 一次只做一个 V3-N 项,不并行
- 每完成一项,在本文档把状态从"进行中"改为"已完成",commit message 用 feat(v3-N) / test(v3-N) / fix(v3-N) / refactor(v3-N) / docs(v3-N) 格式
- 本地 commit 累积,中间不 push 远程
- 全部 14 项完成 + 自检全过后,一次 push + 打 v3.0.0 tag,届时 README / SKILL / changelog 一并对外更新
- V3 不打中间小版本(v3.0.0-rc1 / v3.0.0-rc2 之类),封板就 v3.0.0

### 审核节奏(Plan-Execute-Review 三阶段协议)

V3 期间每个 V3-N 项分三阶段,审核位介入两次(Plan 审 + 完工审),中途 Claude Code 自主执行不贴审。

**Phase 1: Plan(强制审核点 1)**

- Claude Code 进入 Plan Mode,产出 V3-N 完整执行计划写到 plans/v3-N.md
- 计划内容必须包含:
  - 子任务拆分(fixture 准备 / 测试代码 / 工具脚本等)
  - commit 序列(每个 commit 的 message 和动到的文件)
  - 关键设计决策(fixture 边界、断言策略、依赖处理)
  - 自检方式(怎么验证完成判定每一条)
- 审核位审计划,通过后 Claude Code 进 Phase 2

**Phase 2: Execute(无审核,自主执行)**

- Claude Code 按 plans/v3-N.md 在 main 上线性 commit
- 每个 commit 自检通过即进下一个,不贴审
- 计划内的 commit 不需要等审核
- 中途必须停下来跟用户确认的情况:
  - 计划外的改动(plans/v3-N.md 没写但发现需要做)
  - 发现源码 bug(走 V3-13 登记 + xfail 流程)
  - 子任务执行中发现计划本身需要调整
  - 任何动到非 V3-N 范围内文件的改动

**Phase 3: Review(强制审核点 2)**

- Claude Code 完工后,贴以下内容给审核位:
  - V3-N 期间所有 commit 的 git log(含 message)
  - 整体 diff:git diff <V3-N 起点>..HEAD
  - 自检报告:测试运行结果、文件数、case 数、完成判定逐条对照
- 审核位整体审,通过则 Claude Code 改 V3-N 状态为"已完成"(单独 commit)
- 不通过则定位到具体 commit 单独 revert,修复后重走 Phase 3

V3-N 启动和收尾的强制点:
- 启动:plans/v3-N.md 必须经审核位审过才进 Phase 2
- 收尾:状态改"已完成"的 commit 必须 Phase 3 审过后才执行,不允许 Claude Code 自行标"已完成"

## 推荐开发顺序

按依赖关系和成本递减:

1. V3-2 测试基础设施(无依赖,V3-1 的依赖项,先做)
2. V3-1 B 模式真实实现(依赖 V3-2)
3. V3-11 B 模式口径诚实化(配套 V3-1,做完 V3-1 立即做)
4. V3-5 compliance_check 分流(1 小时小活,顺手做)
5. V3-7 Word 直切集成(1-2 小时小活)
6. V3-3 timing hook(为后续优化提供量化基础)
7. V3-4 正文级缝合句检测
8. V3-8 docx 字体深度检查
9. V3-6 扫描版 PDF 自动 OCR
10. V3-9 check_cross_consistency 扩充
11. V3-10 README + SKILL 阶段口径统一
12. V3-12 SKILL.md description 精简
13. V3-13 demo 重跑工具(V3-3 衍生,后续 V3-N+ 重跑 parse_tender 时方便,优先级中)
14. V3-14 开源前最终审计(V3 收尾,依赖 V3-1 至 V3-13 全部完成)

V3-10 和 V3-12 放最后,因为它们涉及 README/SKILL 文案,V3 全部功能完成后一次性对外发布更整洁。V3-13 是 V3-3 衍生债,不阻塞其他项,做完更顺手。V3-14 是 V3 收尾动作,开源前的最终审计,真正放在最末。

## 与 v2.0.x 的边界

- v2.0.0 是首发,v2.0.1 是文档+小 bug 补丁,两者都不再变更
- V3 在 main 上线性推进(单人项目,不开分支)
- 每个 V3-N commit 独立可 revert,如果某项有问题就单独 revert 该 commit,不动其他项
- 本地 main 在 V3 期间会和 origin/main 渐行渐远,这是预期。用户已确认依靠每版本本地备份,不在远程做 WIP 推送

## 文档更新约定

- 每次 V3-N commit 同时更新本文档对应项的状态字段(待开始 → 进行中 → 已完成)
- 如果开发中发现项的预估或做法需要调整,直接改本文档(不开新文档)
- 全部完成后,本文档保留作为 V3 历史档案,V4 再新建 v4_planning.md
