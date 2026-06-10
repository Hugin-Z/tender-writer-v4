# -*- coding: utf-8 -*-
"""legitimate_lookalikes · 看起来像违规但其实合法的样本.

v2 (V4-0.2 commit 6b): 验扫描器不误抓元变量占位 / 跨仓引用 / 合法 glob.
clean fixture 整体断言 0 violations, 任何把下列引用误抓的退化都会让 clean 测试失败.

误报率盲区分类 (基于 V4-0 V4-0.2 教训):
  1. 元变量占位 - 通配符 / 大写字母占位 / 已知占位词
  2. 跨仓引用 - 顶层目录不在仓内
  3. 合法自指 - 本文件自指 (本 fixture 不演示, clean/consumer.py 已演示)
"""

# ── 1. 元变量占位 ──
# glob 通配 (plans/v3-*.md 形态): 路径含 *
_HISTORICAL_PLANS = "plans/v3-*.md"

# 大写字母占位 (plans/v4-N.md 形态): -N 是单大写字母占位
_PLAN_TEMPLATE_PATH = "plans/v4-N.md"

# 大写字母占位 (docs/v4-X 形态): -X 同理
_DOC_TEMPLATE_PATH = "docs/v4-X.md"

# 已知英文占位词 (your_project)
_USER_PROJECT = "projects/your_project/output/tender_brief.json"

# 大括号占位 ({...})
_GENERIC_PROJECT = "projects/{项目名}/output/c_mode/"

# 尖括号占位 (<...>)
_GENERIC_PART = "projects/<项目>/output/c_mode/<part_name>/"

# ── 2. 跨仓引用 (顶层目录不在 PATH_ROOT_DIRS) ──
# handbook 是另一个仓, 路径在本仓 PATH_ROOT_DIRS 之外
_HANDBOOK_NOTE = "handbook/_workspace/audit-2026-05-27.md"

# 相对父目录跨仓
_PARENT_HANDBOOK = "../handbook/lessons/foo.md"


def noop():
    """所有上述字符串都不应被 R10 扫描器抓为违规."""
    return [
        _HISTORICAL_PLANS,
        _PLAN_TEMPLATE_PATH,
        _DOC_TEMPLATE_PATH,
        _USER_PROJECT,
        _GENERIC_PROJECT,
        _GENERIC_PART,
        _HANDBOOK_NOTE,
        _PARENT_HANDBOOK,
    ]
