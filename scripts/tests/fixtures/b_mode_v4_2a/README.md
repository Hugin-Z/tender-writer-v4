# V4-2a B 智能匹配·链路打通 fixture

## R10 来源声明

所有 fixture 由人工构造,字面信息(filename / company_id / 评分项内容)均为占位文本,**不来自训练数据**,不复用真实公司或项目材料。

## 文件清单

| 文件 | 角色 | R10 说明 |
|---|---|---|
| `scoring_matrix_sample.csv` | 评分矩阵样本(4 评分项:2 行归属"其他资格证明文件"+ 2 行归属"技术部分") | 验 scoring_matrix_excerpt 过滤逻辑 |
| `assets_inventory_clean.json` | 库内候选清单样本(5 条 own_demo 候选,4 公司资质 + 1 团队简历) | 跟 V3-1 demo assets/own_demo/ 实测内容对齐 |
| `manifest_good.yaml` | AI 据 inventory 选材后的好 manifest(`inventory_match` 指真实候选) | 验 validator 通过真实命中 |
| `manifest_placeholder.yaml` | 库内无匹配场景(`inventory_match` 三字段标 `__PENDING_USER__`) | 验占位 R10 通过 |
| `manifest_bad_blind.yaml` | **盲写反例**:AI 凭原文编造 `inventory_match.filename`,不在 inventory 内 | 验 validator 抓得到盲写(fail→pass 反映 V4-2a 修好) |

## 测试约定

`test_b_mode_v4_2a.py` 调内嵌 `validate_inventory_match(manifest, inventory)` 函数,**不**触碰真实 `assets/` 或 demo 项目。

## 验证目标

V4-2a 的 R10 红线:**AI 选材必须落实到 inventory 内真实候选,或显式标占位;严禁盲写库外不存在的 filename**。

- 好样本(`manifest_good`)→ validator PASS
- 占位样本(`manifest_placeholder`)→ validator PASS(占位合法)
- 盲写样本(`manifest_bad_blind`)→ validator FAIL(抓到盲写)
