# own_default · 公司资质目录

## 这是什么

这是一个**空壳占位目录**,对应 `companies.yaml` 中 `id: own_default` 的占位条目(`status: placeholder`)。

## 首次使用

**不要直接往这个目录放真实素材**。请先走"新增公司"流程登记你方实际投标主体,再把该主体的真实资质证书放到对应 `assets/公司资质/<你的 company_id>/` 目录。

新增公司的命令:

```bash
./run_script.bat add_company.py "你公司全称" own --alias "你公司简称"
```

脚本会:
1. 自动生成 `own_<拼音/简写>` 格式的 company_id
2. 追加到 `companies.yaml`
3. 在 `assets/公司资质/`、`assets/类似业绩/`、`assets/团队简历/`、`assets/通用图表/`、`assets/标准话术/` 下分别初始化 `<新 company_id>/_inbox/`、`<新 company_id>/_raw/` 和索引文件

## 为什么不放在 own_default 下

- `own_default` 是**占位条目**,用于示范目录结构
- 真实素材放在占位下会让"首次使用者"误以为 own_default 是可用主体
- 分 company_id 隔离也便于未来出现第二家 own 主体时不混用

## 资质清单索引

该目录内已经带一个空骨架 `资质清单.md`,它是索引文件,保留不动。新增公司时脚本会创建 `assets/公司资质/<你的 company_id>/资质清单.md`,把真实资质索引写到那边。
