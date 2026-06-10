# plans/v4-1a-fix-table-size.md — V4-1a 表格字号固化到 master (乙裁定)

## 背景

V4-1a Phase 3 目检发现注入表格字号没体现 "表格小一号" 约定 (现实 11pt = docDefaults 兜底,期望 12pt = 表格约定)。Phase 0 实测根因:"表格 12pt" 约定只活在 `docx_builder.add_table` 的 per-run `set_run_font(size_pt=12)`,未固化到 TableNormal/TableGrid style;V4-1a.9 剥了 run 级 sz 后,注入表格回落 docDefaults 11pt 而非约定 12pt。

Hugin 裁定乙:显式扩 scope 改 master(之前 V4-1a 钉死不动 master),把约定彻底固化到 master,让所有表格路径(add_table 生产 / V4-1a 注入 / 用户手贴)字号一致 12pt。

这是 V4-1a 收尾 (主 5 commit + 字体 fix 2 commit + fixture+归化 fix 2 commit 均未 push)。本次作为 V4-1a.10/.11 延续 commit,跟前 9 个一起 push。

## Phase 0 实测发现

**继承链** (干净 Document() + master assembled.docx 一致):
- `TableNormal` basedOn=`<none>` / sz=none / **w:default="1"** (Word 模板默认表格 style,所有表格根)
- `TableGrid` basedOn=`TableNormal` / sz=none (继承 TableNormal)
- → 改 TableNormal 加 sz=24 (12pt),所有 basedOn=TableNormal 的表格 style 自动继承,一处管所有

**`add_table` 调用点** (全仓 grep):
- `scripts/docx_builder.py` 内 `add_table` 定义
- `scripts/append_chapter.py:306` A 模式 markdown 表唯一外部调用
- `c_mode_extract.py:162` + fixture _generator 用的是 `doc.add_table` (python-docx 原生),不受影响

**测试影响**: 只有 test_b_mode_v4_1a.py case_9 check 表格 run-level sz=0;style def 内 sz 不在 document.xml run 级,改 master 加 style sz 后 case_9 仍 PASS。其他 13 测试文件无表格 run-level sz 显式断言。

## 已定裁定 (Phase 1 ack)

- **A 固化点 = TableNormal style** (顶层根,所有 basedOn=TableNormal 的表格 style 自动继承)
- **B 单一事实源 = `DEFAULT_TABLE_SIZE_PT = 12` 常量** (三处派生:TableNormal style sz + add_table per-run + _body_size_to_table_size)
- **C 保留 add_table per-run set** (不收敛,避免改 set_run_font 接口的 ripple;两层均派生自常量,R10 由"单一事实源"消除而非"删除一层"消除;**per-run 调用点加注释说明为何保留这层冗余,让未来看代码的人不把它当 bug 删**)
- **D `_body_size_to_table_size` 改读常量** (保留函数签名向后兼容,内部废弃多档自适应)

## scope 边界 (钉死)

动:
- `scripts/docx_builder.py` (加 `DEFAULT_TABLE_SIZE_PT` 常量 + `apply_default_styles` 内 TableNormal 加 sz + `_body_size_to_table_size` 改读常量 + add_table 内 per-run set_run_font 加 "为何保留" 注释)
- `scripts/tests/test_b_mode_v4_1a.py` (新 case_10 验注入产物 TableNormal style sz=24)
- `docs/changelog.md` (V4-1 entry 补 bullet,字面 Hugin 给)
- `plans/v4-1a-fix-table-size.md` (本 plan 入仓)

不动 (越界即停):
- `set_run_font` 接口/语义 (不加 size_pt=None 支持)
- `b_mode_fill.py` (V4-1a.6/.9 字体fix + 字号归化逻辑不动 — V4-1a.9 剥 sz 后回落 12pt 是天然对齐)
- Heading 1-4 / Normal style (字号不动)
- C-template/C-reference/C-attachment / handbook / 图片 / 公章 / provider

完成判定:6 条 (见自检方式)。

## 子任务 + commit 序列

| # | commit message | 文件 |
|---|---|---|
| 10 | `V4-1a.10 表格字号固化到 master TableNormal style:DEFAULT_TABLE_SIZE_PT 单一事实源` | docx_builder.py |
| 11 | `V4-1a.11 字号固化测试 + changelog 更新:TableNormal sz=24 + 注入产物字号回落 12pt 实测` | test_b_mode_v4_1a.py / docs/changelog.md / plans/v4-1a-fix-table-size.md |

2 commit。V4-1a.10 实现 / V4-1a.11 测试+文档收尾(A1 pattern)。

## 实现指令

### V4-1a.10 — master 固化

`scripts/docx_builder.py`:

1. **新增常量** (在 DEFAULT_STYLES 字典之后):
```python
# V4-1a.10: 表格字号约定单一事实源
# 跟 master TableNormal style sz + add_table per-run set + _body_size_to_table_size
# 三处同步派生,改 size 只改本常量,不留 "两处管字号" R10 隐患。
DEFAULT_TABLE_SIZE_PT = 12  # 正文 14pt → 表格 12pt 小一号约定
```

2. **`apply_default_styles` 加 TableNormal 分支** (DEFAULT_STYLES 循环之后):
```python
# V4-1a.10: TableNormal style 加字号兜底, 让任何表格 (注入/手贴/add_table)
# 字号都从 style 系统兜底到 DEFAULT_TABLE_SIZE_PT。TableNormal 是所有表格
# style 的顶层根 (TableGrid basedOn TableNormal),改它一处所有 basedOn=TableNormal
# 的表格 style 自动继承。
try:
    tn_style = doc.styles["Normal Table"]  # python-docx 内 TableNormal 的 name
    tn_rpr = tn_style.element.get_or_add_rPr()
    for tag in ("w:sz", "w:szCs"):
        existing = tn_rpr.find(qn(tag))
        if existing is not None:
            tn_rpr.remove(existing)
        sz_el = OxmlElement(tag)
        sz_el.set(qn("w:val"), str(DEFAULT_TABLE_SIZE_PT * 2))  # 半 point
        tn_rpr.append(sz_el)
except KeyError:
    pass  # 若 TableNormal 不存在 (异常文档), 静默跳过
```

3. **`_body_size_to_table_size` 改为读常量**:
```python
def _body_size_to_table_size(body_size_pt: float) -> float:
    """V4-1a.10: 改读 DEFAULT_TABLE_SIZE_PT 单一事实源, 不再多档自适应。
    保留函数签名向后兼容历史调用 (add_table size_pt=None fallback)。
    """
    return float(DEFAULT_TABLE_SIZE_PT)
```

4. **`add_table` per-run set_run_font 调用处加注释** (C 裁定):
   - 注释要点:"per-run set 跟 TableNormal style 兜底两层均派生自 DEFAULT_TABLE_SIZE_PT,
     此处保留 per-run set 是为避免改 set_run_font 接口 (size_pt=None 支持) 的 ripple,
     非冗余 bug。改 size 只改 DEFAULT_TABLE_SIZE_PT 一处即可。"
   - 让未来看代码的人不把这层冗余当问题去删。

### V4-1a.11 — 测试 + 文档

test_b_mode_v4_1a.py 加 case_10:
- 注入产物 styles.xml 内 TableNormal style 实测 `<w:sz w:val="24"/>` (= DEFAULT_TABLE_SIZE_PT * 2 = 24 半 point = 12pt)
- (V4-1a.9 case_9 已验 run-level sz=0,无需重复)
- 等价于 "表格字号最终落 12pt" 自动验

测试夹具 `_inject_anchor_to_tmp_doc` 不需改 (已调 `apply_default_styles`,master fix 自动生效)

changelog: V4-1 entry 补 V4-1a.10/.11 bullet — **字面停下等 Hugin 给** (不自编)

plan 入仓 (跟 changelog 同 commit)

## 关键约束 (Phase 2)

- 每 commit 后跑 `run_all.py` + R10 scan,确认前 9 commit 成果不破坏 + R10 基线持平 (2 FP)
- V4-1a.10 后重生成 injected docx 覆盖 `_v4_1a_phase3_injected.docx`,实测 TableNormal sz=24 + run-level sz=0 + 字号最终落 12pt
- V4-1a.11 changelog 字面落盘前停下问 Hugin
- 硬停下:四种合法停下 + master 加 TableNormal sz 不生效 (style 系统 cascade 异常) → 停下报告 + 现有 add_table 测试 (test_compliance_check / test_check_chapter 等) break → 停下报告

## 自检方式 (Phase 3)

1. **master TableNormal 固化生效**:注入产物 styles.xml 内 TableNormal style 实测 `<w:sz w:val="24"/>` + `<w:szCs w:val="24"/>` (12pt 半 point 表达)
2. **单一事实源**:grep `DEFAULT_TABLE_SIZE_PT` 命中 ≥3 处 (常量定义 + apply_default_styles 用 + _body_size_to_table_size 用)
3. **V4-1a 注入路径字号 12pt**:重生成 injected docx, run-level sz=0 (V4-1a.9 剥) + style 兜底 TableNormal sz=24 → 表格字号视觉 12pt (Hugin 目检)
4. **add_table 路径字号 12pt 不回归**:跑 test_compliance_check / test_check_chapter 等走 append_chapter → add_table 路径的测试全 PASS
5. **scope 零越界**:git diff --name-only 仅 4 文件 / set_run_font 接口未改 / b_mode_fill V4-1a.6/.9 逻辑未改 / Heading/Normal 字号未改
6. **不回归**:run_all.py 全 PASS + R10 基线持平 + V4-1a.1-.9 成果 (字体/列宽/rebind/标题黑/段距缩进) 实测仍在
