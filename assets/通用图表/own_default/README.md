# own_default · 通用图表目录

## 这是什么

这是一个**空壳占位目录**,对应 `companies.yaml` 中 `id: own_default` 的占位条目(`status: placeholder`)。

## 首次使用

**不要直接往这个目录放真实图表(架构图/流程图/甘特图等)**。请先走"新增公司"流程登记你方实际投标主体,再把该主体的图表放到对应 `assets/通用图表/<你的 company_id>/` 目录。

新增公司的命令:

```bash
./run_script.bat add_company.py "你公司全称" own --alias "你公司简称"
```

## 图表素材摄入

图表(PNG / SVG / Visio / docx 嵌入图)放到 `_inbox/` 后,用以下命令登记到索引:

```bash
./run_script.bat ingest_assets.py 图表 <你的 company_id>
```

## 图表索引

该目录已带一个空骨架 `图表索引.md`,保留不动。新增公司后,真实图表索引会写入 `assets/通用图表/<你的 company_id>/图表索引.md`。

## 复用风险提醒

- 架构图/流程图**严禁原样套用到不同项目**(评委一眼能看出"通用 PPT")
- 每次复用前,必须**按本项目业务模块重新调整**图中文本
- 详见 `SKILL.md` §7.4 "引用通用图表"规则
