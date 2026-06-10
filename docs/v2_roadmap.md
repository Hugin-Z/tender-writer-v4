# tender-writer v2 路线图(Roadmap)

## ⚠️ v2.0.x 已收尾,候选项迁入 V3

v2.0.0 首发 + v2.0.1 文档/bug 补丁封板,v2.0.x 不再打补丁。本文档登记的候选 1/2/3 + 已知噪音警告全部迁入 docs/v3_planning.md:

- 候选 1 正文级缝合句检测 → V3-4
- 候选 2 Word 直切集成 c_mode_run 自动分流 → V3-7
- 候选 3 scripts/_timing_hook.py 精确耗时埋点 → V3-3
- 已知噪音警告第 1 条(compliance_check 假阳性)→ V3-5

下方原内容保留作为历史档案,不再更新。

> 建立日期:2026-04-22(v2.0.0 发布同日)
> 本文档登记 v2.0.0 封板时尚未完全解决或新发现的改进点,作为 v2.1+ 启动时的候选任务清单。
> **v2.1 未启动。本清单仅作登记,不自动执行。**

---

## 候选 1 · 正文级缝合句检测

**来源**:P5(v1 反馈)/ v2 单元 3 部分解决

**现状**:`check_chapter.py` 的缝合句作弊检测目前只覆盖 `#` 开头的 ATX 标题行(`check_title_keywords` 函数末尾 L148-154 已留 TODO 注释)。正文段落里如果出现 "审核质量控制措施风险管理制度工作程序标准方法" 这种 8 关键词 ≤30 字的缝合句,不会被本检查抓到。

**扩展方案**(TODO 原文):

> 扫所有段落,对 scoring_matrix 第 5 列所有关键词做滑窗统计;但需要考虑列表项、表头的"枚举式堆叠"误判率,阈值需要更保守。

**触发时机建议**:v2.1+ 启动时优先做。因为 v2 的 Top 2 章节协作节奏规则生效后,用户 review 压力点转到"正文内是否真的写得有实义",而非标题层面。正文级缝合句检测是评审专家关心的质量维度。

**改动量预估**:**中等**
- 新增函数 `check_content_keyword_stitching(text, matrix_rows)` 约 40 行
- 误判率实验需要跑现有 7 个 stub + 7 个生产级章节对比
- 引入"段落类型分类"以区分"列表/表头堆叠"和"正文缝合"
- 单元测试 fixture 新建约 10 用例

**相关文件指针**:
- `scripts/check_chapter.py:148-154`(TODO 锚点)
- `scripts/check_chapter.py:check_title_keywords`(借鉴窗口滑动规则)
- `references/ai_output_rules.md` R7(正文级约束尚未写入规则)

---

## 候选 2 · Word 上游直切集成 c_mode_run 自动分流

**来源**:P25(v1 反馈)/ v2 单元 5 部分解决

**现状**:`scripts/c_mode_docx_passthrough.py` 独立脚本已实现:对 source_format=docx 且变量 ≤5 的 Part 直切源 docx 段落 + 字体归一化,mock 项目 fixture 验证通过。但**未集成到 `c_mode_run.py` 自动分流**,用户需手动决定跑哪个脚本。

**扩展方案**:
1. `c_mode_run.py::run_part` 入口增加前置判断:调 `c_mode_docx_passthrough.passthrough_part(... dry_run=True)`,若返回 `status=ok` 则走直切路径,否则走原有 extract+build+fill 链路
2. 保留 `--no-passthrough` 开关供强制走老链路
3. 冒烟测试用一个真实 docx 上游项目(非 mock)验证直切产物字体归一化到位

**触发时机建议**:**下次遇到 docx 上游项目时做**。目前投标文件以 PDF 为主,mock 验证已足够证明路径通;真实 docx 上游项目触发时才值得集成投入。

**改动量预估**:**小**
- `c_mode_run.py::run_part` 分流判断约 15 行
- 一个真实 docx 上游项目的 fixture
- SKILL.md 阶段 4-C 流程说明同步更新(1-2 段)

**相关文件指针**:
- `scripts/c_mode_docx_passthrough.py`(完整直切实现)
- `scripts/c_mode_run.py::run_part`(集成点)
- `projects/v2_docx_mock/`(mock fixture,若未来引入需新建)

---

## 候选 3 · scripts/_timing_hook.py 精确耗时埋点

**来源**:P26(v2 自提出)

**现状**:v2 提速量化(120 分钟 → 1.5 分钟,≈ 80×)基于"子命令级别墙钟估算",误差 ±30 分钟。v1 耗时靠会话回合数反推,不精确。

**扩展方案**:

1. 新增 `scripts/_timing_hook.py`,提供 `@timed("命令名")` 装饰器 + `TimingLog` 类
2. 装饰所有入口:`parse_tender.main` / `build_scoring_matrix.main` / `generate_outline.main` / `append_chapter.main` / `check_chapter.main` / `check_cross_consistency.main` / `compliance_check.main` / `c_mode_run.main` / `b_mode_run.main` / `v45_merge.main` / `export_deliverables.main`
3. 每次脚本退出时追加一行到 `projects/<project>/output/_timing.log`(JSON Lines 格式:`{"ts": ..., "cmd": ..., "elapsed_s": ..., "exit_code": ...}`)
4. 新增 `scripts/timing_report.py`,汇总 `_timing.log` 按阶段分组输出表格(支持 `--since <日期>` 过滤)

**触发时机建议**:**v2.1+ 启动时做**,作为第一批基础设施动作。有了 timing 数据,后续所有性能优化改动(含候选 1/2)都能有量化对比。

**改动量预估**:**中等偏小**
- `scripts/_timing_hook.py` 约 60 行
- 12 个脚本各加 1 行装饰器
- `scripts/timing_report.py` 约 80 行
- 文档更新(SKILL.md 哪里可以用 timing 数据)约 1 段

**相关文件指针**:
- 暂无(新模块,无现有锚点)
- 参考实现:Python `time.perf_counter()` + `contextlib.contextmanager`

---

## 已知噪音警告(不影响产物,容忍即可)

这一节登记 v2.0.0 工具链中已知的非 bug 噪音警告——产物本身没问题,但读合规报告会困惑。v2.1+ 视优先级决定是否改。

### 1. compliance_check 对 `tender_response.docx` 报 missing 封面/目录 keywords

- **根因**:封面(part_01 filled.docx,C 模式)和目录(v45_merge 合并后才有)在整标合并产物 `final_tender_package/final_response.docx` 中才存在;`output/tender_response.docx` 只是技术部分 A 模式片段容器,没有封面/目录。
- **现象**:对 `tender_response.docx` 跑 `compliance_check.py` 会报 `missing 封面 keywords: 投标文件, 投标人` 和 `missing 目录 keywords: 目录` 两条警告。
- **规避**:整标合规检查对 `final_tender_package/final_response.docx` 跑,不对 `output/tender_response.docx` 跑。两条警告在片段上下文不算 bug。
- **v2.1 修复方向**:让 `compliance_check.py` 按文件名自动分流——文件名含 `final_response` 时全项检查,含 `tender_response` 时跳过封面/目录检查项(加 `--section-only` 开关)。
- **相关文件**:`scripts/compliance_check.py::check_format` + `scripts/compliance_check.py::FORMAT_CHECKS`

## 整体记录

| 候选 | 来源 | 状态 | 改动量 | 优先级 |
|---|---|---|---|---|
| 1 正文级缝合句检测 | P5 | TODO 锚点已留 | 中 | 高(质量硬指标) |
| 2 Word 直切集成 | P25 | 独立脚本已在 | 小 | 低(触发即做) |
| 3 精确耗时埋点 | P26 | 新模块 | 中偏小 | 高(量化依据) |

v2.1+ 启动建议顺序:先做候选 3(有量化基础后再优化),再做候选 1(质量硬指标),候选 2 按"遇到 docx 上游项目"触发。

---

## post-v3.0.0 todo (V4 评估)

V3.0.0 push 后(2026-05-08)外部 audit 抓到的 V4 备查项,V3 已封板不动,V4 启动时评估:

- **companies.yaml own_default 占位措辞合规**: 当前 own_default 字段存在 `__PENDING_USER__` 占位字面,违反 CLAUDE.md 红线 4 (内部术语不外泄到用户产物)。V4 改为对外友好的 `【请填写...】` 系列措辞
- **V3-14c 批次 4-5 polish**(原 v3_planning.md V3-14 已登记,push 后做):
  - 批次 4: 整审 V3 期间所有 commit message,看措辞 / 错别字 / 一致性
  - 批次 5: 整审 scripts/ 顶部 module docstring,看是否准确描述当前行为
- **V3-13 demo_reset.py scope 扩展**: 当前 TARGET_PATH 仅 `projects/demo_cadre_training/output/`,不含 `投标交付物/` + `final_tender_package/`。V3-14b 端到端测试后 export_deliverables 副作用产出在 投标交付物/,需手工 git restore 还原。V4 评估扩展 TARGET_PATH 或 demo_reset 增 --extended flag

