# assets_provider fixtures

测试 CuratedLocalAssetsProvider 用的最小 assets/ 镜像目录。

## R10 来源声明

所有 fixture 由 `_generators/make_test_assets.py` 程序化生成,docx 内容是占位文本("test asset content"),**不来自训练数据**,不复用真实公司材料。

## 目录结构(对齐真实 assets/ 的 `<类别>/<company_id>/` 顺序)

```text
assets_provider/
├── README.md                              (本文件)
├── asset_type_mapping.yaml                (test 用映射,与 references/ 区分)
├── _generators/
│   └── make_test_assets.py                (生成 fixture docx)
├── 公司资质/
│   └── company_a/                          (test company_id)
│       ├── _raw/
│       │   ├── 20240601_iso27001.docx     (year=2024)
│       │   ├── 20250101_iso9001.docx      (year=2025)
│       │   └── 20251015_business_license.docx (year=2025)
│       └── iso9001.md                     (curated 兜底,仅 _raw 全空时使用)
└── 团队简历/
    └── company_a/
        └── _raw/
            └── 20250301_zhang_san.docx    (year=2025)
```

## 生成与重跑

```bash
./run_script.bat tests/fixtures/assets_provider/_generators/make_test_assets.py
```

产物 git track,无需每次跑测重生。

## 测试约定

`test_assets_provider.py` 通过 `assets_root=fixtures/assets_provider/` + `company_id="company_a"` 构造 provider,**不**触碰真实 `assets/` 目录。
