# -*- coding: utf-8 -*-
"""bad_refs · dirty fixture, 每类违规至少 1 例.

故意在主体注释 (L9-12) 触发四类违规, 行号由 test_r10_consistency_check.py
断言. 本 docstring 不含触发模式, 避免行号干扰.
"""

# 主体注释 4 行, 每行 1 类违规:
# 见 docs/nonexistent.md 说明
# 按 valid_module.DELETED_CONST 判定
# 详见 business_model §8 #N99 判据
# 引用 business_model §9 章节

def noop():
    pass
