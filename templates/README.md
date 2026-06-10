# templates/

本目录**当前仅含 `stage_samples/` 子目录**(阶段产物的规范样例)。未来若新增其他类型的模板资源(如 C-template 模板库 / 承诺函模板库),会按子目录组织。

## stage_samples/

阶段产物的**规范样例**，不是代码执行时的模板。

- `outline_template.md` — 阶段 3 产出 markdown 简报的规范格式参考
- `scoring_matrix.csv` — 阶段 2 产出 CSV 的表头规范和示例行
- `tender_brief.md` — 阶段 1 产出 markdown 简报的规范格式参考

代码按 SKILL.md 定义的 schema 生成产物，本目录供维护者 review 产物格式时参考。

## 说明：C 模式模板不放在此目录

C 模式（模板填充）的模板文件是**从具体招标文件派生**的，放在项目目录下：

```text
projects/{项目名}/output/c_mode/{part_name}/
  ├── template.docx
  ├── variables.yaml
  └── filled.docx
```

由 `scripts/c_mode_extract.py` 自动生成，不由用户手工维护。
