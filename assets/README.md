# assets · 可调用成品素材库

## 这是什么

这是 tender-writer 的**可直接抄进标书的成品素材库**。AI 在阶段 4(分章节撰写)时,会从这里挑选素材作为标书正文的原料。

> ⚠️ **务必区分:**
>
> - **`assets/`** = 可直接抄进标书的成品素材(本目录)
> - **`references/knowledge_base/`** = 只能学习风格的参考材料
>
> 一句话:**能直接抄进标书的放 assets,只能参考风格的放 knowledge_base**。

---

## 目录组织(两级:类别 / 公司)

assets 严格按"**类别 / 公司 id**"两级组织。同一类别下,不同公司的素材**完全隔离**,避免跨公司误引用。

```
assets/
├── README.md                ← 本文件
├── .ingest_history.json     ← 摄入去重记录(sha256 → 处理时间)
│
├── 公司资质/
│   ├── README.md
│   ├── 资质schema.md
│   └── <company_id>/        ← 例如 own_default、own_jiao、partner_xinda
│       ├── _inbox/          ← 待摄入的原始 PDF/docx 临时区
│       ├── _raw/            ← 摄入完成后的原文件归档(时间戳前缀)
│       ├── 资质清单.md
│       └── <资质名>.md       ← 摄入流程产生的结构化条目
│
├── 类似业绩/
│   ├── README.md
│   ├── 业绩schema.md
│   └── <company_id>/
│       ├── _inbox/
│       ├── _raw/
│       ├── 业绩列表.csv      ← UTF-8 with BOM,每条业绩追加一行
│       └── <项目简称>.md
│
├── 团队简历/
│   ├── README.md
│   ├── 简历schema.md
│   └── <company_id>/
│       ├── _inbox/
│       ├── _raw/
│       ├── 简历索引.csv      ← UTF-8 with BOM
│       └── <姓名脱敏>.md
│
├── 通用图表/
│   ├── README.md
│   ├── 图表schema.md
│   └── <company_id>/
│       ├── _inbox/
│       ├── _raw/
│       ├── 图表索引.md
│       └── <图表标题>.md
│
└── 标准话术/
    ├── README.md
    ├── 话术schema.md
    └── <company_id>/
        ├── _inbox/
        ├── _raw/
        ├── 话术索引.md
        └── <话术名>.md
```

---

## 公司类型硬约束(高压线)

| company_type | 是否允许进 assets | 撰写标书时的引用规则 |
|---|---|---|
| **own** | ✅ 允许 | 可直接引用进标书 |
| **partner** | ✅ 允许 | 可引用,**但必须在文中或附件中标注来源** |
| **reference** | ❌ **严禁** | 只能进 `references/knowledge_base/`,严禁进 assets |

> 🔴 **任何 reference 类型的素材,无论以什么名义,严禁出现在 assets/ 目录下。** 这是 tender-writer 的高压线。

---

## CSV 索引表头规范(必须 UTF-8 with BOM)

### 业绩列表.csv

```
项目名称|行业|规模万|甲方类型|完成时间|关键技术|验收结果|company_id|company_type|review_status|详情路径
```

### 简历索引.csv

```
姓名|岗位|职称|关键证书|证书有效期|适配项目类型|company_id|company_type|review_status|详情路径
```

> 注意:即使同一公司目录下,每行也要冗余 `company_id` 字段,便于全局查询聚合(例如跨公司筛选所有"高级工程师 + 等保三级"的简历)。

---

## review_status 流程

所有摄入流程产生的 .md 和 CSV 行,**默认 `review_status: pending`**。

| 状态 | 含义 | 是否可被标书引用 |
|---|---|---|
| `pending` | 刚摄入,未经人工核对 | ❌ 不可引用,视为未入库 |
| `approved` | 已经人工 review 通过 | ✅ 可被标书引用 |

> ⚠️ AI 在阶段 4 撰写标书时,**只允许引用 `review_status=approved` 的素材**。`pending` 状态的素材即使存在,也视为不存在。

---

## 摄入流程入口

详见 SKILL.md 第九章(已知分类摄入)和第十章(未知分类 triage)。

简而言之:
- **已知分类**:直接把文件丢到 `assets/<类别>/<公司>/_inbox/`,然后说"处理 xxx inbox"
- **不确定分类**:丢到根目录 `_inbox_unsorted/`,然后说"处理 _inbox_unsorted"
- **新公司**:说"新增公司",AI 会引导你完成注册并自动创建对应目录
