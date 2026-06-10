# 贡献指南

> 欢迎参与 tender-writer 改进。本文档基于 V3 开发期间形成的
> Plan-Execute-Review 三阶段协议提炼,适用于本仓库的代码 / 文档
> / 测试贡献。

## 1. 协作协议

本仓库采用 Plan-Execute-Review 三阶段协议(详见 [docs/v3_planning.md](docs/v3_planning.md)):

- **Phase 1: Plan** — 写 plan 到 `plans/v3-N.md`(或未来 `plans/v4-N.md`),审核位审计划,通过后进 Phase 2
- **Phase 2: Execute** — 自主在 main 上线性 commit,自检通过即进下一个
- **Phase 3: Review** — 完工后贴 git log + diff + 自检报告给审核位

每个 V3-N(或未来 V4-N)项严格按此走,中途不允许跳阶段。

## 2. 提 issue

- 用前缀分类: `[BUG]` / `[FEATURE]` / `[DOCS]` / `[QUESTION]`
- bug 报告必含:
  - 复现步骤(最少示例)
  - 期望行为 vs 实际行为
  - Python 版本 / OS / 工具链 commit hash
- feature 请求建议先发 issue 讨论,确认范围后再写 plan

## 3. 提 PR

### 3.1 起 branch

通用规则:

- bug 修复: `fix/<short-desc>`(如 `fix/parse-tender-encoding`)
- 新功能: `feat/<short-desc>`(如 `feat/mcp-assets-provider`)
- 文档: `docs/<short-desc>`

内部维护者按 V-N 计划迭代时(如 V4-1),可用 `feat/v4-1-<desc>` 这种延续 V3 命名,但不强制。

### 3.2 commit message 格式(采用 conventional commits)

`<type>(scope): subject`(V3 期间 96% commit 已采用此格式):

- type 取值: `feat` / `fix` / `docs` / `test` / `refactor` / `chore`
- scope 取值: `v4-N` / 模块名(如 `parse_tender`) / 不带 scope 也可接受
- subject 用动词起头,英文 / 中文均可

例:

- `feat(v4-1): add MCP external assets provider`
- `fix(parse_tender): handle encrypted PDF gracefully`
- `docs(v4-2): update README install section`

### 3.3 PR 描述

- 头部链接对应 plan 文件(如 `plans/v4-N.md`)
- 列 commit 序列与对应文件
- 自检结果(测试 PASS / 烟测命令 / etc)
- 关闭哪个 issue(如有)

## 4. 测试

任何代码改动**必须**附带测试或回归验证:

```bash
./run_script.bat tests/run_all.py
```

合并前 run_all.py **12 个测试文件全 PASS** 是硬要求。新增功能建议加新 test 文件;bug 修复建议加回归 case。fixture 优先合成,不优先拷真实文件(避免 git 仓体积累积膨胀)。

## 5. 文档同步

任何代码改动伴随相应文档改动:

- 用户可见行为变化 → 改 README / SKILL.md / FAQ.md
- schema 变化 → 改 docs/manifest_schema.md
- 设计决策变化 → 改 docs/DESIGN.md
- 完成判定 / commit 序列 → 改 plans/v3-N.md(或 v4-N.md)

文档语言用中文(项目主开发语境),代码注释 / commit message 中英均可。

## 6. 红线引用

本仓库 6 条硬红线 + 10 条 AI 输出规则,贡献者(尤其 AI 代理)工作前必读:

- [CLAUDE.md](CLAUDE.md): 6 条硬红线(代建闸门 / 报错处置 / 事实来源 / 内部术语 / 字面输入 / 投标主体选择)
- [references/ai_output_rules.md](references/ai_output_rules.md): R1-R10 输出规则(不脑补 / 不演绎 / 中文无空格 / 不扩展 / brief 规范 / 模式判别 / 标题关键词 / 外部可见性 / 不代建闸门 / 报错处置)

PR review 时会重点检查红线遵守情况;违反红线需修正后才能合并。

---

## 协作工具

- 主开发环境: VSCode + Claude Code(本仓库 SKILL.md / CLAUDE.md 为 Claude Code 优化)
- 兼容 Cline / Cursor / 通义灵码等 AI IDE 插件(只要能读 SKILL.md)
- 测试 / 检查脚本统一通过 `./run_script.bat <脚本名>` 调用,不要直接 `python xxx.py`

## 项目维护者

仓库归属: [@Hugin-Z](https://github.com/Hugin-Z)
