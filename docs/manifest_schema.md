# manifest.yaml schema(B 模式 Part)

`projects/<项目>/output/b_mode/<part_dir>/manifest.yaml` 是 B 模式 Part 的组装清单,由 `b_mode_extract.py` 产出,被 `b_mode_fill.py` 消费。本文档记录字段约定,V3-1 新增的字段单独标注。

---

## 顶层字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `part_name` | str | 是 | Part 名称(对应 `tender_brief.response_file_parts[i].name`) |
| `production_mode` | str | 是 | 生产模式,B 模式 Part 此值固定为 `B` |
| `source_anchor` | dict | 是 | 招标文件原文锚点(`type` / `start_line` / `end_line` / `evidence`) |
| `assembly_order` | list[dict] | 是 | 组装清单,逐项处理 |
| `assets_provider` | str | 否 | 见下文 |

### `assets_provider`

控制本 Part 走哪个 AssetsProvider 实现。缺省 `placeholder`。

| 取值 | 说明 |
|---|---|
| `placeholder` | `PlaceholderAssetsProvider`,所有 lookup 返回占位 AssetRef,resolve 产占位 docx(原 v2 默认行为) |
| `curated_local` | **V3-1 新增**:`CuratedLocalAssetsProvider`,扫 `assets/<类别>/<company_id>/` 找真实文件 |

---

## `assembly_order[]` 项字段

每项描述 Part 中的一段内容来源。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `section_id` | str | 否 | 段落序号(如 `(一)`) |
| `section_title` | str | 是 | 段落标题 |
| `asset_type` | str | 是 | 细粒度类型(如 `资质证书` / `财务报告` / `团队简历` / `业绩清单`) |
| `source_type` | str | 是 | `inline_template` / `asset_lookup` / `self_drafted` |
| `source` | str | 否 | 招标文件原文引用(用于追溯) |
| `items` | list | 否 | 该段需要包含的字段清单 |
| `format` | str | 否 | 格式要求(如"扫描件加盖投标人公章") |
| `asset_query` | dict | 否 | 粗粒度查询提示,含 `type`(如"资质" / "简历") + `name`(可选,具体名称) + **`inventory_match`(V4-2a 新增,见下文)** |
| `lookup_priority` | str | 否 | **V3-1 新增**,见下文 |
| `year_filter` | str | 否 | **V3-1 新增**,见下文 |

---

## V3-1 新增字段(`assembly_order[]` 项内)

### `lookup_priority`

控制 `CuratedLocalAssetsProvider` 在多命中场景下,**非交互模式**(stdin 非 tty 或 `non_interactive=True`)的自动选择策略。

| 取值 | 行为 | 实现状态 |
|---|---|---|
| `latest_year_first`(默认) | 按文件名 `YYYYMMDD_` 前缀提取年份,最新优先 | ✅ V3-1 |
| `name_match_first` | 候选 metadata.name 与 `asset_query.name` 完全匹配的优先 | 🟡 V4-2b 结构占位:接口收值,实际 fallback `latest_year_first` 并 emit `[V4-2b 占位]` warning(V4-skel.3 起);实线判据 V4-2b 实现层填 |
| `review_status_first` | curated `.md` 中 `review_status: approved` 的优先 | 🟡 V4-2b 结构占位:接口收值,实际 fallback `latest_year_first` 并 emit `[V4-2b 占位]` warning(V4-skel.3 起);实线判据 V4-2b 实现层填 |

交互模式(stdin 是 tty 且 `non_interactive=False`)下,`lookup_priority` **不消费**——直接让用户 stdin 输入序号选择。

### `year_filter`

字符串形式的年份过滤条件,在 `_scan_candidates` 阶段对候选做过滤。语法:

| 语法 | 含义 | 例 |
|---|---|---|
| `>=YYYY` | 大于等于 | `>=2024` 保留 2024 及之后年份 |
| `<=YYYY` | 小于等于 | `<=2025` 保留 2025 及之前 |
| `YYYY` | 单年 | `2025` 仅保留 2025 |
| `YYYY-YYYY` | 范围(含两端) | `2023-2025` 保留 2023/2024/2025 |

年份从 `_raw/<file>` 文件名前 8 位 `YYYYMMDD_` 提取;无 timestamp 前缀的文件视为无年份,year_filter 启用时被过滤掉。

---

## V4-2a 新增字段(`asset_query.inventory_match`)

`asset_query.inventory_match` 是 AI 在 B 模式 extract 阶段写 intermediate.json 时,从 `assets_inventory.json` 候选清单中选中的真实条目(由 `b_mode_extract.cmd_extract_text` 调 `CuratedLocalAssetsProvider.enumerate_inventory()` 产出 sidecar)。

V4-2a 目的:消除 AI 凭招标文件原文盲写 `asset_query.name` 的行为,使选材落实到库内真实候选(或显式标占位)。

**结构**:

| 子字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `filename` | str | 是 | 从 `assets_inventory.json` 选中条目的 `filename`(含 `YYYYMMDD_` 前缀的原始文件名);占位时为 `"__PENDING_USER__"` |
| `company_id` | str | 是 | 选中条目的 `company_id`(对应 `companies.yaml` 主体 id);占位时为 `"__PENDING_USER__"` |
| `year` | int 或 null | 否 | 选中条目的 `year`(从 `filename` `YYYYMMDD_` 前缀提取,无前缀为 null);占位时省略或填 null |

**占位规则**(R10 红线,复用 V4-4 同源 `__PENDING_USER__` 字面):

- 库内无匹配候选时(空库 / 评分项无相关 asset / `inventory_match` 必须显式标占位):
  - `filename: "__PENDING_USER__"` + `company_id: "__PENDING_USER__"` + `year: null`
  - **不得盲写**不存在的 `name` / `filename`
- V4-2a 只填 `inventory_match`,**不填** `rationale`(为什么选这个),`rationale` 字段留 V4-2b

**示例**(库内真实命中):

```yaml
asset_query:
  type: 资质
  name: 营业执照
  inventory_match:
    filename: 20250101_demo_business_license.docx
    company_id: own_demo
    year: 2025
```

**示例**(库内无匹配,占位):

```yaml
asset_query:
  type: 资质
  name: 营业执照
  inventory_match:
    filename: __PENDING_USER__
    company_id: __PENDING_USER__
    year: null
```

**向后兼容**:`asset_query.inventory_match` 缺省时 `b_mode_fill` / `CuratedLocalAssetsProvider.lookup` 走 V3-1 默认 lookup 路径(按 `type` / `name` / `lookup_priority` / `year_filter` 查),旧 manifest 不需回填。`inventory_match` 当前不被 `b_mode_fill` 消费(只作 R10 占位透传 + V4-2b rationale 写盘的输入)。

---

## V4-2b 结构占位字段(`asset_query.rationale`)

`asset_query.rationale` 是 AI 在 B 模式 extract 阶段写 intermediate.json 时,**为什么选这条 inventory_match**(选材理由)。结构层在 V4-skel.2 加,实现层 V4-2b。

V4-2b 目的:让用户拿到 manifest.yaml 后**不打开源 docx** 就能判 "AI 选得对不对"(V4-2a 只有 inventory_match 选了谁,看不出为什么选)。

**结构** — 单字段 `asset_query.rationale: str`(类型 str,**否**必填 / V4-skel.2 结构层占位):

- AI 选材理由文本
- 未填或值为 `"__PENDING_AI__"` 时 `b_mode_fill` 溯源行追加 `[V4-2b 占位] rationale 未填`
- 不影响 `lookup` / `resolve` 控制流(rationale 不消费,只供用户回查)

**占位规则**(R10 红线,复用 V4-4 / V4-2a 同源 `__PENDING_USER__` / `__PENDING_AI__` 字面):

- 字段缺失 / 值为 `"__PENDING_AI__"` → `b_mode_fill` 溯源行 emit `[V4-2b 占位] rationale 未填 (asset_query.rationale 缺失或 __PENDING_AI__), 实线 V4-2b 实现层补`
- **R10 边界**:不静默放过,WPS 打开 assembled.docx 在溯源行可见 "[V4-2b 占位]" 字面
- 已填(非占位)时 `b_mode_fill` 透传不消费(rationale 不影响 lookup,只供用户回查)

**详略约定**:V4-2b 实现层填 — 详略 / 必含信息项 待真实使用手感后定(`docs/v4_backlog.md §1 V4-2b` 观察点 B)。

**示例**(rationale 已填):

```yaml
asset_query:
  type: 资质
  name: 等保三级安评报告
  inventory_match:
    filename: 20250420_demo_audit_report.docx
    company_id: own_demo
    year: 2025
  rationale: "招标要求等保三级,本条 filename 含 '审计报告' 关键词,2025-04 发布在有效期内 (24个月内),其他候选 (ISO9001/营业执照) 不匹配等保类要求"
```

**示例**(rationale 占位):

```yaml
asset_query:
  type: 资质
  name: 等保三级安评报告
  inventory_match:
    filename: 20250420_demo_audit_report.docx
    company_id: own_demo
    year: 2025
  rationale: __PENDING_AI__
```

**配套 sidecar 产物** `selection_rationale.json` (V4-2b 结构层 schema 定 / AI 写 / 字面提示由 `b_mode_extract.cmd_extract_text` CLI echo):

```json
{
  "candidates_total": <N>,
  "excluded_filenames": ["..."],
  "excluded_reasons": ["..."],
  "selected_filename": "...",
  "reasoning_text": "__PENDING_AI__"
}
```

`selection_rationale.json` 跟 `intermediate.json` 配对(同 part_dir),`reasoning_text` 跟 `asset_query.rationale` 内容同源(rationale 是 manifest 内 inline / reasoning_text 是 sidecar 详细版)。**结构层只定 schema,内容是 AI 写的 V4-2b 实现层产出**。

---

## 向后兼容

- `lookup_priority` / `year_filter` 缺省时 `CuratedLocalAssetsProvider` 走默认行为(latest_year_first + 不过滤),旧 manifest 不需回填。
- `assets_provider` 缺省时 `b_mode_fill.py` 走 `placeholder`,行为与 v2 默认一致。

---

## 示例(V3-1 完整字段)

```yaml
part_name: 其他资格证明文件
production_mode: B
assets_provider: curated_local
source_anchor:
  type: text
  start_line: 91
  end_line: 93
  evidence: L91 (三)其他资格证明文件
assembly_order:
- section_id: (一)
  section_title: 营业执照
  asset_type: 营业执照
  source_type: asset_lookup
  source: 申请人资格要求 3:营业执照
  items:
  - 营业执照扫描件(统一社会信用代码)
  format: 扫描件加盖投标人公章
  asset_query:
    type: 资质
    name: 营业执照
    inventory_match:
      filename: 20250101_demo_business_license.docx
      company_id: own_demo
      year: 2025
  lookup_priority: latest_year_first
  year_filter: ">=2024"
```
