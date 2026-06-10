# plans/v4-structure-completion.md — V4 三待办结构层补全 + 占位喊话地图

## 任务定义

把 V4 剩余三待办(V4-2b / V4-1b / V4-7)做到**结构层** — 字段、接口、调用链、占位接住,**让完整跑一次能全程不断流**;实现层留待完整跑暴露真实问题后再修。

**总原则(Hugin 定的)**: 每个占位必须**自己喊出**"我是占位、实线未做、看某 sidecar"。完整跑铺出一张"哪里真 / 哪里占位"的地图 — **这是结构层交付的核心价值,自检验"喊出来了"不只验"字段加了"**(沿 V4-1a "测试验生效不验存在" 教训)。

## 已定裁定(Phase 1 ack)

1. V4-2b frontmatter:`enumerate_inventory()` 字段加,值 None,**不读 frontmatter**,CLI/sidecar 显式标 "V4-2b 未消费值 None"
2. V4-1b `_extract_inline_images` helper + `<w:drawing>` 剥离 留实现层,结构层不碰(避免 V4-1a 第二季)
3. V4-7 `_post_merge_normalize` noop 是结构层,log enum 字符串 `"noop"` 不用 True/False
4. lookup_priority 非默认档命中 fallback 必须 emit warning,manifest_schema 字面改 "🟡 V4-2b 结构占位",不保持现状
5. C4/C5 不踏 OXML 剥离:**纯只读检测含图段** + **整段跳过(不 deepcopy)** + 插占位段(聚焦"缺证书图、投标前人工放原件",不强调"丢了文字")
6. 占位点清单静态入仓:plan 内 §4.5 + changelog 内引用,**不另立单独文件**

## scope 边界(钉死)

**动**:
- `scripts/assets_provider.py`(C1/C3)
- `scripts/b_mode_extract.py`(C1/C2 CLI echo)
- `scripts/b_mode_fill.py`(C2/C4/C5)
- `scripts/v45_merge.py`(C7/C8)
- `docs/manifest_schema.md`(C2/C3 schema 字面)
- `SKILL.md`(C6/C9 诚实化,Hugin 给字面)
- `README.md`(C6 诚实化,Hugin 给字面)
- `docs/changelog.md`(C10,Hugin 给字面)
- `docs/v4_backlog.md`(C10 §5 同步加一行)
- `scripts/tests/test_v4_skeleton_e2e.py`(C10 e2e + 喊话断言)
- `scripts/tests/fixtures/v4_skeleton/`(C10 含图 fixture 给 V4-1b 占位段验证)
- `plans/v4-structure-completion.md`(本 plan / C10 入仓)
- `final_tender_package/v4_placeholders_map.md`(C10 e2e 产物,运行时生成,**不入仓**)

**不动**(越界即停):
- `<w:drawing>` 子元素剥离 / 重组 → V4-1b 实现层
- media part 复制 / relationship 注册 / rId 重分配 → V4-1b 实现层
- `<w:hdr>` / `<w:ftr>` part 复制 → V4-1b 实现层
- section break 拆分 / 合并 → V4-7 实现层
- cell-level 内段落 iter 含图精化检测 → V4-1b 实现层(粗粒度 `tables_with_potential_images` 计数代替)
- frontmatter 解析 / curated .md 字段映射 → V4-2b 实现层
- rationale 详略约定 → V4-2b 实现层
- V4-1a 字体/字号/rebind 现有 helper(`_rebind_or_strip_refs` / `_apply_explicit_fonts_to_runs` / `_normalize_run_size` / `_apply_table_cell_size_to_runs`)调用顺序
- V4-2a 链路 / inventory_match 现有逻辑
- C-template / C-reference / C-attachment 任何分支
- handbook 仓

完成判定:10 条(见 §5 自检方式)。

## commit 序列

| # | commit message | 文件 |
|---|---|---|
| C1 | `V4-skel.1 V4-2b enumerate_inventory frontmatter 字段占位 + CLI 喊话` | assets_provider.py / b_mode_extract.py |
| C2 | `V4-skel.2 V4-2b asset_query.rationale 结构 + b_mode_fill 占位喊话 + selection_rationale schema` | manifest_schema.md / b_mode_fill.py / b_mode_extract.py |
| C3 | `V4-skel.3 V4-2b lookup_priority 非默认档 fallback emit warning + schema 字面诚实化` | assets_provider.py / manifest_schema.md |
| C4 | `V4-skel.4 V4-1b _handle_asset_lookup 含图段落只读检测 + missing_elements.yaml sidecar` | b_mode_fill.py |
| C5 | `V4-skel.5 V4-1b 含图段落整段跳过 + 可见占位段 (聚焦"缺证书图人工放原件")` | b_mode_fill.py |
| C6 | `V4-skel.6 V4-1b SKILL.md + README 诚实化字面` (Hugin 给字面) | SKILL.md / README.md |
| C7 | `V4-skel.7 V4-7 v45_merge _post_merge_normalize noop helper + 接入点` | v45_merge.py |
| C8 | `V4-skel.8 V4-7 merge_normalize.log sidecar + per-fragment 元数据` | v45_merge.py |
| C9 | `V4-skel.9 V4-7 SKILL.md 阶段 6 诚实化字面` (Hugin 给字面) | SKILL.md |
| C10 | `V4-skel.10 e2e 占位喊话验证测试 + v4_placeholders_map + plan + changelog 总账` (Hugin 给字面) | tests + plans + changelog + v4_backlog.md |

10 commits。三组(V4-2b / V4-1b / V4-7)各 3 commit + C10 收尾。C6/C9/C10 三处停下问 Hugin 字面。

## §1 V4-2b 结构层 (C1-C3)

### C1 · `enumerate_inventory()` 加 frontmatter 字段 + 喊话

`scripts/assets_provider.py::CuratedLocalAssetsProvider.enumerate_inventory()`:
- 每条 inventory dict 加 4 字段:`review_status: None` / `valid_until: None` / `issuer: None` / `applicable_scope: None`(**值留 None,不读 frontmatter**)
- docstring 加 "V4-2b 结构占位"

`scripts/b_mode_extract.cmd_extract_text` CLI echo 扩:
- 每次跑 emit `[V4-2b 占位] assets_inventory.json 含 frontmatter 字段 (review_status/valid_until/issuer/applicable_scope) 全 None, 值 V4-2b 实现层填` 到 stderr

### C2 · `asset_query.rationale` schema + b_mode_fill 喊话 + selection_rationale schema

`docs/manifest_schema.md`:
- `asset_query.rationale: str` 字段定义(V4-2b 结构占位)
- 占位值 `__PENDING_AI__`
- 示例 yaml 含 rationale 字段
- 字面 "V4-2b 实现层填 — 详略 / 必含信息项 待 Hugin 跑真实标手感后定"

`scripts/b_mode_fill.py::_handle_asset_lookup`:
- 读 `spec.get('asset_query', {}).get('rationale')`
- 未填或 `__PENDING_AI__` 时,溯源行后追加 `[V4-2b 占位] rationale 未填 (asset_query.rationale 缺失或 __PENDING_AI__), 实线 V4-2b 实现层补`
- 已填则透传(不影响 lookup/resolve)

`scripts/b_mode_extract.cmd_extract_text` CLI echo 加 selection_rationale.json schema(AI 写,结构定):
```json
{
  "candidates_total": N,
  "excluded_filenames": ["..."],
  "excluded_reasons": ["..."],
  "selected_filename": "...",
  "reasoning_text": "__PENDING_AI__"
}
```

### C3 · `lookup_priority` 非默认档 fallback 喊话

`scripts/assets_provider.py::_sort_by_priority`:
- 接收 `lookup_priority` 时,若非 `latest_year_first`,emit `[V4-2b 占位] lookup_priority='{...}' 是结构占位, 当前 fallback latest_year_first` 到 stderr
- 控制流仍走 latest_year_first

`docs/manifest_schema.md` lookup_priority 表:
- `name_match_first` / `review_status_first` 状态 "⏸ V4 占位" → **"🟡 V4-2b 结构占位:接口收值,实际 fallback latest_year_first 并 emit warning"**

## §2 V4-1b 结构层 (C4-C6)

### C4 · 含图段落只读检测 + missing_elements.yaml(纯只读)

`scripts/b_mode_fill.py` 新增两个**只读** helper:

```python
def _paragraph_has_drawing(p_elem) -> bool:
    """V4-1b 占位: 只读检测段落是否含 <w:drawing> (不修改 element)。"""
    return p_elem.find(f'.//{qn("w:drawing")}') is not None

def _count_drawings_in(p_elem) -> int:
    """V4-1b 占位: 只读统计段落内 <w:drawing> 数 (不修改)。"""
    return len(list(p_elem.iter(qn('w:drawing'))))
```

`_handle_asset_lookup` iter 循环改:
```python
for child in src_body.iterchildren():
    if child.tag == p_tag:
        if not _has_text(child):
            continue  # V3-1 trim
        if _paragraph_has_drawing(child):
            n_drawings = _count_drawings_in(child)
            # C5 helper 插占位段, continue 不 deepcopy
            _insert_image_placeholder_paragraph(doc, n_drawings, resolved_path, dst_sectPr)
            skipped_image_paragraphs.append({'n_drawings': n_drawings})
            continue
    elif child.tag == tbl_tag:
        # 表格 cell 内含图: 结构层粗粒度计数, cell-level 不展开 (留 V4-1b 实现层)
        if any(_paragraph_has_drawing(p) for p in child.iter(p_tag)):
            tables_with_potential_images += 1
        pass  # 表格仍 deepcopy (V4-1a 现有路径), drawing 在 cell 内 (deepcopy 带破引用, V4-1b 实现层修)
    ...
```

写 `output/b_mode/<part>/missing_elements.yaml`:
```yaml
source_asset: assets/公司资质/own_xxx/_raw/20250101_xxx.docx
images:
  total_drawings_skipped: N
  image_paragraphs_skipped: M
tables_with_potential_images: K
headers: <len(src_doc.sections)>  # 粗粒度: section 数代理 header/footer 存在性
footers: <同上>
placeholders_inserted: N
v4_1b_implementation_pending: true
```

stderr emit: `[V4-1b 占位] 注入 <asset>: 跳过 N 处含图段落 / K 个表格可能含图 / S 个 section header/footer, 见 missing_elements.yaml`

**注**: `text_chars` 字段可在 missing_elements.yaml 留(粗粒度信息),但 stderr 喊话 + 占位段措辞**不强调**(Hugin 业务上含图段文字基本是图注,真要文字 AI 自己组织,强调"丢了 M 字"会业务误导)。

### C5 · 含图段落整段跳过 + 可见占位段(R10 最关键,聚焦"缺证书图")

`scripts/b_mode_fill.py` 新 helper:

```python
def _insert_image_placeholder_paragraph(doc, n_drawings, source_path, dst_sectPr):
    """V4-1b 占位: 含图段落整段跳过, 在原位置插显式占位段。

    业务语义: 资质/证书章节内,含图段是证书扫描件 — 投标前由用户人工放入原件
    (V4-4 公章红线同源: 签章/原件是用户法律动作, 工具不代劳)。
    占位段聚焦 "缺证书图, 投标前手放原件", 不强调 "丢了文字"
    (含图段文字基本是图注, 真要文字 AI 自己组织, 强调字数会误导)。

    不操作 <w:drawing> 剥离 / 不操作段落重组 / 不操作 media part —
    踏一步就是 V4-1a 第二季。整段跳过 + 占位段是结构层 R10 红线。
    """
    text = (
        f'[V4-1b 占位:此处缺 {n_drawings} 张证书图(源 {source_path}),'
        f'V4-1b 未自动搬运,投标前请人工放入原件]'
    )
    p = doc.add_paragraph()  # python-docx add_paragraph 自动 insert sectPr 前
    run = p.add_run(text)
    run.italic = True
```

**R10 关键**: WPS 打开产物看到斜体占位段说 "此处缺 N 张证书图,投标前请人工放入原件",Hugin 投标前知道 "这小节证书图没搬进来,投标前我自己放原件" — 业务语义清晰、不误导。

### C6 · SKILL.md 阶段 4-B + README 诚实化字面(Hugin 给)

**字面 Hugin 给,不自编**。核心:
- SKILL.md 阶段 4-B "asset_lookup" 描述加 "V4-1b 占位:含图段落整段跳过,assembled.docx 内插可见占位段 + 产 missing_elements.yaml,投标前用户人工放原件"
- README L56 V3 诚实化字面同步更新

## §3 V4-7 结构层 (C7-C9)

### C7 · `_post_merge_normalize()` noop helper + 接入点

`scripts/v45_merge.py` 新 helper:

```python
def _post_merge_normalize(final_doc, fragments_info: list[dict]) -> dict:
    """V4-7 结构占位: cross-doc 合并协调 hook, 当前 noop。
    
    实线 V4-7 实现层补: 字体协调 / 表格列宽统一 / section break 收敛 / 页码 reset。
    return 字典所有维度均为 "noop" 字符串 (不用 True/False, 防 R10 假"已协调")。
    """
    result = {
        'fragments_count': len(fragments_info),
        'font_normalize': 'noop',
        'table_width_unify': 'noop',
        'section_break': 'noop',
        'page_number_reset': 'noop',
    }
    print(f"[V4-7 占位] post_merge_normalize: {result}", file=sys.stderr)
    return result
```

接入点: `composer.append` 全跑完后、`composer.save(final_response_path)` 之前。fragments_info 收集 per-fragment 元数据 (part_name / kind / src_path)。

### C8 · `merge_normalize.log` sidecar 写盘

`final_tender_package/merge_normalize.log`(新 sidecar):
- 内容 = C7 helper return 的 result dict + per-fragment 元数据
- enum 值 `"noop"` 字符串
- 文件头加:
  ```
  # V4-7 结构占位 merge_normalize.log
  # 当前所有协调维度均为 "noop", 实线 V4-7 实现层
  # fragments 数: N
  ```

### C9 · SKILL.md 阶段 6 诚实化字面(Hugin 给)

**字面 Hugin 给**。核心:
- SKILL.md 阶段 6 加 "V4-7 占位:cross-doc 字体 / 列宽 / section / 页码协调当前 **noop**, 见 merge_normalize.log"

## §4 收尾 (C10)

### C10 · e2e 测试 + v4_placeholders_map + plan + changelog

`scripts/tests/test_v4_skeleton_e2e.py`(新):
- 跑 demo_cadre_training 完整链 (b_mode_run --all → v45_merge → export_deliverables) 不断流
- 断言 4 处占位喊话出现:
  - V4-2b 占位 stderr 行(rationale / frontmatter / lookup_priority 各至少 1 次,fixture 显式设非默认 priority)
  - V4-1b 占位 stderr 行(跳过元素)
  - V4-1b assembled.docx 内可见占位段(含图 fixture 验)
  - V4-7 占位 stderr 行 + merge_normalize.log 内 `"noop"` 字面

`scripts/tests/fixtures/v4_skeleton/`(新含图 fixture):
- 1 个真实含 `<w:drawing>` 的 docx(可用 python-docx + `add_picture` 程序生成,无需真实证书图)
- 用作 V4-1b 占位段验证

`final_tender_package/v4_placeholders_map.md`(运行时产,**不入仓**):
- e2e 跑完后产物,覆盖 V4-2b/V4-1b/V4-7 全部占位生效点
- schema:`{V4-2b: {rationale: N 处 / frontmatter: N 字段 / lookup_priority: N 档}, V4-1b: {images: N / headers: N / footers: N}, V4-7: {fonts: noop / tables: noop / sections: noop / page_numbers: noop}}`

`docs/changelog.md` V4-skel 总账 entry(字面 Hugin 给) — 含 "占位点清单见 plans/v4-structure-completion.md §4.5"

`docs/v4_backlog.md` §5 加 "V4-skel 结构层(V4-1b/V4-2b/V4-7 接住占位喊话)"

`plans/v4-structure-completion.md`(本 plan)入仓

## §4.5 静态占位点清单(C10 落地后静态可见)

**V4-2b 占位**(3 类 / 6 处生效点):
- `enumerate_inventory()` 每条 inventory 含 4 个 frontmatter 字段值为 `None`(review_status / valid_until / issuer / applicable_scope),CLI emit "未消费值 None"
- `asset_query.rationale` 字段定义,未填走 `__PENDING_AI__`,b_mode_fill 溯源行 emit "rationale 未填"
- `lookup_priority` 非默认档(`name_match_first` / `review_status_first`)命中时 emit "结构占位 fallback latest_year_first",manifest_schema "🟡 V4-2b 结构占位"

**V4-1b 占位**(3 类 / 4 处生效点):
- 含图段落整段跳过(不 deepcopy),WPS 内可见占位段 `[V4-1b 占位:此处缺 N 张证书图(源...),投标前请人工放入原件]`
- 表格内含图:`missing_elements.yaml` 内 `tables_with_potential_images` 粗粒度计数(cell-level 不展开)
- 页眉页脚不搬:`missing_elements.yaml` 内 `headers` / `footers` 数(通过 `len(src_doc.sections)` 算)
- 缺失元素总账:`missing_elements.yaml` 含 `v4_1b_implementation_pending: true` 显式标

**V4-7 占位**(1 类 / 4 处生效点 / 全 noop):
- `_post_merge_normalize(final_doc)` helper noop,返 4 维度全 `"noop"` 字符串
- `merge_normalize.log` 写 4 维度全 `"noop"` + per-fragment 元数据
- v45_merge 主循环 stderr emit `[V4-7 占位] post_merge_normalize: {...}`
- SKILL.md 阶段 6 字面诚实化 "cross-doc 协调当前 noop"

**怎么从仓里静态看到**(不用跑):
1. 本 plan §4.5(grep "结构占位" / "V4-1b 占位" / "V4-2b 占位" / "V4-7 占位")
2. `docs/changelog.md` V4-skel 总账 entry 含 "占位点清单见 plans/v4-structure-completion.md §4.5"
3. `docs/v4_backlog.md` §5 加一行 "V4-skel 结构层" + 指向本 plan
4. 跑出来的运行时地图:`final_tender_package/v4_placeholders_map.md`(不入仓)

## §5 自检方式 (Phase 3 完成判定 / 重点验"喊出来了")

1. **V4-2b enumerate_inventory frontmatter 字段** — `assets_inventory.json` 每条 inventory 含 4 字段且值 `None` + CLI stderr 含 "V4-2b 占位 / 未消费值 None" 字面(**验喊话生效**)

2. **V4-2b rationale** — `manifest.yaml` 内 asset_query.rationale 字段定义存在 + 未填时 b_mode_fill 控制台输出 `[V4-2b 占位] rationale 未填`(**验喊话**)+ `manifest_schema.md` 含 `__PENDING_AI__` 占位字面

3. **V4-2b lookup_priority fallback** — fixture 显式设 `lookup_priority=review_status_first`,跑 b_mode_fill stderr 含 `[V4-2b 占位] lookup_priority='review_status_first' 是结构占位 fallback latest_year_first`(**验非默认档命中时喊话**,默认档不喊不算 bug)

4. **V4-1b 跳过元素监测** — `missing_elements.yaml` 文件产出 + schema 字段齐 + 含图 fixture 跑过后 yaml 内 `images.total_drawings_skipped > 0`(**验生效**)

5. **V4-1b 可见占位段(R10 最关键)** — 含图 fixture 跑过后 assembled.docx 内含 `[V4-1b 占位:此处缺 N 张证书图...]` 字面(**必须验生效不只验代码**,沿 V4-1a "测试验生效不验存在" 教训)

6. **V4-7 noop log** — `merge_normalize.log` 产出 + 内容含 `"noop"` 字符串(4 维度全 noop)+ stderr 含 `[V4-7 占位] post_merge_normalize` 字面

7. **完整跑不断流** — `test_v4_skeleton_e2e.py` 跑 demo 完整链(b_mode_run --all → v45_merge → export_deliverables)全 PASS,无 raise / 无 exit-1(**结构层目标就是不断流,断流是结构层 bug**)

8. **`v4_placeholders_map.md` 一张地图** — e2e 跑完后 `final_tender_package/v4_placeholders_map.md` 产出,覆盖 V4-2b/V4-1b/V4-7 全部占位生效点

9. **V4-1a/2a 现有产物不回归** — V4-1a 13 commit 成果 + V4-2a 链路实测全 PASS + run_all.py 全 PASS + R10 基线持平 (2 FP)

10. **scope 零越界** — git diff --name-only 仅 plan §scope 动文件清单 / `<w:drawing>` 剥离 + media part + header/footer + section 拆分 / cell-level 含图精化 / frontmatter 解析 / V4-1a 字体字号 helper 调用顺序 / V4-2a 链路 / 其他 sub_mode 0 改

## 关键约束 (Phase 2)

- **每 commit 后跑 run_all.py + R10 scan**,确认前 V4-1a/2a/3/4 成果不破坏 + 基线持平(2 FP)
- **C6/C9/C10 字面落盘前停下问 Hugin**(3 个停下点)
- 硬停下:
  - 四种合法停下情形
  - C4/C5 改 `_handle_asset_lookup` 误触 V4-1a 现有 helper 调用顺序 → 停下
  - C7 接入点放错位置(e.g. 放 composer.save 之后,改不到 final_doc)→ 停下
  - C10 e2e 测试发现完整跑断流(某占位喊话没出,或喊话出了但产物缺)→ 停下报告 — **结构层目标就是不断流,断流是结构层 bug**
- 占位段措辞业务对齐:**聚焦"缺证书图、投标前人工放原件"**,不强调"丢了文字"(Hugin 业务现实)
