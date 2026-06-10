# knowledge_base · 学习参考材料库

## 这是什么

这是 tender-writer 的**学习参考材料库**。AI 在编制标书的阶段 3(提纲)和阶段 4(正文)时,会扫描这里的内容,**吸收其结构、策略、话术风格**,但**不能照抄具体业绩、资质、人员、金额数据**。

> ⚠️ **务必区分:**
>
> - **`assets/`** = 可直接抄进标书的成品素材(按公司隔离)
> - **`references/knowledge_base/`** = 只能学习风格的参考材料(不进标书正文)
>
> 一句话:**能直接抄进标书的放 assets,只能参考风格的放 knowledge_base**。

## 公司类型约束(硬约束)

knowledge_base 接受三种 `company_type`,但行为差异巨大:

| company_type | 是否允许 | 使用方式 |
|---|---|---|
| **own** | ✅ 允许 | 可以作为结构和话术参考,**但不能整段复制**;具体素材应放到 `assets/` |
| **partner** | ✅ 允许 | 可以作为结构参考,**严禁**复制其未在 `assets/` 中登记的具体素材 |
| **reference** | ✅ 允许(且**只能**进 knowledge_base) | **严禁**任何具体业绩、资质、人员、金额信息进入标书正文 |

> 🔴 **reference 类型的材料只能进 knowledge_base/,严禁进 assets/**。这是 tender-writer 的高压线。

## 子目录

| 子目录 | 用途 |
|---|---|
| [历史标书案例/](历史标书案例/) | 往期投标书全文(中标/未中标皆可),按案例 schema 结构化 |
| [评标专家偏好/](评标专家偏好/) | 不同行业评标专家的关注点、偏好、扣分点 |
| [行业术语对照/](行业术语对照/) | 各行业的标准术语与常见误用 |
| [失败教训/](失败教训/) | 踩过的坑、被废标的原因、复盘记录 |

## frontmatter 必填字段(所有 .md 文件)

knowledge_base 下的每一份 markdown(README 除外)都必须在 frontmatter 中包含以下字段:

```yaml
---
source_company: <公司 id,引用 companies.yaml,如 own_default / partner_xinda / ref_huawei>
company_type: own | partner | reference
review_status: pending | approved
source_file: <原始文件名>
ingest_date: <YYYY-MM-DD>
---
```

历史标书案例的 .md 还需要额外补充:

```yaml
项目类型: <智慧城市 / 数字乡村 / 政务系统 / ...>
预算: <万元>
结果: 中标 | 未中标 | 废标
评分: <技术分/总分,如 85.6/100>
关键成功因素: [<列表>]      # 中标时填
失败原因: [<列表>]          # 未中标或废标时填
```

## 引用规则(给 AI)

撰写阶段 3 提纲与阶段 4 正文之前:

1. **扫描** `历史标书案例/` 下所有案例的 frontmatter(不读正文),按"项目类型 + 预算 + 行业"匹配,挑 1-3 份最相关的**深读**。
2. **吸收** 章节结构、应答策略、话术风格。
3. **严禁**复制任何 `company_type=reference` 案例的具体业绩/资质/人员/金额。
4. **严禁**复制 `company_type=partner` 案例中未在 `assets/` 中登记的素材。
5. `company_type=own` 案例可作为结构和话术参考,**但不能整段复制**。
6. 同时浏览 `评标专家偏好/`、`行业术语对照/`、`失败教训/` 中与当前项目相关的内容。
