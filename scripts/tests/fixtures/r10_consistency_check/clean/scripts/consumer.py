# -*- coding: utf-8 -*-
"""consumer · clean fixture, 所有引用均合法."""

# 路径引用: scripts/valid_module.py 真实存在
# 锚点引用: business_model §8 #N20 在 docs/business_model_v1.md 真实存在
# 常量引用: 见 valid_module.VALID_CONST

from valid_module import VALID_CONST

print(VALID_CONST)
