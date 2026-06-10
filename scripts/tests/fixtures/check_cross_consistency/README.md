# check_cross_consistency 测试 fixture

V3-9 新增 4 个 docx fixture + 1 个 brief_minimal.json,用于覆盖项 4/5/6 三项检查的 clean / dirty 配对场景。

## fixture 清单

| 文件 | 用途 |
|---|---|
| `brief_minimal.json` | 配套所有 docx fixture 的最小 brief,含 extracted.project_name / buyer_name / buyer_agency_name 等字段 |
| `clean_response.docx` | 各项一致正例;含**同段两人名场景**("张三...李四 担任技术负责人...王五 担任实施") 验证 NAME_RE 不跨人 |
| `dirty_project_name.docx` | docx 项目名与 brief 字面完全不一致(jaccard < 0.4 触发项 4 失败) |
| `dirty_resume_org.docx` | "张三" 在简历章节是项目经理,在组织架构图是技术负责人(触发项 5 失败) |
| `dirty_section_ref.docx` | docx 章节最大到 4.x,但**正文段落引用 8.5 节** + **表格 cell 引用 9.1 节**;两处都在 docx 章节体系外,验证项 6 抓段落 + 表格 cell 双覆盖 |

## 来源 + 重新生成

所有 fixture 均由 `_generators/make_test_docx.py` 合成生成,无敏感数据。重新生成命令:

```bash
./run_script.bat tests/fixtures/check_cross_consistency/_generators/make_test_docx.py
```

产物 git track,不需要每次跑测重新生成。仅 fixture 设计调整时手工重跑。
