# own_default · 类似业绩目录

## 这是什么

这是一个**空壳占位目录**,对应 `companies.yaml` 中 `id: own_default` 的占位条目(`status: placeholder`)。

## 首次使用

**不要直接往这个目录放真实业绩材料(合同扫描件、中标通知书等)**。请先走"新增公司"流程登记你方实际投标主体,再把该主体的真实业绩放到对应 `assets/类似业绩/<你的 company_id>/` 目录。

新增公司的命令:

```bash
./run_script.bat add_company.py "你公司全称" own --alias "你公司简称"
```

脚本会:
1. 自动生成 `own_<拼音/简写>` 格式的 company_id
2. 追加到 `companies.yaml`
3. 在 `assets/类似业绩/<新 company_id>/` 下初始化 `_inbox/`、`_raw/` 和 `业绩列表.csv` 索引

## 业绩素材摄入

业绩材料放到 `_inbox/` 后,用以下命令自动抽取要素并登记到索引:

```bash
./run_script.bat ingest_assets.py 业绩 <你的 company_id>
```

## 业绩列表索引

该目录已带一个空骨架 `业绩列表.csv`,它是索引文件,保留不动。新增公司后,真实业绩索引会写入 `assets/类似业绩/<你的 company_id>/业绩列表.csv`。

## 合规提醒

- **严禁**把 `company_type=reference` 的公司业绩放到 `assets/` 任何目录
- `reference` 公司的业绩材料只能进 `references/knowledge_base/历史标书案例/`,且只能学习风格,不能抄具体数据
- 详见 `CLAUDE.md` 红线与 `references/ai_output_rules.md` R5
