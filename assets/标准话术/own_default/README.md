# own_default · 标准话术目录

## 这是什么

这是一个**空壳占位目录**,对应 `companies.yaml` 中 `id: own_default` 的占位条目(`status: placeholder`)。

## 首次使用

**不要直接往这个目录放真实话术素材**。请先走"新增公司"流程登记你方实际投标主体,再把该主体沉淀的高质量话术放到对应 `assets/标准话术/<你的 company_id>/` 目录。

新增公司的命令:

```bash
./run_script.bat add_company.py "你公司全称" own --alias "你公司简称"
```

## 话术素材摄入

话术片段(docx / md)放到 `_inbox/` 后,用以下命令登记:

```bash
./run_script.bat ingest_assets.py 话术 <你的 company_id>
```

## 话术索引

该目录已带一个空骨架 `话术索引.md`,保留不动。新增公司后,真实话术索引会写入 `assets/标准话术/<你的 company_id>/话术索引.md`。

## 使用原则

- 话术库提供的是**骨架**,不是成品 — 每次使用前必须本地化改写
- 话术中涉及具体项目名/金额/人员的占位符(如 `[项目名]`、`[XX 万元]`),必须替换为本项目真实数据
- 原样复制粘贴的话术会被 `compliance_check.py` 标为"模板残留"并阻塞终审
- 详见 `SKILL.md` §7.5 "引用标准话术"规则
