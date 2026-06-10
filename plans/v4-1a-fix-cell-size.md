# plans/v4-1a-fix-cell-size.md — V4-1a 表格 cell 字号 per-run 真修 (V4-1a.10 回滚 + per-run set)

## 背景

V4-1a Phase 3 Hugin 目检发现 WPS 显示注入表格 cell 文字 14pt 而非约定 12pt。Phase 0 实测根因:

- 注入表格 cell 段落 OXML 无 pStyle → 隐式 Normal → master Normal sz=28 (14pt) 生效
- V4-1a.10 加的 TableNormal sz=24 (12pt) **优先级低于 paragraph-level Normal,被覆盖**,对 cell 文字无效
- V4-1a.10 的 "TableNormal 兜底" 是 OXML 继承层级走错;DEFAULT_TABLE_SIZE_PT 单一常量本身没错,但被设到了不生效的位置
- add_table 表格 12pt 实际靠 **per-run set sz=24** 生效 (run-level 优先级最高),不靠 TableNormal style

**OOXML 字号继承优先级** (高 → 低):
1. Run 直接 rPr.sz (最高)
2. Character style
3. Paragraph style (Normal sz=28) ← 在此命中,覆盖下层
4. Numbering style
5. ~~Table style (TableNormal sz=24)~~ ← 被覆盖,对 cell 文字无效
6. Document defaults

**修法**: V4-1a.10 TableNormal sz=24 是死代码 (实测无效),删之;按 add_table 同款,给注入 cell 内 run **per-run set sz=24** (run-level rPr.sz 优先级最高,XML 有则 WPS 必取,不赌继承链)。

这是 V4-1a 收尾期发现 V4-1a.10 设计走错 OXML 继承层级后插入的修正 commit,跟前 11 个一起 push。

## 已定裁定 (Phase 1 ack)

1. **删 TableNormal sz=24** (V4-1a.10 加的死代码) — `apply_default_styles` 内回滚 TableNormal 分支
2. **保留 DEFAULT_TABLE_SIZE_PT 常量** — 真单一事实源,被 add_table per-run + 即将加的 cell per-run 两条真实路径派生
3. **per-run set 给注入 cell 内 run** (run-level rPr 优先级最高)
4. **诚实化**: changelog 追溯 V4-1a.10 走错 + 改 per-run 真修;V4-1a.10 plan 历史不动 (沿 V4-3 风险 3)

## scope 边界 (钉死)

动:
- `scripts/docx_builder.py` (回滚 `apply_default_styles` 内 TableNormal sz 分支;保留 `DEFAULT_TABLE_SIZE_PT` 常量;V4-1a.10 设计注释顺手诚实化)
- `scripts/b_mode_fill.py` (新增 helper `_apply_table_cell_size_to_runs` + 在 `_handle_asset_lookup` 集成调用 + 日志加 `cell_size_set` 统计)
- `scripts/tests/test_b_mode_v4_1a.py` (改写 case_10 从"验 TableNormal sz=24 存在"→"验注入 cell run sz=24 生效";case_9 同步改为"验**表外** sz=0";测试夹具加 `_apply_table_cell_size_to_runs` 跟生产同序)
- `docs/changelog.md` (V4-1 entry 加 V4-1a.12/.13 bullet 追溯诚实化,字面 Hugin 给)
- `plans/v4-1a-fix-cell-size.md` (本 plan 入仓)

不动 (越界即停):
- `DEFAULT_TABLE_SIZE_PT` 常量值 (仍 12)
- `add_table` per-run 走 `_body_size_to_table_size` 路径
- `_body_size_to_table_size` (V4-1a.10 已对)
- `set_run_font` 接口
- `b_mode_fill.py` V4-1a.6/.9 字体 fix + 字号归化逻辑
- Heading 1-4 / Normal style 字号
- `plans/v4-1a-fix-table-size.md` (V4-1a.10/.11 历史 plan,沿 V4-3 风险 3 不动)
- 其他 sub_mode / handbook / 图片 / 公章 / provider

## 设计要点

### V4-1a.12 实现 (代码)

**A. 回滚 master `apply_default_styles` 内 TableNormal 分支**:
- 删 V4-1a.10 加的整段 (TableNormal sz=24 + szCs=24 set)
- 理由: 实测无效 (被 Normal 覆盖),死代码先删
- `DEFAULT_TABLE_SIZE_PT` 常量保留 (真两条路径派生)
- 常量 docstring 诚实化 + apply_default_styles docstring 加历史备注 (说明 TableNormal sz 删因 + 替代方案)

**B. `b_mode_fill.py` 新 helper `_apply_table_cell_size_to_runs(elem) -> int`**:
- 遍历 element 内 `<w:tbl>` 范围下所有 `<w:r>`,给 rPr 显式 set `<w:sz w:val="24"/>` + `<w:szCs w:val="24"/>` (从 `DEFAULT_TABLE_SIZE_PT` 派生)
- **仅在 cell run 内 set**,不动表外段落 run (表外字号继续走 V4-1a.9 剥后回落 Normal 14pt)
- **set 等价 add** (前空): V4-1a.9 已剥 cell run sz+szCs 两者,这里 set 实际是从空到 12pt;即使将来 V4-1a.9 改成只剥 sz 不剥 szCs,这里覆盖式 set 也正确 (字号约定就是要统一 12pt,不容源端 szCs 残留)
- 跟 V4-1a.6 字体 fix 同型 (run-level 显式 set 不赌继承)
- 延迟 import DEFAULT_TABLE_SIZE_PT 跟 _main_body 内 apply_default_styles 调用同型
- 返回 set 的 attribute count (供日志/测试统计)

**C. `_handle_asset_lookup` 集成顺序**:
```
deepcopy → rebind → 补字体 (V4-1a.6) → 归化字号 (V4-1a.9 剥 sz) → 表格 cell sz set (V4-1a.12 显式 12pt)
```

**D. 日志加 `cell_size_set` 统计** (跟 rebind/strip/font_apply/size_strip 同型并列输出)

### V4-1a.13 测试 + 诚实化

**测试 case_10 改写** (不新增 case,改写已有 case_10):
- **从** "验 TableNormal style 内 sz=24 写进去" (验存在)
- **改为** 两段断言:
  - (a) 注入表格每个 cell run rPr 含 `<w:sz w:val="24"/>` + `<w:szCs w:val="24"/>` (验生效层,run-level rPr.sz 优先级最高 → WPS 必取)
  - (b) master TableNormal style 内无 sz (验 V4-1a.10 死代码回滚生效)
- 这次断言验**生效层** (XML 有则 WPS 必取,等价"视觉 12pt")

**case_9 同步调整** (V4-1a.12 影响):
- V4-1a.12 后表内 cell run 含 sz=24,case_9 原 "全文 sz=0" 断言被破坏
- 改为 "**表外** sz=0" — 这才是 V4-1a.9 真语义 (归化只对表外段落生效,表内 cell 走 V4-1a.12 路径)
- 用 `re.sub(r'<w:tbl>.*?</w:tbl>', '', doc_xml, flags=re.DOTALL)` 抠掉表格内容后扫剩余 sz

**测试夹具 `_inject_anchor_to_tmp_doc` 加 `_apply_table_cell_size_to_runs` 调用** (跟生产同序,沿 V4-1a.8 fixture 对齐生产 pattern)

**保持自检 case 总数 = 10** (case_10 改写,不增 case_11)

**changelog**: V4-1 entry 加 V4-1a.12/.13 bullet 追溯诚实化:
- V4-1a.10 TableNormal sz=24 经实测对 cell 文字无效 (OXML 继承优先级:段落 style Normal sz=28 压过表格 style TableNormal sz=24)
- 已删 TableNormal sz=24 (死代码);改 per-run set 给 cell 内 run 真修 (跟 add_table 同款,run-level 优先级最高,XML 有则 WPS 必取)
- DEFAULT_TABLE_SIZE_PT 常量保留 (真单一事实源)
- 字面 Hugin 给,不自编

## commit 序列

| # | commit message | 文件 |
|---|---|---|
| 12 | `V4-1a.12 表格 cell 字号 per-run 真修:回滚 V4-1a.10 死代码 + cell run 显式 set sz=24` | docx_builder.py / b_mode_fill.py |
| 13 | `V4-1a.13 cell sz 测试 + changelog 诚实化:case_10 改验生效层 + V4-1a.10 走错 OXML 层级追溯` | test_b_mode_v4_1a.py / docs/changelog.md / plans/v4-1a-fix-cell-size.md |

2 commit (A1 pattern, .12 实现 / .13 测试+文档)。

## 关键约束 (Phase 2)

- 每 commit 后跑 `run_all.py` + R10 scan,确认前 11 commit 成果不破坏 + R10 基线持平 (2 FP)
- V4-1a.12 后重生成 injected docx 覆盖 `_v4_1a_phase3_injected.docx`,实测 cell run sz=24 全到位 + TableNormal style 无 sz (回滚验证) + V4-1a.1-.9 成果全留 (字体/列宽/标题黑/段距/缩进/表外 14pt)
- V4-1a.12 commit 后 case_10 暂时 fail (V4-1a.10 验存在的断言被推翻),V4-1a.13 改写后修;commit message 内 disclosure
- V4-1a.13 changelog 字面落盘前停下问 Hugin
- 硬停下:
  - 四种合法停下情形
  - 新 helper 误触表外段落 run (lxml 选择器写错,只该在 `<w:tbl>` 内 set,误延伸到外面) → 停下
  - 回滚 TableNormal sz 后破坏 add_table 测试 (理论不会,add_table 不靠 TableNormal style,但守正) → 停下

## 自检方式 (Phase 3)

1. **V4-1a.10 死代码回滚**: `apply_default_styles` 后 TableNormal style 实测无 `<w:sz>` + grep `apply_default_styles` 内不含 "Normal Table" 字面
2. **cell run per-run set 生效** (V4-1a.12 招牌目标 / 验生效不验存在): 注入产物每个表格 cell `<w:r>` 内 `<w:rPr>` 直接含 `<w:sz w:val="24"/>` + `<w:szCs w:val="24"/>`,逐 run 对照
3. **表外段落不被误触**: 表外 `<w:p>` (非 cell 内) 的 run 无 `<w:sz>` (V4-1a.9 仍剥 + V4-1a.12 不动),回落 Normal 14pt
4. **add_table 路径不回归**: run_all.py 含 test_check_chapter / test_compliance_check (走 append_chapter→add_table) 全 PASS;add_table 产物表格 cell run sz=24 (per-run set,DEFAULT_TABLE_SIZE_PT 派生)
5. **scope 零越界**: git diff --name-only 仅 5 文件 / DEFAULT_TABLE_SIZE_PT 常量值未改 / set_run_font 接口未改 / V4-1a.6/.9 字体+归化逻辑未改 / Normal style 字号未改
6. **不回归 + V4-1a.1-.11 成果实测仍在**: run_all.py 全 PASS + R10 基线持平 + 列宽/rebind/字体/标题黑/段距/缩进/表外 14pt 全实测
