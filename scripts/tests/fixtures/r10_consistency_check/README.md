# r10_consistency_check fixtures

测试 R10 扫描脚本用的迷你仓镜像目录。

## R10 来源声明

所有 fixture 由手工编写, 内容是"自包含的迷你仓"结构, **不来自训练数据**, 不复用真实代码内容。

clean/ 内含合法引用; dirty/ 内含每类违规至少 1 例, 用于断言扫描脚本能抓到。

## 目录结构

```text
r10_consistency_check/
├── README.md                       (本文件)
├── clean/                          (零违规仓镜像)
│   ├── docs/
│   │   └── business_model_v1.md    (含 §8 #N20 锚点)
│   └── scripts/
│       ├── valid_module.py         (定义 VALID_CONST)
│       └── consumer.py             (引 valid_module.VALID_CONST + 真实路径 + 真实锚点)
└── dirty/                          (含已知违规)
    ├── docs/
    │   └── business_model_v1.md    (只含 §8 #N20 锚点)
    └── scripts/
        ├── valid_module.py         (定义 EXISTING_CONST)
        └── bad_refs.py             (引 nonexistent path + deleted const + missing anchor)
```

## 测试约定

`test_r10_consistency_check.py` 跑两套:

- clean fixture → 0 violations 断言
- dirty fixture → 每类违规至少 1 处, 检测到的行号和引用对应 dirty/scripts/bad_refs.py 内已知违规
