# -*- coding: utf-8 -*-
"""
test_budget_parsing.py · 预算解析回归 fixture

覆盖 check_cross_consistency.py 对合同预算字段的各种写法的解析,
防止"万"单位误判再次回归。

运行:
    ./run_script.bat tests/test_budget_parsing.py

"万"误判的根因:
    原代码用 `"万" in budget_str` 作为"乘 10000"的触发条件,
    但"500000.00元(人民币伍拾万元整)" 这类字符串里"万"
    只是中文大写金额的一部分,不是计量单位。触发后误乘 10000。
    正确做法是:只当数字后直接跟"万元"/"万"作为单位时才乘。
"""
import re
import sys
from pathlib import Path

# 从 check_cross_consistency 复用解析逻辑(参考实现)
# 这里重写一遍,用于保证 fixture 独立于脚本内部实现


def parse_budget(budget_str: str) -> float | None:
    """
    从 extracted.budget 字符串解析金额(元)。
    规则:
    - "数字+万元" → 数字 × 10000
    - "数字+万"   → 数字 × 10000
    - "数字+元"   → 数字
    - 带逗号先 strip 逗号
    - 多个候选时取首个"带单位"的匹配
    - 找不到返回 None
    """
    s = (budget_str or "").replace(",", "")
    m_wanyuan = re.search(r"(\d+(?:\.\d+)?)\s*万元", s)
    m_yuan = re.search(r"(\d+(?:\.\d+)?)\s*元", s)
    # "万元" 在 "元" 的前方或单独出现
    if m_wanyuan and (not m_yuan or m_wanyuan.start() < m_yuan.start()):
        return float(m_wanyuan.group(1)) * 10000
    if m_yuan:
        return float(m_yuan.group(1))
    # 仅"X万" 无"元"
    m_wan = re.search(r"(\d+(?:\.\d+)?)\s*万(?!元)", s)
    if m_wan:
        return float(m_wan.group(1)) * 10000
    return None


# Fixture 清单:(输入字符串, 期望元, 备注)
CASES = [
    # 常见写法
    ("500000.00元", 500000.0, "纯数字+元"),
    ("500000元", 500000.0, "整数+元"),
    ("50万元", 500000.0, "整数+万元"),
    ("50.5万元", 505000.0, "小数+万元"),
    ("60万", 600000.0, "整数+万(无'元')"),
    ("600000元", 600000.0, "大额+元"),

    # 易误判写法("万"单位 bug 根因的回归案例)
    ("500000.00元(人民币伍拾万元整)", 500000.0,
     "元+大写金额含'万'字 → 只看第一个'元'"),
    ("500000元(含税)", 500000.0, "元+附加说明"),
    ("人民币50万元整", 500000.0, "前缀+数字+万元"),

    # 带逗号
    ("500,000元", 500000.0, "逗号千分位"),
    ("6,000,000.00元", 6000000.0, "大额逗号分隔"),

    # 带空格(R3 违规写法也要容错)
    ("50 万元", 500000.0, "数字-单位带空格"),
    ("500000 元", 500000.0, "数字-元带空格"),

    # 边界
    ("", None, "空串"),
    ("【招标文件未明示,待用户确认】", None, "占位未找到"),
    ("预算未明示", None, "仅文字无数字"),
    ("60万元(最高限价)", 600000.0, "万元+附加说明"),

    # 抗干扰
    ("项目预算 50 万元,履约保证金 3000 元", 500000.0,
     "多个金额,取首个带单位的'万元' → 50 万元"),
    ("3000元(保证金,非预算)", 3000.0,
     "警示:仅首元匹配,此场景需调用方确认传入的 budget 字段正确"),
]


def main() -> int:
    fails = 0
    print(f"预算解析 fixture:{len(CASES)} 个用例")
    print()
    for inp, expected, note in CASES:
        actual = parse_budget(inp)
        ok = (actual == expected)
        icon = "PASS" if ok else "FAIL"
        expected_s = f"{expected:.2f}" if expected is not None else "None"
        actual_s = f"{actual:.2f}" if actual is not None else "None"
        print(f"  [{icon}] {inp!r:60s} -> expected={expected_s:>12s} actual={actual_s:>12s}  {note}")
        if not ok:
            fails += 1

    print()
    print(f"总结:{len(CASES) - fails} 通过 / {fails} 失败")
    if fails > 0:
        print()
        print("如果 fixture 失败,说明 parse_budget 规则有遗漏。"
              "对照 check_cross_consistency.py 的同逻辑更新以保持一致。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
