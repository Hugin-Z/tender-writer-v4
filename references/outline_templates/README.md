# outline_templates 目录说明

> v2 引入。按项目类型提供 outline 骨架模板,`generate_outline.py` 按 `tender_brief.json` 的 `extracted.project_type` 字段选对应模板。

## 类型判定

AI 在阶段 1 Step 2A 填 `extracted.project_type` 字段,合法值五选一:

| 类型值 | 中文名 | 典型判据 | 典型交付物 | 典型服务期 |
|---|---|---|---|---|
| `engineering` | 工程类 | 采购需求含"建设/施工/改造/工程";最终交付为建成物 | 建筑物/土建/装饰/安装完成物 | 3-24 月 |
| `platform` | 平台类 | 采购需求含"开发/建设/部署";最终交付为软件系统 | 信息化系统/平台/APP | 3-12 月 |
| `research` | 课题研究类 | 采购需求含"研究/分析/咨询/课题";最终交付为报告/研究结论 | 研究报告/可行性报告/咨询报告 | 1-6 月 |
| `planning` | 规划编制类 | 采购需求含"规划/编制/设计/方案";最终交付为规划文本/设计方案 | 总体规划/专项规划/设计方案 | 3-12 月 |
| `other` | 其他 | 不属上述四类(如设备采购/服务外包/培训) | 各种 | 不定 |

**多重特征混合**(如"研究+平台建设"):按最终交付物的主权重判定。实在模糊时判 `other` 并在 `tender_brief.md` 顶部记录"类型判定存疑"。

## 目录结构

每个类型子目录含两份文件:

- `outline_skeleton.md` — 章节骨架(从"方向 C 已重组"的完整骨架起步,而非机械截取采购需求)
- `guidance.md` — 撰写要点、该类型专属注意事项、反例

## generate_outline.py 使用方式

```
./run_script.bat generate_outline.py projects/{项目}/output/scoring_matrix.csv --out projects/{项目}/output
```

脚本自动从 `tender_brief.json` 读 `extracted.project_type`,加载对应模板;若为空或 `other`,用通用骨架(platform 作为默认);在骨架上按 `scoring_matrix.csv` 填入主撰类评分项响应章节。

AI 在阶段 3 user review 时应对照模板 `guidance.md` 做该类型专属的检查。
