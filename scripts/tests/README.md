# scripts/tests · 测试目录说明

本目录是 tender-writer 工具链的回归测试集,V3-2 起补齐覆盖。

## 测试风格

- **stdlib only**:不引入 pytest / unittest 依赖,降低环境维护成本
- 每个 `test_*.py` 是**独立可执行脚本**,顶部有 docstring 说明覆盖的函数清单
- `main()` 返回退出码:`0` = 全部 case 通过;`1` = 至少 1 个 case 失败
- 内部用 CASES 列表(`(input, expected, note)` 三元组)+ 主循环逐项断言
- 失败时打印 `[FAIL]` 行,通过打印 `[PASS]` 行;末尾打印汇总

## 运行方式

**单个测试**:

```bash
./run_script.bat tests/test_budget_parsing.py
```

**一键跑全部**:

```bash
./run_script.bat tests/run_all.py
```

`run_all.py` 通过 `importlib` 动态加载所有 `test_*.py`,调其 `main()`,汇总退出码。

## 新增测试约定

新增 `test_xxx.py` 时:

1. 顶部 docstring 列出"覆盖的函数清单",并标注哪些 case 是 happy path
2. fixture 数据放 `fixtures/xxx/` 子目录,fixture 来源在 `fixtures/README.md` 顶部统一声明
3. 不在测试文件里 import 真实项目数据(`projects/<项目>/`),fixture 必须自包含
4. CASES 列表要尽量穷举边界:0 命中 / 1 命中 / 多命中 / 空输入
5. 断言 happy path + 至少 1 条边界

## 何时重跑 fixture 生成器

部分 fixture(如 compliance_check 的 docx)由 `fixtures/<scope>/_generators/make_*.py` 生成。生成产物 git track,**不每次跑测都重跑生成器**。

只在以下情况手工重跑生成器:

- fixture 设计需要变更(如新增字段、改文本内容)
- 生成器代码本身改动
- 被测脚本对 docx 的解析逻辑变化,需要更新 fixture 期望

重跑后 commit 生成的 docx + 生成器代码同一笔。
