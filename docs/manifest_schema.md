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
| `asset_query` | dict | 否 | 粗粒度查询提示,含 `type`(如"资质" / "简历") + `name`(可选,具体名称) |
| `lookup_priority` | str | 否 | **V3-1 新增**,见下文 |
| `year_filter` | str | 否 | **V3-1 新增**,见下文 |

---

## V3-1 新增字段(`assembly_order[]` 项内)

### `lookup_priority`

控制 `CuratedLocalAssetsProvider` 在多命中场景下,**非交互模式**(stdin 非 tty 或 `non_interactive=True`)的自动选择策略。

| 取值 | 行为 | 实现状态 |
|---|---|---|
| `latest_year_first`(默认) | 按文件名 `YYYYMMDD_` 前缀提取年份,最新优先 | ✅ V3-1 |
| `name_match_first` | 候选 metadata.name 与 `asset_query.name` 完全匹配的优先 | ⏸ V4 占位(本期 fallback 到 latest_year_first) |
| `review_status_first` | curated `.md` 中 `review_status: approved` 的优先 | ⏸ V4 占位(本期 fallback 到 latest_year_first) |

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
  lookup_priority: latest_year_first
  year_filter: ">=2024"
```
