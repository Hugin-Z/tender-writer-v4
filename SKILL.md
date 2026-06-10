---
name: tender-writer
description: 政府类项目投标文件(技术标)编制专家。当用户上传招标文件、招标公告,或提到投标、技术标、响应文件、评分办法、废标条款、实质性响应、政府采购、竞争性磋商等关键词时触发。本 skill 严格按照"招标文件解析→评分矩阵构建→提纲生成→分章节撰写→合规终审"五阶段主干 + 并列阶段(4-B/4-C/6)工作流推进,确保每一分都对应到具体应答内容,杜绝漏答、错答、废标风险。适用于政府机关、事业单位、国有企业的信息化、智慧城市、数字乡村、政务系统等技术标编制场景。
---

# 标书助手 · tender-writer

> 完整修改记录见 [docs/changelog.md](docs/changelog.md)

## 零、AI 工作前必读(v2 新增硬约束)

> **每次 AI 开始工作前必须加载以下文档,不得跳过**:
>
> 1. `CLAUDE.md`(仓库根) — 根级硬红线,违反即停止工作
> 2. `references/ai_output_rules.md` — AI 输出规则 R1-R10
> 3. 本文档(SKILL.md) — 五阶段主干 + 并列阶段(4-B/4-C/6)工作流程
>
> 各阶段开头会以 `> 生成前必读:references/ai_output_rules.md 的 RN 规则` 引用对应规则条目。AI 不得跳过引用,不得在工作中违反引用规则。

## 一、设计原则(必须严格遵守)

本 skill 的所有行为都建立在以下四条原则之上,任何阶段的输出都必须先自检是否违背了这四条原则。一旦发现冲突,立即停止并向用户报告,而不是绕过原则继续推进。

### 1. Single Source of Truth(唯一事实来源)
`output/tender_brief.md` 一旦在阶段 1 生成并经用户确认,后续所有阶段(评分矩阵、提纲、正文、终审)都必须以它为唯一事实来源。（`templates/stage_samples/tender_brief.md` 是格式规范样例，不是运行时模板。）**严禁**凭模型记忆补充招标文件中没有的信息(例如预算、工期、资质要求、技术规格)。如果发现 tender_brief.md 中信息缺失,必须返回阶段 1 重新解析,而不是脑补。

### 2. 分阶段验证(Staged Verification)
每一个阶段都必须输出可被用户 review 的中间产物(markdown、csv 或 json 文件),用户**显式确认**后才能推进到下一阶段。禁止把多个阶段合并成一次性输出。任何"我先帮你把整本写完再看"的冲动都必须被压制。

### 3. 按分点应答(Point-by-Point Response)
正文撰写阶段必须严格对照 `scoring_matrix.csv` 的**每一行**逐项应答,确保没有任何一个评分项被漏掉。每写完一章,要在该章标题下方用注释标出本章覆盖了 scoring_matrix.csv 的哪几行(行号或评分项名称)。

### 4. 本地化优先(Localization First)
涉及项目所在地的地理、气候、产业结构、人口、行政区划、产业基础、信息化基础等描述时,**必须**基于真实情况撰写。**严禁**使用"该地区资源丰富、产业兴旺、人民安居乐业"之类的通用空话套话。如果模型对项目所在地不熟悉,应在 tender_brief.md 中明确标注"待用户补充本地化信息",而不是编造。

### 5. 脚本与 AI 职责边界

> 本节定义脚本与 AI 在工作流中的职责边界,是后续阶段的元规则。

脚本做纯数据处理（格式转换、字段校验、文件读写），不做语义推断。`production_mode`（Part 生产模式）和 `part_attribution`（评分项归属 Part）的判断是 AI 职责（阶段 1 Step 5/6），脚本只负责校验这些字段是否已填充且格式合法。缺失字段时脚本硬失败（退出码 1），不静默兜底。

---

## 二、五阶段主干 + 并列阶段(4-B/4-C/6)工作流(严格分阶段,绝不允许跳过或一键生成)

### 阶段 1:招标文件解析

> **生成前必读**:`references/ai_output_rules.md` 的 **R1(不脑补)/ R2(不扩展字面输入)/ R5(tender_brief.md 生成规范)** 规则。

**目标**:把招标文件读懂、读透,把所有和投标方相关的关键信息结构化提取出来。

**操作(脚本 → AI → 用户 三段式)**:

**Step 1 — 脚本跑数据提取**:
1. 用户上传招标文件(PDF 或 docx)后,调用脚本:
   ```
   ./run_script.bat parse_tender.py "<招标文件绝对路径>"
   ```

   **扫描版 PDF 处理**:parse_tender 自动检测 PDF 字符密度,< 50 字/页判定为扫描版(无内嵌文字流)。命中扫描版时脚本退出并列出 3 条用户处理路径(本地 OCR / 外部 AI / 找原版)。如已用外部工具 OCR 出文本,可加 `--ocr-text <txt路径>` 让 parse_tender 跳过 PDF 文字提取走 fallback 通道。详见 [docs/FAQ.md Q4](docs/FAQ.md)。

   **重跑保护机制**:parse_tender 默认拒绝覆盖已存在的 `output/tender_brief.json`。如果因招标文件更新或逻辑调整需要重跑,加 `--force` 参数。重跑后 extracted 字段回到空骨架。⚠️ 当前 `ensure_reviewed` 闸门只检查 `.reviewed` 文件存在性,**不校验 hash**,因此**用户必须手动删除 `.reviewed` 标记**,否则下游脚本仍会放行使用空骨架数据。hash 校验机制留 V4 实现。不加 --force 时脚本会提示错误并退出。如需在重跑前清干净 demo 项目 output/ 状态(回 HEAD baseline + 保留 .reviewed 标记),用 `./run_script.bat demo_reset.py`(详见 [docs/FAQ.md Q6](docs/FAQ.md))。

2. 脚本会输出:
   - `output/tender_brief.json`:含 `raw_lines_for_ai`(带行号+特征的全文行列表)、`tables`(PDF 中所有表格的二维结构,详见下方)、`section_anchors`(空,待 AI 填)、`extracted`(预算/工期/资质/★▲ + 项目核心字段: project_name / project_number / buyer_name / buyer_agency_name 自动提取)、`part_list_candidates`(Part 清单候选段落,脚本自动生成)、`score_items_raw_positions`(评分项粗位置,首次运行为空,二次运行自动生成)
   - **tables 字段**:PDF 中所有表格的二维结构,每个 table 含 `table_id` / `page_num` / `headers` / `rows` / `evidence`。由 `pdfplumber.extract_tables()` 自动提取。table_id 全局编号(t_001, t_002, ...)跨页连续。
   - `output/tender_brief.md`:基于模板填充的 markdown 简报(章节内容待 AI 标注后补充)
   - `output/tender_raw.txt`:纯文本全文

**Step 2A — AI 读原文填 extracted 字段(v1.2+ 两层验证,硬门槛)**:

parse_tender.py 产出的 `extracted` 字段是空骨架(9 个字符串字段为 "" + qualifications 为 [] + substantial_response_marks 已由脚本抽出 + **v2 新增 project_type 空串**)。AI 必须读 `raw_lines_for_ai` 或 `tender_raw.txt` 原文,直接判定并填入以下 **11** 个字段:

- `procurement_method` / `budget` / `cap_price` / `duration` / `delivery_location`
- `project_name` / `project_number` / `buyer_name` / `buyer_agency_name`
- `qualifications`(资格要求列表,从"供应商资格要求"章节抽取)
- **`project_type`(v2 新增)**:项目类型五选一,影响阶段 3 generate_outline 选哪份模板骨架。
  - 合法值:`engineering`(工程) / `platform`(平台) / `research`(课题研究) / `planning`(规划编制) / `other`(其他)
  - 判据:
    - **采购需求关键词**:采购需求章节含"建设/施工/改造" → engineering;含"开发/建设/部署(系统/平台)" → platform;含"研究/分析/咨询/课题" → research;含"规划/编制(规划)/设计(方案)" → planning;其他 → other
    - **最终交付物类型**:建成物 → engineering;软件系统 → platform;研究报告 → research;规划文本/设计方案 → planning
    - **服务期限参考**:课题研究常 1-6 月,规划 3-12 月,平台 3-12 月,工程 3-24 月(只作辅助判据,不作硬规则)
  - 多重特征混合时按最终交付物主权重判定;实在模糊判 `other` 并在 tender_brief.md 顶部记录"类型判定存疑"
  - 类型对应的 outline 骨架模板详见 `references/outline_templates/README.md`

复杂句式必读:项目编号、采购人、采购代理机构等字段经常出现"XX 受 YY 委托"这类嵌套句式,AI 必须基于语义理解逐字段填。substantial_response_marks 由脚本按 ★/▲ 符号抽取,AI 只需 review 不需要重填。

**不允许**空值静默通过——每个字段都需要 AI 显式判定(找到值 → 填;未找到 → 填"未在招标文件中找到")。漏填会在 Step 3 用户 review 或下游脚本启动的 `ensure_reviewed` 闸口被截住。

**示例 prompt(直接让对话里的 AI 做)**:

> 以下是 tender_brief.json 的 raw_lines_for_ai 片段,请从中判定并填充 extracted 字段的 11 个字段(10 个字符串 + qualifications 列表)。找到的值直接填入,未找到的字段填"未在招标文件中找到",不得留空或编造。输出修正后的 extracted dict(JSON 格式)。
>
> [此处粘贴 raw_lines_for_ai 相关片段]

**背景**: 早期版本曾用 parse_tender 脚本的 regex 做初提(带 draft 前缀机制)+ AI 校对两层。后续清理后改为主 agent 直读原文,脚本不做初提——脚本只做无歧义数据提取,语义判断交 AI。

**Step 2 — AI 标注 section_anchors**:
3. AI 读取 `tender_brief.json` 中的 `raw_lines_for_ai`,为以下关键章节标注起止行号,写回 `tender_brief.json` 的 `section_anchors` 字段:

   必须标注的章节:
   - **评审办法**(或"评分办法/评标办法"):评分前附表+评分标准正文
   - **采购需求**(或"技术要求"):功能需求+技术规格+工程量清单
   - **供应商资格要求**:资质/业绩/人员/信誉最低要求
   - **响应文件格式**:响应文件组成+格式要求

   `section_anchors` 格式:
   ```json
   [
     {"section": "评审办法", "start_line": 669, "end_line": 889,
      "confidence": "high",
      "is_embedded": false, "embedded_in": null,
      "evidence": "第669行'第三章 评审办法'为独立标题行,670-889为评分前附表+评分标准正文"}
   ]
   ```

   注：`start_line` 为 inclusive（含本行），`end_line` 为 exclusive（不含本行，即实际范围到 end_line-1）。遵循 Python 切片惯例：`lines[start_line:end_line]`。

   **嵌入式章节字段说明**:
   `section_anchors` 每条含 `is_embedded` / `embedded_in` 字段,填法:
   - 关键章节独立成章 → `is_embedded=false`, `embedded_in=null`
   - 关键章节嵌入到上层章节中(如供应商资格要求嵌入第一章附录) → `is_embedded=true`, `embedded_in` 填上层章节名
   - `evidence` 字段说明嵌入位置(段落编号或小节标题)

   **AI 标注判断原则(区分真章节标题 vs 目录/引用)**:
   - 真章节标题:独立成行 + 有章节编号(第X章/X.X) + 行长 < 30 字 + 前后有空行或页码行 + 不含省略号引导符
   - 目录条目:含连续点号"....."或页码数字,跳过
   - 正文引用:如"详见评审办法第X条"、"按照评审办法前附表的规定",这是引用不是标题,跳过
   - 表格内拍平文本:如果一行看起来像表格单元格拼接(含多个制表符或短语堆叠),不是标题

4. AI 从原文(tender_raw.txt)中**强制**提取以下字段,填入 tender_brief.md 对应位置;**同时校对并补齐 tender_brief.json 的 `extracted` 字段(4 项项目核心信息)**:
   - 项目名称(**写入 `extracted.project_name`**,从招标文件首页/封面/项目概述提取)
   - 项目编号(**写入 `extracted.project_number`**,从封面或项目基本信息提取招标编号/采购编号)
   - 采购人全称(**写入 `extracted.buyer_name`**)
   - 采购代理机构全称(**写入 `extracted.buyer_agency_name`**,无代理机构则留空串 `""`)
   - 项目预算(总预算、最高限价、单项限价)
   - 项目工期(总工期、关键里程碑)
   - 投标人资格要求(资质等级、业绩、人员、注册资金等)
   - 评分办法(技术分/商务分/价格分的权重分配,每个评分项的具体分值)
   - 实质性响应条款(★条款、▲条款、必须响应条款)
   - 废标条款(常见废标情形清单)
   - 格式要求(字号、字体、行距、页边距、封面样式、目录要求)
   - 投标文件构成、装订要求、份数要求
   - 开标时间、地点、投标截止时间

   parse_tender.py 已对 4 个项目核心字段做 regex 初提,AI 必须在 Step 2 校对并修正(regex 可能命中错误或留空,特别是嵌入在段落中的项目名)。这 4 个字段是 C 模式模板填充的重要数据源,必须准确。

   **字段处理规则(AI 填充 tender_brief.md 时必须遵守)**:

   **未找到字段处理规则**:
   原文中未找到字段对应信息时,按字段类型分三类降级处理:
   - **格式类**(字体/字号/行距/页边距):降级使用 `references/doc_format_spec.md` 默认值,在字段值末尾标注【降级使用默认值】
   - **关键业务类**(里程碑/付款/工期/履约保证金等):必须标【未找到】并在 `tender_brief.md` 顶部"提醒维护者补"清单中列出
   - **可选字段类**(联系人备用电话/传真等):可标【未找到】不影响后续

   不允许的处理方式:
   - 用 AI 训练数据/通用知识补字段
   - 静默标【未找到】不进提醒清单(关键业务类)

   **矛盾/不一致记录字段**:
   `tender_brief.md` 顶部增加"招标文件矛盾/不一致记录"字段,专门收集招标文件自身的内部矛盾。下游阶段必读。
   典型矛盾类型:
   - 评审办法引用★条款但正文无★标记
   - 投标须知前附表与正文条款不一致
   - 同一字段在不同章节给出不同值
   - 评分项分值合计不等于总分

   每条记录含:
   - 矛盾描述
   - 涉及位置(章节名 + 行号)
   - 风险等级(高/中/低)
   - 建议处理(答疑澄清/按原文从严/按原文从宽)

   **字段定义降级填入规则**:
   原文不严格匹配字段定义时,允许 AI 降级填入相关信息+说明语义差异,不许直接标【未找到】丢弃有用信息。
   例:
   - "关键里程碑"无严格里程碑 → 填付款节点(30%+30%+30%+10%),备注"原文未给项目里程碑,降级填入付款节点"
   - "投标保证金金额"未明确但有"无需保证金"声明 → 填"豁免",引用原文位置

   降级原则:
   - 降级填入的信息必须来源于原文(不许编造)
   - 必须在字段值后标注【降级】+ 说明语义差异
   - 关键业务类字段降级后仍需进矛盾/不一致记录,提醒维护者复核

   **跨章节汇总类字段提取规则**:
   "废标条款"、"实质性响应条款"等跨章节汇总类字段,AI 全文搜索关键词后逐条提取,每条带行号。
   跨章节汇总字段清单:
   - **废标条款**:关键词 否决/无效/拒收/不予采纳
   - **实质性响应条款**:关键词 ★/必须/应当/不得

   提取格式:
   - 每条独立成行
   - 末尾带原文行号引用 (L###)
   - 不去重,允许多章节出现的同条款重复列出(后续维护者判断)

   **电子采购场景映射**:
   "投标文件构成、装订要求、份数要求"字段定义基于传统纸质投标模式。遇到电子采购项目时,AI 先判断采购模式(电子/纸质/混合),再按以下映射填字段:
   - **电子采购**:无正本/副本/装订概念,填电子递交方式(平台名称/CA证书/文件格式)+成交后纸质份数(如有)
   - **纸质投标**:按传统字段定义填正本/副本/装订/密封方式
   - **混合模式**:电子+纸质分别填,标注哪部分电子递交/哪部分纸质递交

   **section_anchors 写回操作指引**:
   AI 写回 `section_anchors` 时必须用 Python 精准修改 JSON 的 `section_anchors` 键,不要整体读写 JSON。工作流:
   - 读 `tender_raw.txt`(与 `raw_lines_for_ai` 同源,行号一致)定位章节起止行号
   - 用 Python 内联命令读取 `tender_brief.json`,只修改 `section_anchors` 字段,保留其他字段不变
   - 写回 JSON 时确保 `ensure_ascii=False, indent=2` 保持文件可读

   示例命令:
   ```
   .venv/Scripts/python.exe -c "
   import json
   from pathlib import Path
   p = Path('projects/{项目名}/output/tender_brief.json')
   data = json.loads(p.read_text(encoding='utf-8'))
   data['section_anchors'] = [
       {
           'section': '...',
           'start_line': N,
           'end_line': N,
           'confidence': 'high',
           'is_embedded': False,
           'embedded_in': None,
           'evidence': '...'
       },
       ...
   ]
   p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
   "
   ```

   写回完成后,跑 `update_score_positions.py` 生成 `score_items_raw_positions` 字段：
   ```
   ./run_script.bat update_score_positions.py projects/{项目名}/output/tender_brief.json
   ```

**Step 3 — 用户 review(硬门槛 + review 标记)**:

下游脚本(build_scoring_matrix / generate_outline / append_chapter / compliance_check / c_mode_* / update_score_positions)在未 review 状态下启动会硬失败(`ensure_reviewed` 闸口)。

用户打开 `output/tender_brief.json` 或 `output/tender_brief.md`,按以下 checklist 逐项核对:

- [ ] `extracted` 下 11 个字段(10 个字符串 + qualifications 列表)全部由 AI 在 Step 2A 填充完成,无空值或 "__PENDING_AI__" 残留
- [ ] `project_name` / `project_number` / `buyer_name` / `buyer_agency_name` 四个字段特别确认(项目核心信息,正则常踩坑)
- [ ] `★/▲` 条款清单(`substantial_response_marks`)数量和内容符合原文
- [ ] `response_file_parts` 中每个 Part 的 `production_mode` 归属合理(A/B/C/D/不适用)
- [ ] `section_anchors` 的章节起止行号无明显错误(重点核对"评审办法"覆盖完整的评分前附表)
- [ ] **tables 字段数量合理,关键表(分项报价表、资格审查表、评审因素表)都被提取到**
- [ ] **response_file_parts 中表格型 Part 的 `source_anchor.type` 为 `"table"` 且 `table_ids` 指向正确的 table;文本型 Part 为 `"text"`**
- [ ] 其他顶层字段(source_file、char_count 等)无异常
- [ ] `tender_brief.md` 所有【待补充】字段已补全,字段填充遵循 Step 2 字段处理规则(#3-#7)

checklist 全部通过后,创建 review 标记文件:

```bash
# bash / git bash
touch projects/{项目名}/output/tender_brief.reviewed
```

```powershell
# PowerShell
echo $null > projects/{项目名}/output/tender_brief.reviewed
```

或在 IDE 里新建一个名为 `tender_brief.reviewed` 的空文件(不带点号前缀,Windows 兼容)。

**回溯流程**:如果在后续阶段发现问题源自阶段 1,必须:

1. **删除** `tender_brief.reviewed`
2. 修正 `tender_brief.json`(可能需要重跑 parse_tender + 重新 AI 校对)
3. 重新走 Step 3 review checklist
4. 重建 `tender_brief.reviewed`

跳过此流程直接改 tender_brief.json 而不重建 review 标记,下游脚本仍然会因为"磁盘和 review 状态脱钩"产生未知问题。

**产物**:`output/tender_brief.json`(含 section_anchors)+ `output/tender_brief.md` + `output/tender_brief.reviewed`

**完成标志**:`tender_brief.reviewed` 文件存在。**禁止**在用户未确认前推进到 Step 4。

**Step 4 — Part 清单识别(对应业务模型 #N1 / #N4)**:

触发:Step 3 完成(section_anchors 和 tender_brief.md 已确认)后。

输入:`tender_brief.json` 的 `part_list_candidates` 字段(`parse_tender.py` 自动生成,含 `chapter` / `front_table` / `keyword_match` 三类候选)。

7. AI 阅读全部候选段落,识别招标文件规定的 N 个 Part:
   - 每条候选含 `source` / `text` / `start_line` / `end_line`
   - 候选可能重叠,AI 需识别哪些指向同一份"投标文件组成"规定
   - 逐项确定:
     - `id`:part_01, part_02, ... 按招标文件原文顺序编号
     - `name`:必须用招标文件原文措辞,不许概括/简化/翻译
     - `order`:整数,与 id 一致
     - `source_anchor`: 区分 type:
       - `type: "text"`(段落/列表/承诺条款等线性文本 Part):`{ type: "text", start_line, end_line, evidence }`
       - `type: "table"`(表格型 Part,如分项报价表/资格审查表):`{ type: "table", table_ids: ["t_00N", ...], evidence }`,不填 start_line/end_line
       - 判断准则:打开 tender_brief.json 的 tables 字段,如果目标 Part 的内容已被 pdfplumber 完整提取成表格(headers + rows 匹配 PDF 原表结构),用 table 型;否则 text 型
       - 混合场景(主体是段落 + 少量表格)优先选 text 型——table 型只用于"内容主体是一张表"的 Part

   **容错(#N4)**:
   若所有候选都没识别出明确 Part 清单 → **停下报告**:
   "未发现 Part 清单明确规定。反推方案:[基于评审办法+技术要求章节反推的 N 个 Part]。等用户确认。"
   **严禁**套用通用模板(技术/商务/报价三段式等)。

8. AI 用 Python 精准修改 JSON,写回 `response_file_parts` 数组(沿用 Step 2 写回操作指引,不整体读写)。
   写回完成后,跑 `update_score_positions.py` 生成 `score_items_raw_positions`（供 Step 6 使用）：
   ```
   ./run_script.bat update_score_positions.py projects/{项目名}/output/tender_brief.json
   ```

输出:
- `tender_brief.json` 的 `response_file_parts`(N 个 Part 元数据)
- `score_items_raw_positions`（`update_score_positions.py` 生成）

**完成标志**:`response_file_parts` 写回完成,推进到 Step 5。

> **⚠️ Step 4 完成后必须跑 `update_score_positions.py`**,否则后续 Step 6 读不到 `score_items_raw_positions`。命令见上方 item 8 末尾。

**Step 5 — Part 生产模式判别(对应业务模型 #N2)**:

触发:Step 4 完成后。

输入:每个 Part 的 `name` + 该 Part 在招标文件中的描述段落（`response_file_parts[i].source_anchor` 范围内的原文）。

9. AI 对每个 Part 判定 `production_mode`:
   - **A 文本生成**(AI 按骨架写作):技术响应方案、服务方案、施工组织设计
   - **B 材料组装**(从 assets 抽取插入):资质证明、业绩合同、获奖证书
   - **C 模板填充**(固定模板+变量替换):投标函、承诺函、法代授权书、报价表
   - **D 外部信息采集**(网站查询+截图+插入):信用信息、企业基本情况查询
   - **不适用**:本项目不需要的 Part(联合体协议(非联合体)、保证金(已豁免)等)

   判别冲突处理:
   - 一个 Part 同时含多模式内容(如"技术响应方案及业绩证明") → 判主导模式,在 evidence 字段说明
   - 模式判不出 → **停下报告**,不静默归类

10. 写回 `response_file_parts[i].production_mode`(沿用 Step 2 写回操作指引)。

   注意:v1.1 仅生成模式 A 的 Part。其他模式的 Part 信息进 `tender_brief` 但不触发后续生成流程。这一行为由阶段 3-4 处理,Step 5 只判别不过滤。

输出:每 Part 含 `production_mode` 字段。

**完成标志**:全部 Part 含 `production_mode`,推进到 Step 6。

**Step 6 — 评分项 Part 归属标注(对应业务模型 #N3)**:

触发:Step 5 完成后(`response_file_parts` 已含 `production_mode`)。

输入:
- `tender_brief.json` 的 `score_items_raw_positions`(每条评分项的粗位置切片)
- `response_file_parts`(全部 Part 列表 + 各自 `production_mode`)

11. AI 阅读每条评分项的 `raw_text`,判定 `part_attribution`:
    - 归属判断本质:AI 基于评分项内容描述,推断"响应这条评分项需要交什么材料/写什么内容" → 落在哪个 Part。这是 AI 语义推断,不是简单的文本位置匹配
    - 例:
      - "供应商业绩(20分)..." → 要求提供业绩证明材料 → 资格审查资料 Part
      - "对项目理解(10分)..." → 要求编写技术方案 → 技术响应方案 Part
      - "报价得分(20分)..." → 响应产物是报价表 → 分项报价表 Part
    - `part_attribution` 值必须与 `response_file_parts[i].name` **严格一致**(字符级匹配,不许同义改写)

    归属容错(**必停**):
    - 一个评分项的响应内容明确分散在两个 Part(例:报价得分评审价取自开标一览表,但明细必须在分项报价表) → **停下报告**:"评分项 X 响应分散于 Part A 和 Part B,需维护者裁决主归属或拆分。"
    - 一个评分项无法对应到任何已识别的 Part(例:Part 清单缺漏) → **停下报告**:"评分项 X 找不到对应 Part,可能 Step 4 Part 清单遗漏,需维护者复核。"
    - **严禁**静默归属

12. 在 `score_items_raw_positions` 每条加 `part_attribution` 字段(写在评分项侧,不在 Part 侧维护反向索引)。
    写回示例:
    ```
    .venv/Scripts/python.exe -c "
    import json
    from pathlib import Path
    p = Path('projects/{项目名}/output/tender_brief.json')
    data = json.loads(p.read_text(encoding='utf-8'))
    for item in data['score_items_raw_positions']:
        # AI 逐条判断后填入,以下仅为写回机制示例:
        item['part_attribution'] = 'AI 判定的 Part 名称'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    "
    ```
    (示例中 `part_attribution` 的赋值仅用于说明写回机制。实际判断必须 AI 阅读 `raw_text` 后逐条人工判定,不许写自动化规则。)

输出:每条评分项含 `part_attribution`(Part 名称)。

**完成标志**:全部评分项含 `part_attribution`,阶段 1 全部完成。推进到阶段 2。

### review 标记的生命周期

`tender_brief.reviewed` 文件存在 = 当前 `tender_brief.json` 状态经过人工确认,下游可放心使用。

**标记失效的场景**:

- 手动编辑 `tender_brief.json`(任何修改都应视为标记失效)
- 重跑 `parse_tender.py`(会重新生成 tender_brief.json,标记失效)
- 工具链升级导致 schema 变化(`migrate_brief_schema.py` 运行后,应删除标记重新 review)

失效后必须删除标记文件,重走 Step 3。

---

### 阶段 2:评分矩阵构建

> **生成前必读**:`references/ai_output_rules.md` 的 **R8(外部可见性,撰写指引不得含"取档策略/素材钩子/应答骨架"等内部术语)** 规则。

**目标**:把评分办法拆解成一张可逐行追踪的矩阵,每一分都有归属。

**CSV 10 列 schema**:

| 列号 | 列名 | 数据来源 | 填写时机 |
|---|---|---|---|
| 1 | 评分项归属 | `part_attribution` 直接拷贝 | 脚本(阶段 2 Step 1) |
| 2 | 评分项 | AI 从 `raw_text` 提取 | AI(阶段 2 Step 2) |
| 3 | 分值 | AI 从 `raw_text` 提取整数 | AI(阶段 2 Step 2) |
| 4 | 评分标准 | AI 从 `raw_text` 完整段落提取 | AI(阶段 2 Step 2) |
| 5 | 关键词 | AI 提炼标题检索用关键词 | AI(阶段 2 Step 2) |
| 6 | 应答章节 | 脚本填 placeholder,阶段 3 回填 | 脚本(阶段 2) + AI(阶段 3) |
| 7 | 证据材料 | AI 判断该评分项需提供的证据材料 | AI(阶段 2 Step 2) |
| 8 | 风险提示 | AI 判断撰写该评分项的风险点 | AI(阶段 2 Step 2) |
| 9 | 撰写指引 | AI 生成三子点(**章节结构建议 / 评分档位要求 / 素材来源**;对外用自然语言,禁用工具链内部术语) | AI(阶段 2 Step 2) |
| 10 | 必备要素 | AI 基于评分项语义推断必须出现的具体名词 | AI(阶段 2 Step 2.5) |

**操作(脚本 → AI → 用户 三段式)**:

**Step 1 — 脚本生成 CSV 骨架**:
1. 调用脚本:
   ```
   ./run_script.bat build_scoring_matrix.py projects/{项目名}/output/tender_brief.json --out projects/{项目名}/output
   ```
2. 脚本从 `tender_brief.json` 读取 `score_items_raw_positions`(每条评分项的粗位置 + `part_attribution`)和 `response_file_parts`(各 Part 的 `production_mode`),输出 `output/scoring_matrix.csv`(UTF-8 with BOM 编码,Excel 直接打开不乱码):
   - 第 1 列(评分项归属):直接拷贝 `part_attribution`
   - 第 6 列(应答章节):
     - `production_mode == 'A'` → `"{part_name} / [待阶段 3 回填]"`
     - `production_mode != 'A'` → `"{part_name} / [非 v1.1 范围]"`
   - 其余 7 列:留空,由 AI 在 Step 2 填充

   **schema 升级场景**:
   如果 `scoring_matrix.csv` 已存在但列数与当前 `SCORING_MATRIX_COLUMNS` 不一致(常见于工具链升级后在旧项目上回跑),**不要**直接跑 `build_scoring_matrix.py`——它会拒绝执行并提示走 migrate 路径。正确流程:
   1. 跑 `migrate_brief_schema.py` 做 schema 迁移(按列名匹配回填已有数据,缺失列填 `__PENDING_AI__`)
   2. 迁移完成后检查 csv,新增列的值应为 `__PENDING_AI__`
   3. AI 补齐 `__PENDING_AI__` 占位的新列数据
   4. 继续阶段 2 后续步骤

   如果是初次生成,直接跑 `build_scoring_matrix.py` 即可(文件不存在时不会有冲突)。如需强制重建(对已有数据不满意要重来),加 `--force` 参数,此操作会覆盖已有数据。

**Step 2 — AI 填充评分矩阵**:
3. AI 同时读取 `scoring_matrix.csv` 和 `tender_brief.json`,对每一行执行:
   - 读取对应 `score_items_raw_positions[i].raw_text`(评分项原文)
   - 填第 2 列(评分项):从 `raw_text` 第一行提取评分项名称(如"供应商业绩(20分)")
   - 填第 3 列(分值):从 `raw_text` 提取整数分值
   - 填第 4 列(评分标准):从 `raw_text` 完整段落提取评分标准原文
   - 填第 5 列(关键词):提炼标题检索用关键词(供阶段 3 提纲使用)
   - **不动**第 1 列(已由脚本填)和第 6 列(等阶段 3 回填)
   - 填第 7 列(证据材料):列出能为该项加分的支撑材料(类似项目案例、获奖证书、人员资质、产品检测报告等)
   - 填第 8 列(风险提示):标注是否为 ★/▲ 条款、是否容易漏答、是否需要附件证明
   - 填第 9 列(撰写指引):生成三子点(见下方"撰写指引分类参考")
   - 报价类评分项撰写指引标注"N/A - 报价策略项",给出报价策略建议

4. **每一个独立的评分项必须独立成行**。`score_items_raw_positions` 的粗切片可能包含多个子评分项,AI 拆分时:若分值未明确细分,按合理比例拆分并在风险提示中标注"原文未细分,需复核"。

   **CSV 写回操作指引**:
   AI 写回 CSV 时必须用 Python csv 模块读写(utf-8-sig 编码),确保含逗号/引号/换行的字段被正确转义。不要用 Edit 工具逐行替换 CSV(易破坏格式)。
   示例命令:
   ```
   .venv/Scripts/python.exe -c "
   import csv
   from pathlib import Path
   p = Path('projects/{项目名}/output/scoring_matrix.csv')
   rows = list(csv.reader(p.open(encoding='utf-8-sig')))
   headers, data = rows[0], rows[1:]
   # AI 逐行填充第 2-5 列和第 7-9 列
   for row in data:
       row[1] = '评分项名称'   # 第 2 列
       row[2] = '20'           # 第 3 列
       row[3] = '评分标准原文'  # 第 4 列
       row[4] = '关键词'       # 第 5 列
       # row[5] 不动            # 第 6 列(placeholder)
       row[6] = '证据材料'     # 第 7 列
       row[7] = '风险提示'     # 第 8 列
       row[8] = '撰写指引'     # 第 9 列
   with p.open('w', encoding='utf-8-sig', newline='') as f:
       csv.writer(f).writerows([headers] + data)
   "
   ```

   **评分档位要求推荐写法**(对外表述,禁用"取档策略"一词):
   撰写指引第二子点(评分档位要求)推荐句式:"X 要素必须同时体现,缺任一会被压到 N 档"。把主观评分档次转化为可执行的自检清单。避免"应当表现出设计完善"这类空话。

   **外部可见性硬约束(v2 新增)**:
   scoring_matrix.csv 第 9 列"撰写指引"面向使用者(标书经理、标书编制人员、评审复核人员),**禁用**以下工具链内部术语:
   - 禁用"取档策略" → 改为"评分档位要求"
   - 禁用"素材钩子" → 改为"素材来源"
   - 禁用"应答骨架" → 改为"章节结构建议"
   - 禁用"mode A/B/C/D" / "production_mode" / "part_attribution" 等工具链字段名
   详见 `references/ai_output_rules.md` R8。

**Step 2.5 — AI 填写必备要素(第 10 列)**:

AI 对每个评分项填写"必备要素"列,规则如下:

- 参考该行的**关键词列(第 5 列)**和**评分标准列(第 4 列)**推断该章节必须包含的要素,不要凭空想象
- 每个评分项至少列 3 个必备要素,上不封顶
- 多个要素用分号分隔(中文分号或英文分号均可)
- 要素必须是**可在章节文本中硬出现的具体名词**(型号、数字、名称、技术参数),不要写抽象描述
- 非 A 模式评分项可留空

正面示例:
- 雷达升级评分项 → "毫米波雷达;工作频段;探测距离;通信协议;安装调试"
- 售后方案评分项 → "响应时间;故障分级;巡检频次;培训课时;缺陷责任期"

反面示例(禁止):
- ❌ "先进性;完整性;合理性" — 这些是评分标准的措辞,不是可 grep 的具体名词
- ❌ "方案设计水平;技术可行性" — 同上,无法在文本中做子串匹配

AI 填完之后,用 Python csv 模块写回(与 Step 2 同一次写回操作即可)。

**Step 3 — 用户 review**:
5. 用户 review `scoring_matrix.csv`:
   - 第 1 列归属是否正确(与 `tender_brief.json` 的 Part 清单一致)
   - 第 2-5 列评分项/分值/标准/关键词是否准确
   - 第 6 列 placeholder 是否合理(模式 A 待回填,其余非范围)
   - 第 7-9 列证据材料/风险提示/撰写指引质量
   - 第 10 列必备要素是否合理(检查要素是否为可 grep 的具体名词,此时修改成本最低)

### 撰写指引分类参考(对外表述)

AI 在生成"撰写指引"第 9 列时,按以下分类给出**章节结构建议**(对外禁用"应答骨架"一词):

- **业绩类**评分项(关键词:业绩/案例/项目经验):章节结构建议通常为「业绩总览(数量/领域) → 典型案例详述(每案含项目名/金额/周期/成效) → 与本项目关联性分析」;素材来源为 `assets/类似业绩/<company_id>/`
- **人员类**评分项(关键词:人员/团队/证书/职称):章节结构建议通常为「团队配置表 → 项目负责人简历 → 关键人员简历与证书」;素材来源为 `assets/团队简历/<company_id>/`
- **技术类**评分项(关键词:架构/方案/设计/功能):章节结构建议须嵌入项目具体技术点;素材来源为 `assets/通用图表/<company_id>/`(架构图)+ `assets/标准话术/<company_id>/`(技术方案话术)
- **服务类**评分项(关键词:售后/培训/运维/响应):章节结构建议通常为「服务体系 → 响应机制 → 培训计划 → 应急预案」;素材来源为 `assets/标准话术/<company_id>/`
- **报价类**评分项(关键词:报价/价格/公式):撰写指引标注 N/A,给出报价策略建议

**产物**:`output/scoring_matrix.csv`(9 列,用户必须 review 并确认)

**完成标志**:9 列填齐(第 6 列保留 placeholder),用户确认后推进到阶段 3。**禁止**跳过本阶段直接写提纲。

---

### 阶段 3:提纲生成

**目标**:为 v1.1 范围内的 Part（`production_mode==A`）生成章节提纲,并回填 `scoring_matrix.csv` 第 6 列章节路径。其他模式的 Part 不入提纲。

**方向 C 说明**:`outline.md` 采用方向 C（整体方案主干 + 招标技术要求逐条以独立标题嵌入）。脚本输出主干段 + 评分项响应段两段式结构,AI 在阶段 4 撰写时融合。

**操作(脚本 → 用户 两段式)**:

**Step 1 — 脚本生成提纲 + 回填 CSV**:
1. 调用脚本:
   ```
   ./run_script.bat generate_outline.py projects/{项目名}/output/scoring_matrix.csv --out projects/{项目名}/output
   ```
2. 脚本同时读取 `scoring_matrix.csv` 和同目录的 `tender_brief.json`:
   - 从 `tender_brief.json` 读 `response_file_parts`,取 `production_mode==A` 的 Part 名称集合,识别 CSV 第 1 列归属于这些 Part 的行作为 mode A 评分项,其余跳过
   - 从 `tender_brief.json` 的 `section_anchors` 中定位"采购需求"章节,提取子标题作为整体方案主干
   - 输出 `outline.md`(方向 C 两段式):
     - **一、整体方案主干**:采购需求章节的子标题骨架
     - `[待 AI 阶段 4 重组]` 占位标记
     - **二、评分项响应章节**:每条 mode A 评分项独立成节,标注分值+关键词+撰写指引行号引用
     - **覆盖度自检表**:确认每条 mode A 评分项都有对应章节
   - 同时回填 `scoring_matrix.csv` 第 6 列:
     - 原 `"{Part} / [待阶段 3 回填]"` → `"{Part} / 二.N {评分项名}"`
     - 已回填的行不重写（幂等）

**Step 2 — 用户 review**:
3. 用户 review `outline.md`:
   - 主干条目是否完整覆盖采购需求
   - 评分项响应章节是否齐全（对照覆盖度自检表）
   - 章节命名和顺序是否合理
4. 用户 review `scoring_matrix.csv` 第 6 列回填结果:
   - 原 `[待阶段 3 回填]` 已全部变为 `"{Part} / 章节路径"`
   - `[非 v1.1 范围]` 行未被改动

   **提纲 review 颗粒度下钻**:
   维护者 review `outline.md` 时,必须下钻到以下层级(不能只看标题列表就过):
   - 主干每条与采购需求原文对照:是否遗漏关键需求条目
   - 评分项响应章节与 `scoring_matrix.csv` 归属列对照:每条评分项是否归属正确的 Part
   - 章节方向一致性:主干条目的技术方向是否与其下嵌入的评分项响应方向一致(例:主干"系统设计与开发"下不应嵌入"售后方案"评分项)

**产物**:`output/outline.md`（仅 mode A Part 提纲）+ `output/scoring_matrix.csv`（第 6 列回填完成）

**完成标志**:用户确认 `outline.md` 合理且 `scoring_matrix.csv` 第 6 列回填正确,推进到阶段 4。**禁止**跳过本阶段。

---

### 阶段 4:分章节撰写

> **生成前必读**:`references/ai_output_rules.md` 的 **R1(不脑补)/ R2(不扩展字面输入)/ R3(中文无空格)/ R4(不扩展用户约束)/ R7(标题关键词反缝合句作弊)** 规则。

**目标**:为 `production_mode==A` 的 Part 逐章撰写正文。基于 `outline.md`（章节骨架）+ `scoring_matrix.csv`（评分项归属与撰写指引）+ `tender_brief.md`（项目事实）三份输入,产出 `chapters/{part_id}/chapter_NN_中文名.md` 章节文件,通过 `append_chapter.py` 追加到 docx 终稿。

**操作**:

**Step 1 — 生成 docx 正文容器**:
1. 调用脚本:
   ```
   ./run_script.bat docx_builder.py --section-only --out "projects/{项目名}/output/tender_response.docx"
   ```
   脚本生成仅含样式、页边距和列表样式预激活的空白正文容器。不包含封面、目录、页眉页脚——这些由后续整标合并器统一处理。

**Step 2 — 创建 chapters/ 目录**:
2. 按 Part 分子目录:
   ```
   output/chapters/
   └── {part_id}/           # 只为 production_mode=A 的 Part 建目录
       ├── chapter_01_整体方案.md
       ├── chapter_02_xxx.md
       └── ...
   ```
   命名规则:
   - 子目录名:`{part_id}`(与 `response_file_parts.id` 一致)
   - 文件名:`chapter_NN_中文名.md`(NN 两位数字,与 outline.md 章节编号对齐;中文名与 outline.md 章节标题一致,去前缀编号)

   **章节编号体系**:
   - 主干章节:一级用阿拉伯数字（`1` `2`，由 outline.md 自动编号）
   - 评分项响应章节:一级用 `二.N`（与 outline.md 一致）
   - 章节内部:用 `N.M` / `N.M.K` 多级阿拉伯数字
   - 不使用中文序号（一、二、三）作为章节编号（避免与主干采购需求原文序号冲突导致双重编号）

**Step 3 — 逐章撰写(核心)**:

   **输入文件清单**:
   撰写前必须同时打开三份输入(缺任何一份不许开始写):
   - `outline.md`:章节骨架(主干 + 评分项响应章节两段式)
   - `scoring_matrix.csv`:第 1 列(评分项归属)+ 第 5 列(关键词)+ 第 9 列(撰写指引)
   - `tender_brief.md`:项目事实(项目背景/采购需求/资格要求等)

   撰写指引不嵌入 `outline.md`(避免臃肿),AI 必须主动读 CSV 第 9 列。

   **写作前 Part 边界声明**:
   每章 markdown 文件开头必须含 Part 边界声明(HTML 注释):
   ```
   <!-- Part 边界声明 -->
   <!-- 本章属于:{Part 名称}(part_id: {part_NN}) -->
   <!-- 生产模式:A(文本生成) -->
   <!-- 语言体系:技术语言(实现语言),非商务语言(承诺语言) -->
   <!-- 严禁:跨 Part 串语言,严禁把商务承诺写到本 Part -->
   ```

   **章节标题关键词约束**:
   每条评分项对应的章节标题必须包含 `scoring_matrix.csv` 第 5 列的关键词(至少 1 个)。撰写完每章后 AI 自检,阶段 5 终审复核覆盖率。

   **主干 + 响应嵌入融合**:
   `outline.md` 输出主干段 + 评分项响应段两段式,AI 撰写时融合:
   - 评分项响应章节按内容相关性嵌入到主干对应小节后
   - 嵌入后:主干小节标题不变,评分项响应章节作为下一级标题紧随其后
   - `[待 AI 阶段 4 重组]` 占位标记届时移除

   **篇幅基准**（仅适用于 `production_mode==A` 的 Part）:
   - **锚点**：该 Part 总篇幅 ≈ 投标金额（万元）× 1 页 A4。例：本项目 80 万 → 技术响应方案 ≈ 70-80 页 A4
   - **章内页数分配**：按评分项分值占比。例：技术服务 20 分 / 技术评分总 50 分 → 占约 40% → 80 × 40% ≈ 32 页
   - **单页字数按章节类型分档**：
     - 偏文字章节（项目理解/售后方案）：700 字/页
     - 图表章节（技术架构/数据采集与建模）：600 字/页
     - 表格密集章节（质量保证/实施进度/验收）：500 字/页
   - **系数基准**：上述系数基于小四字体、1.5 倍行距、A4 页面、2.54cm 边距的标准版式估算。若项目招标文件强制要求四号字体，实际每页字数约降低 20%（即乘 0.8），当前工具链不对字号做自动换算，使用者需自行在产出后核对字号与页密度匹配
   - **章节类型判别**：依据 `count_words.py` 输出的表格行占比——≥60% 表格密集，30-60% 图表，<30% 偏文字
   - **字数目标计算**：目标字数 = 目标页数 × 档位字数。例：二.3 质量保证 16 页 × 500 字/页 = 8000 字；二.2 技术服务 32 页 × 600 字/页 = 19200 字
   - **不适用范围**：其他生产模式的 Part 无篇幅概念，按格式要求即可

   **取档策略证据落地**:
   撰写指引"取档策略"中列出的证据形式(架构图/对比表/分配表)必须在章节中逐项落地,不能只以占位图形式出现。例:撰写指引要求"渲染框架对比表",章节中必须出现真实对比表内容,不能只标占位。

   **履约前置条件不写免责句式**:
   配套设施依赖、环境依赖、第三方协作等前置条件,不得用免责句式。
   - 错误:"本方案前提是甲方提供配套硬件,如未提供导致..."
   - 正确:"本方案实施前,投标方将与甲方核查现场配套硬件状态;若需补充,投标方承担..."

   **assets 空库处理**:
   `assets/` 目录空时,严禁编造业绩/客户/金额/证书等硬数据。用占位符:
   - 图:`**【图 N.M:图标题】**`(单独一行,加粗)
   - 表:正常 markdown 表格,内容字段填【待补充】
   - 业绩:`**【案例待补充:{案例特征描述}】**`

   **章节完成后自检（硬约束）**:
   每章 markdown 撰写完成后,必须跑 `check_chapter.py` 自检:
   ```
   ./run_script.bat check_chapter.py projects/{项目名}/output/chapters/{part_id}/chapter_NN_中文名.md --brief projects/{项目名}/output/tender_brief.json --matrix projects/{项目名}/output/scoring_matrix.csv --tech-score 50 --pages 80
   ```
   自检含 5 类检查（Part 边界声明 / 标题关键词覆盖 / 字数 / 图占位符 / 履约句式）。
   任何"失败"项必须当场修复并重新自检,不得先追加 docx 或提交 review。
   检查通过后,章末保留自检注释作为记录:
   ```
   <!-- check_chapter.py 自检: 通过 -->
   <!-- 字数: N / 目标: M（章节类型 T） -->
   <!-- 图占位符: N 个 -->
   <!-- 覆盖评分项: R0N -->
   ```

3. **每次只写一章**。写完后追加到主文档(见 Step 4)。写下一章前,必须先口头汇报:
   - 本章覆盖了 `scoring_matrix.csv` 的哪几行
   - 是否有本地化信息需要用户确认
   - 是否引用了 `references/phrase_library.md` 的话术
4. 涉及本地化的段落,必须在写完后**单独**列出"待用户复核的本地化事实",由用户逐项确认或修正。

   **协作节奏硬规则(v2 新增)**:
   - **评分占比 Top 2 的 A 模式章节必须单独 review,禁止批量节奏跳过**。Top 2 的判定:读 scoring_matrix.csv 第 3 列分值,取最高两项归属 Part 为 A 模式的章节。(本项目示例:服务方案 25 分 + 工作计划 14 分)
   - 这两章写完后停下,让用户逐章 review,不得以"用户选 C 一口气写完"为由合并。
   - 其余评分章节(单项分值 ≤ 15 分)允许合并 review(用户可选 B 模式"批量 2-3 章停一次"或 C 模式"一口气写完最后 review")。
   - 非评分章节(项目理解 / 团队配置 / 研究方案主体等)按合并 review 处理即可。
   - AI 每次启动阶段 4 撰写前,必须先计算 Top 2 清单并口头汇报给用户,获得"Top 2 按单独 review"的默认确认后再开工。

5. 严禁:
   - 一次性输出多章内容(Top 2 A 模式章节绝对禁止批量节奏合并)
   - 在未读 `scoring_matrix.csv` 的情况下凭印象撰写
   - 使用"该地区资源丰富"之类的通用空话
   - 扩展用户字面输入(见 `references/ai_output_rules.md` R2)
   - 扩展用户范围约束(见 `references/ai_output_rules.md` R4)

**Step 4 — append_chapter.py 追加 docx(强制)**:
6. `append_chapter.py` 在阶段 4 为**强制工具**,不是可选。每写完一章 markdown **立即追加**,不要积累多章后批量追加。命令(必填全部参数):
   ```
   ./run_script.bat append_chapter.py "projects/{项目名}/output/tender_response.docx" "projects/{项目名}/output/chapters/{part_id}/chapter_NN_中文名.md"
   ```

**产物**:`output/tender_response.docx`(每章追加后都让用户 review)+ `output/chapters/{part_id}/` 全部章节 markdown

**完成标志**:所有 `production_mode==A` 的 Part 全部章节撰写完毕,各章 Part 边界声明 + 标题关键词约束 + 取档策略证据三项 AI 自检通过。推进到阶段 5。

---

### 阶段 4-C:C 模式 Part 产出(按 sub_mode 分流)

> **生成前必读**:`references/ai_output_rules.md` 的 **R6(模板段落 verbatim 来自招标文件,变量描述不含虚构示例)/ R8(filled.docx 不含 __PENDING_USER__ 等占位符字面,改为"【待填:字段描述】")** 规则。

**Step 0 · 确认投标主体(v2 补丁 1)**:C 模式 Part 填充前必须确定 `extracted.bidding_entity`(companies.yaml 的 own 主体 id)。流程:

- `c_mode_run.py` 启动时会自动触发 `select_bidding_entity.py`,不需额外手工步骤
- 单主体场景:自动选中
- 多主体场景:交互模式 stdin 选择;非交互必须带 `--entity-id <id>` 显式指定
- **AI 不得代替用户选择主体**(CLAUDE.md 红线 6)。多主体下无指定 id 时停下等用户

**适用范围**:`tender_brief.json` 中 `production_mode=='C'` 的 Part。本节独立于阶段 4(A 模式的章节撰写)。

**目标**:按 `response_file_parts[i].sub_mode` 产出对应形态的 Part 交付物。

**分流依据**:sub_mode 三类:

- **C-template**:产出 `template.docx` + `variables.yaml` + `intermediate.json` + `filled.docx` 三件套。filled.docx 作为 docx 片段供整标合并器并入主响应文件。
- **C-reference**:产出 `instructions.md`(YAML front matter + markdown 正文)单文件。由外部系统(电子采购平台)生成 filled 产物,工具链不产 docx 模板。
- **C-attachment**:**当前挂档**,遇到真实用例时启封设计,raise NotImplementedError。

**工具链命令行接口对所有 sub_mode 保持一致**:

```
# 分步(v1 时代的分步流程,保留可用)
./run_script.bat c_mode_extract.py --project <项目> --part <N> --extract-text
# AI 读 raw.txt 产出 intermediate.json
./run_script.bat c_mode_extract.py --project <项目> --part <N> --build-from-json <intermediate.json>
./run_script.bat c_mode_fill.py --project <项目> --part <N>

# 合并命令(v2 新增,推荐)
./run_script.bat c_mode_run.py --project <项目> --part <N>   # 单 Part
./run_script.bat c_mode_run.py --project <项目> --all         # 所有 C 模式 Part 批量
```

脚本内部按 sub_mode 分支;C-reference 的 `c_mode_fill` 仅做存在性校验不产 docx。此一致性是刻意保留,便于用户对所有 C 模式 Part 用同一组命令处理。

**v2 变更**:
- `c_mode_fill.py` 从交互式 `input()` 改为**非交互**:variables.yaml 中无法解析的变量(pending_user / manual)在 filled.docx 中写入"【待填:变量描述】"显式占位,用户在 Word 里搜索"【待填:"逐项替换即可。
- `c_mode_run.py` 新增一键合并:extract-text + build-from-json + fill 三步并为一条命令。`--all` 自动扫 `response_file_parts` 取 `production_mode==C` 的 Part 批量处理;跳过 intermediate.json 未产出的 Part 并在汇总中提示。
- 用户在 `companies.yaml` 中把 `__PENDING_USER__` 字段更新为实际值**一次**,所有 C 模式 Part 重跑 `c_mode_run.py --all` 就全部体现真实值,无需逐 Part 输入。

**sub_mode 判定**:

- 新项目:parse_tender.py 阶段 1 由 AI 按 `docs/business_model_v1.md` §8 #N20 判据为 production_mode=C 的 Part 判定 sub_mode,写入 `response_file_parts[i].sub_mode`(原 `brief_schema.SUB_MODE_JUDGE_PROMPT` 常量已在 v1 P2 清理中删除,迁移到 business_model §8 #N20)
- 已有项目:走 `migrate_brief_schema.migrate_v10_to_v11` 迁移(首次 sub_mode 写入属 V49bis 元信息层"从无到有",不触发 #N19 的完整重做)

sub_mode 判据:filled 产物去向(投标方视角);非判据:项目级 CA / 电子平台关键词(仅作 AI 判定时的上下文辅助)。

**执行者边界**(V49 + V49bis + #N19):

- 执行者(Claude Code 等)不得自行修改已产出的 template.docx / filled.docx / instructions.md / intermediate.json。发现问题停下反馈
- V49bis 允许用户显式决定后修改 variables.yaml 的元信息层(source/path/description/required)
- sub_mode 字段变更不属元信息层,触发该 Part 完整重做

**产物**:

- `output/c_mode/<part_name>/` 目录,按 sub_mode 产出对应文件集合
- C-template: intermediate.json + template.docx + variables.yaml + filled.docx
- C-reference: intermediate.json + instructions.md
- 所有 sub_mode 共享 raw.txt(extract-text 阶段产物)

**完成标志**:所有 `production_mode=='C'` 的 Part 的 sub_mode 对应产物齐备,用户 review 通过。

---

### 阶段 4-B:B 模式 Part 产出(材料组装)

**适用范围**:`tender_brief.json` 中 `production_mode=='B'` 的 Part。与阶段 4 / 4-C 并列。

**目标**:按 production_mode=B 的 Part,读招标文件 + 按 assets_provider 组装 docx。

**分流依据**:`manifest.yaml` 中 AI 判定的 `assembly_order[i].source_type`(三类参考值):

- **inline_template**:招标文件给模板 + 变量占位(如基本情况表、信誉声明) → 当前产占位段落,未来由 b_mode_fill 自动调 c_mode_fill 完成填充(留 V4)
- **asset_lookup**:从 assets 库查供应商素材(如资质证明、业绩合同) → 走 `AssetsProvider.lookup + resolve`;V3-1 起 `CuratedLocalAssetsProvider` 默认扫 `assets/<类别>/<company_id>/_raw/` 真实命中,缺省走 `PlaceholderAssetsProvider` 占位。⚠️ 当前实现:asset 注入 assembled.docx 走 OXML element 拷贝,**表格(含列宽)、段落级样式、字体保真(V4-1a)**。图片保真留 V4-1b;公章不做——签章(物理盖章 / 电子签章)是用户的法律动作,工具不代为生成,业绩合同 / 资质证书的公章页由用户投标前自行处理;扫描件保真待定。涉及上述未保真项时,使用者投标前需手工核对原件
   - **V4-skel V4-1b 结构层(2026-06)**:上述「图片保真留 V4-1b」期间,含图段落不再静默丢弃,改为整段跳过并在原位置插入显式可见占位段「[V4-1b 占位:此处缺 N 张证书图(源 ...),V4-1b 未自动搬运,投标前请人工放入原件]」,同时产 `output/b_mode/<part>/missing_elements.yaml` 记录含图段计数、表内含图(粗粒度)、sections 数。使用者投标前据占位段与该 sidecar 人工放入证书原件。实线图片保真(OXML 拷贝 + media part 复制 + relationship 注册)仍在 V4-1b 实现层,待真实含图 anchor + 人工目检驱动。
- **self_drafted**:供应商自撰(如开放资料) → 产占位段落 "[本节需供应商自撰: <title>]"

AI 遇到新形态可自造 source_type 值;b_mode_fill 遇未知值 raise ValueError 由用户 review 决定是否扩展工具链。

**Step 3 — AI 撰写 intermediate.json 的选材约束(V4-2a)**:

AI 写 intermediate.json 时,asset_lookup 类 Part 的选材不得凭招标文件原文盲写,必须基于以下三件源:

- `raw.txt` — 招标文件原文片段(本 Part 的撰写依据)
- `scoring_matrix_excerpt.md` — 本 Part 关联评分项的关键词 + 证据材料(评审看什么)
- `assets_inventory.json` — 库内候选清单(`enumerate_inventory()` 扫 assets 文件系统产出,每条含 category / company_id / filename / year)

约束:

- `asset_query.inventory_match` 必须从 `assets_inventory.json` 的候选条目中选中真实存在的一条,据三件源综合判断哪条候选最契合本 Part 的评分项证据材料要求。
- 库内无匹配候选(库空 / 无契合本 Part 评分项的候选)时,`inventory_match` 按 [`docs/manifest_schema.md`](docs/manifest_schema.md) 的 `asset_query.inventory_match` 占位规则标占位,不得盲写库内不存在的条目。
- 选材是 AI 的语义判断(脚本只产候选清单,不替 AI 选);AI 不得依赖脚本预筛或硬编码映射决定选哪条。
- 「为什么选这条」的理由撰写(rationale)不在本阶段,留 V4-2b。

**工具链命令行接口**:

```
# 分步(保留可用)
./run_script.bat b_mode_extract.py --project <项目> --part <N> --extract-text
# AI 读 raw.txt 产出 intermediate.json(含 assembly_order)
./run_script.bat b_mode_extract.py --project <项目> --part <N> --build-from-json <intermediate.json>
./run_script.bat b_mode_fill.py --project <项目> --part <N>
# 产出 assembled.docx + .pending_marker

# 合并命令(v2 新增,推荐)
./run_script.bat b_mode_run.py --project <项目> --part <N>   # 单 Part
./run_script.bat b_mode_run.py --project <项目> --all         # 所有 B 模式 Part 批量
```

**assets_provider 切换**:

manifest.yaml 顶部 `assets_provider` 字段控制本 Part 走哪个 Provider。详见 [docs/manifest_schema.md](docs/manifest_schema.md):

- `placeholder`(V61 基建,默认):所有 asset 查询返回占位,resolve 产占位 docx
- `curated_local`(V3-1 新增):扫 `assets/<类别>/<company_id>/_raw/` 找真实文件,_raw 优先 docx → pdf 走 pdf2docx 转换 → curated `.md` 兜底;多命中走 stdin 交互(`--non-interactive` 时按 `lookup_priority` 自动选);b_mode_fill 自动从 `brief.extracted.bidding_entity` 取 company_id

未来工作:`MCPExternalAssetsProvider`(对接外部材料库,V4+)。

**占位标记机制**:

assembled.docx 产出必附 `.pending_marker` 空文件,表示"占位状态,真实填充未完成"。用户真实填充完成后手工删除 marker。V45 整标合并器检测 marker → 占位照合入 final_response.docx + 列入 pending_manual_work.md。

**执行者边界**(V49 + V49bis + #N21):

- 不得自行修改已产出 assembled.docx
- 不得跳过 `.pending_marker` 机制(任何 B 模式产出都必须附带 marker,即使某段恰好是 self_drafted 的简短占位)
- 不得自造 source_type 就直接合入 b_mode_fill 代码(需用户 review 决定扩展)
- AI 判定与直觉不符时 raise 异常反馈

**产物**:`output/b_mode/<part_name>/{manifest.yaml, assembled.docx, .pending_marker}`

**完成标志**:所有 `production_mode=='B'` 的 Part 的三件套齐备,manifest 中 assembly_order 经用户 review。

---

### 阶段 5:合规终审

> **v2 新增**:本阶段在 `compliance_check.py` 之前,**必须先跑** `check_cross_consistency.py` 做跨章节一致性检查。两者互补,前者抓"承诺时间 vs 工期 / 团队成本 vs 预算 / 关键数字一致性"这类自相矛盾;后者抓"评分项覆盖 / 模板残留 / 格式"。
>
> ```
> ./run_script.bat check_cross_consistency.py projects/{项目}/output/tender_response.docx \
>     --brief projects/{项目}/output/tender_brief.json
> ```
>
> 输出:跨章节一致性报告(控制台打印)。有 `[失败]` 项必须修正后再跑 compliance_check。



**目标**:终审 `tender_response.docx`,产出 `compliance_report.md`。校验项:评分项覆盖率、★/▲ 条款响应、模板残留检测、格式合规、**标题关键词覆盖率**(#N12 新增)。

**操作**:

**Step 1 — 跑 compliance_check.py**:
1. 调用脚本:
   ```
   ./run_script.bat compliance_check.py "projects/{项目名}/output/tender_response.docx" "projects/{项目名}/output/scoring_matrix.csv" --out "projects/{项目名}/output"
   ```
   脚本自动从 `scoring_matrix.csv` 同目录检测 `tender_brief.json` 和 `chapters/` 目录。
2. 脚本输出 `output/compliance_report.md`,含六段校验:
   - 一、评分项覆盖度检查(评分项关键词在 docx 全文的匹配情况)
   - 二、★/▲ 条款响应检查(实质性响应条款是否有近邻响应表述)
   - 三、模板残留检查(XXX 公司/TODO/【待补充】等模板占位)
   - 四、格式检查(页边距/封面/目录/标题样式)
   - 五、标题关键词覆盖校验(**新增**:每条 mode A 评分项的关键词是否出现在章节 markdown 标题中)
   - 六、结论(汇总严重问题数)

**Step 2 — 用户 review compliance_report.md**:
3. review 焦点:
   - 评分项覆盖率 100%(任何缺漏立即回阶段 4 补写)
   - ★/▲ 条款全部明确响应
   - 模板残留为零
   - 标题关键词覆盖率 100%(任何 ✗ 项回阶段 4 改章节标题)
   - 篇幅符合金额换算基准(±20% 内)

**Step 3 — 失败项回流**:
4. 校验失败项不许放过。回流路径:
   - 标题关键词缺失 → 回阶段 4,改对应章节标题(添加缺失关键词)
   - 评分项覆盖缺失 → 回阶段 4,补章节
   - 篇幅不达标 → 回阶段 4,扩写或精简
   - 编造/模板残留检测命中 → 回阶段 4,删除问题内容

**产物**:`output/compliance_report.md` + 最终版 `output/tender_response.docx`

**完成标志**:`compliance_report.md` 全部校验通过,用户 review 通过。阶段 5 结束,`tender_response.docx` 可投递。

---

### 阶段 6:交付层导出(V71)

**适用范围**:工具链所有阶段完成后(含 V45 整标合并),投标前最后一步。

**目标**:把工具链内部产出(`output/` / `c_mode/` / `b_mode/` / `final_tender_package/`,英文命名 + 原格式)导出为中文命名 + Office 原生格式的用户交付层(`投标交付物/`),供投标当天直接使用。

**触发时机**:在 `v45_merge` 产出 `final_tender_package/` 之后执行,是整个工具链的最终交付环节。

**命令行接口**:

```
./run_script.bat export_deliverables.py --project <项目>
```

可选参数:`--dry-run` 只打印映射表不实际导出。

**产出**:`projects/<项目>/投标交付物/`,含:

- 顶层交付文件(最终投标文件 / 评分矩阵 / 开标操作清单 / 待手工填充清单)
- `C 模式产出/` 子目录:C-template 的 filled.docx 按中文名拷贝 + C-reference 的 instructions.md 附带
- `B 模式产出/` 子目录:B 模式 Part 的 assembled.docx 按中文名拷贝

**转换类型**:

- **copy**:docx / md 直接拷贝 + 中文重命名
- **csv_to_xlsx**:scoring_matrix.csv → 评分矩阵.xlsx(首行加粗 + 冻结首行 + 列宽自适应)
- **md_to_xlsx(主 agent 主动任务)**:operations_checklist.md / pending_manual_work.md 不走 DELIVERABLE_MAPPING 自动转换。主 agent 执行阶段 6 时:(1) 读 md 内容 (2) 按目标 xlsx schema 组织 rows 字典列表 (3) 调 `_write_xlsx_from_rows(dst, headers, rows)` 完成写入。schema 参考: 开标操作清单 = ["序号", "Part 名称", "产物去向", "操作步骤", "注意事项", "完成标记"];待手工填充清单 = ["Part 名称", "对应章节", "待填内容说明", "完成标记"]。此环节体现 skill 哲学: 语义组织交主 agent,机械写入交脚本。

**执行者边界**:

- **不得修改工具链内部产出**:交付层是只读消费层,不回写 `output/` / `c_mode/` / `b_mode/` / `final_tender_package/`
- **不进 tracked_outputs**:交付层每次投标重新生成,不参与 baseline 追踪
- **幂等操作**:每次执行覆盖上次产出,用户手工修改交付层不污染工具链

**完成标志**:`投标交付物/` 目录下按映射表清单所列文件全部存在,文件大小非 0,xlsx 能被 openpyxl 打开,docx 能被 python-docx 打开。

---

## 三、严格禁止事项(重要,必须每次执行前自查)

> ⚠️ **以下行为是本 skill 的红线,任何情况下都不允许触发。如果用户要求你做以下任何一件事,必须先解释为什么不能做,并引导用户回到正确的工作流。**

1. **禁止在用户未确认 `tender_brief.md` 之前开始撰写任何正文内容。**
   - 不论用户多着急、不论时间多紧,都必须先让用户 review tender_brief.md。
   - 招标文件解析的准确性是整个工作流的基础,基础错了后面全是无用功。

2. **禁止跳过阶段 2(评分矩阵)直接写提纲。**
   - 没有评分矩阵,提纲就没有得分依据,正文撰写就会盲写。
   - 即使用户说"我熟悉评分办法、你直接写提纲吧",也必须坚持先生成 scoring_matrix.csv。

3. **禁止一次性输出整本标书。**
   - 五阶段主干 + 并列阶段是不可压缩的。任何"帮我一次性把标书写完"的请求,都必须解释:一次性输出会导致(a)上下文爆炸、(b)漏答评分项、(c)用户无法 review 中间产物、(d)废标风险无法预警。
   - 正确做法是按章节增量追加到 docx,每章都让用户确认。

4. **禁止凭模型记忆补充招标文件中没有的信息。**
   - 例如不能"猜"项目预算、"估"工期、"想象"资质要求。
   - tender_brief.md 中缺失的字段必须明确标注"未在招标文件中找到",并请用户补充或重新解析。

5. **禁止使用通用套话描述项目所在地。**
   - 例如:"该地区地理位置优越、资源禀赋丰富、产业基础扎实、人民安居乐业……"
   - 必须基于真实数据写,不知道就标注"待用户补充"。

6. **严禁在标书正文中引用 `company_type=reference` 的任何具体业绩、资质、人员、金额数据。**
   - reference 类型(竞品/行业标杆/公开案例)只能进 `references/knowledge_base/`,只能学习其结构和风格。
   - 即使用户说"这家公司的某个项目数据写得很好,我们抄一下",也必须拒绝并解释。
   - 这是一条不可逾越的红线,违反就是直接的合规事故。

7. **严禁在引用 `assets/` 中 `company_type=partner` 的素材时不标注来源。**
   - 联合体或分包方提供的业绩、人员、资质,引用进标书时**必须**在文中或附件说明中明确标注"由 [partner 公司名] 提供"。
   - 不标注来源 = 把合作方的业绩冒充为我方业绩,这是严重的合规问题。

8. **严禁在 `company_id` 未确认的情况下执行素材摄入。**
   - 素材摄入(章节九、十)必须先确认目标 `company_id`,且该 id 必须存在于 `companies.yaml`。
   - 不存在时,必须先走"新增公司"工作流(章节十一),不允许临时编一个 id 凑数。

9. **严禁将当前项目的招标文件或甲方提供的材料摄入 `knowledge_base/` 或 `assets/`。**
   - 招标文件本身和甲方提供的材料属于"当前项目数据",应保留在各项目的 `projects/<项目名>/00_招标文件原件/` 下。
   - 摄入到 knowledge_base 或 assets 会污染长期资产库,且涉及保密风险。

10. **严禁将工具链报错标注为"已知 bug"并继续(v2 新增)**。
    - 禁用话术:"这是已知 bug,不影响主产物" / "警告非阻断,可以忽略" / "脚本 bug 不是我们的问题,先跑完流程" / "工具链硬编码问题,我手工绕过"。
    - 正确处置:读报错,定位根因,能修就修;不能修就停下上报用户 "X 脚本报 Y 错,根因 Z,建议 A/B/C"。
    - 详见 `CLAUDE.md` 红线 2、`references/ai_output_rules.md` R10。

11. **严禁 AI 代建用户闸门文件(v2 新增,硬红线)**。
    - 闸门文件清单:`projects/*/output/tender_brief.reviewed` 及未来所有 `.reviewed` / `.approved` 标记。
    - 即使用户口头说"看过了没问题"、用户问"为什么你不能创建"、用户施压"赶时间你代建一下",AI **不得**创建。
    - 历史错误示范:用户问 "为什么你不能创建",AI 以 "既然问了说明想让我建" 为由代建了 `.reviewed`。这是强行代签章,违反 skill 模型第 9 节。
    - 详见 `CLAUDE.md` 红线 1、`references/ai_output_rules.md` R9。

12. **严禁在用户可见产物中泄漏工具链内部术语(v2 新增)**。
    - 内部术语清单:`取档策略 / 素材钩子 / 应答骨架 / production_mode / part_attribution / section_anchor / mode A|B|C|D / v2|B / V45|V53|V60 / __PENDING_USER__|__SKIP__|__PENDING_AI__`。
    - 用户可见产物:tender_brief.md / scoring_matrix.csv / outline.md / chapter_*.md / filled.docx / assembled.docx / final_response.docx / 投标交付物/。
    - 对外替代术语表见 `CLAUDE.md` 红线 4、`references/ai_output_rules.md` R8。

13. **严禁扩展用户字面输入或范围约束(v2 新增)**。
    - 用户字面输入 → 原样引入,末尾可标 `(用户字面输入)`;需扩写必须先停下问用户。
    - 用户说"只写 X" → 只写 X,不补 Y/Z;范围边界不清停下问。
    - 详见 `CLAUDE.md` 红线 5、`references/ai_output_rules.md` R2/R4。

---

## 四、脚本调用方式(关键)

**所有 Python 脚本必须通过工作区根目录下的 `./run_script.bat` 调用,绝对不要直接 `python xxx.py`。**

原因:本 skill 自带一个隔离的 Python 虚拟环境(`tender-writer/.venv/`),所有依赖都装在这个 venv 里。直接调用系统 Python 会因为缺包而报错。`./run_script.bat` 会自动用 venv 里的 python 执行脚本,无需手动激活。

调用格式:
```
./run_script.bat <脚本名> <参数1> <参数2> ...
```

示例:
```
./run_script.bat parse_tender.py "D:\项目\xxx招标文件.pdf"
./run_script.bat build_scoring_matrix.py projects/{项目名}/output/tender_brief.json --out projects/{项目名}/output
./run_script.bat generate_outline.py projects/{项目名}/output/scoring_matrix.csv --out projects/{项目名}/output
./run_script.bat append_chapter.py projects/{项目名}/output/tender_response.docx projects/{项目名}/output/chapters/{part_id}/chapter_NN_中文名.md
./run_script.bat compliance_check.py projects/{项目名}/output/tender_response.docx projects/{项目名}/output/scoring_matrix.csv --out projects/{项目名}/output
./run_script.bat ingest_assets.py 业绩 own_default
./run_script.bat triage_unsorted.py
./run_script.bat add_company.py "某某科技有限公司" partner --alias "某某科技"
```

如果 `.venv` 目录不存在,./run_script.bat 会提示用户先双击 `install.bat` 准备环境。

---

## 五、参考资料速查

### 5.1 知识参考与模板

| 文件 | 用途 |
|---|---|
| `companies.yaml` | **公司注册表(集中事实来源)**,所有公司在这里登记,其他地方通过 id 引用 |
| `references/scoring_dimensions.md` | 政府项目四大评分维度的子项与应答要点 |
| `references/compliance_rules.md` | 常见废标原因和合规检查清单 |
| `references/doc_format_spec.md` | 中文标书标准排版规范 |
| `references/phrase_library.md` | 四大维度的高质量话术片段(待实战回填) |
| `references/knowledge_base/` | **学习参考材料库**(章节八),只学风格不进正文 |
| `templates/stage_samples/tender_brief.md` | 招标文件解读输出模板 |
| `templates/stage_samples/scoring_matrix.csv` | 评分矩阵 CSV 表头模板 |
| `templates/stage_samples/outline_template.md` | 标书提纲骨架 |

### 5.2 可调用素材库(写入正文的原料)

| 目录 | 用途 |
|---|---|
| `assets/公司资质/<company_id>/` | 资质证书结构化记录(章节七) |
| `assets/类似业绩/<company_id>/` | 项目业绩结构化记录(章节七) |
| `assets/团队简历/<company_id>/` | 团队成员简历结构化记录(章节七) |
| `assets/通用图表/<company_id>/` | 架构图/流程图/甘特图等的索引(章节七) |
| `assets/标准话术/<company_id>/` | 公司沉淀的高质量话术(章节七) |
| `assets/.ingest_history.json` | 摄入去重记录(sha256 → 处理时间) |

### 5.3 临时收件箱

| 目录 | 用途 |
|---|---|
| `_inbox_unsorted/` | 不确定分类的材料临时区,触发 triage 流程(章节十) |
| `assets/<类别>/<company_id>/_inbox/` | 已知分类但未摄入的材料临时区(章节九) |
| `references/knowledge_base/历史标书案例/_inbox/` | 待摄入的往期标书案例 |

---

## 六、与用户的交互模式

每次启动一个新的投标任务时,按以下顺序与用户对话:

1. 确认招标文件路径(如果用户没上传,主动询问)
2. 执行阶段 1,产出 tender_brief.md,**等待用户确认**
3. 执行阶段 2,产出 scoring_matrix.csv,**等待用户确认**
4. 执行阶段 3,产出 outline.md,**等待用户确认**
5. 进入阶段 4,**逐章**撰写,每章都让用户 review
6. 执行阶段 5,产出 compliance_report.md,根据报告补写或修正

**永远记住**:你的价值不在于"快",而在于"对"和"全"。一份漏答关键评分项的标书,即使写得再快也是废纸。

---

## 七、素材调用规则(主工作流阶段 4 撰写时使用)

阶段 4(分章节撰写)时,标书正文中所有具体的资质、业绩、人员、图表、话术,**都必须**从 `assets/` 中按公司归属挑选。本章规定挑选规则。

### 7.0 总体硬约束(贯穿所有子章节)

- ✅ **只引用 `review_status=approved` 的素材**。`pending` 视为未入库,即使存在也不允许引用。
- ❌ **严禁引用 `company_type=reference` 的任何具体信息**(reference 只在 `references/knowledge_base/` 出现,本来就不在 `assets/`)。
- ⚠️ **涉及 `company_type=partner` 素材时,必须在标书正文或附件说明中标注来源**(如"由 [partner 公司名] 提供")。

### 7.1 撰写资质章节

- **优先**从 `assets/公司资质/<own_company_id>/资质清单.md` 中挑选。
- partner 资质**原则上不引用**,除非:
  1. 当前是联合体投标
  2. 招标文件明确允许联合体成员资质合并计算
  3. 引用时在文中明确标注 "联合体成员 [partner 公司名] 提供:..."
- 阶段 5 终审会自动检查 `有效期至` 字段,**过期或临期(< 30 天)的资质会被标红**。

### 7.2 撰写业绩章节

- **优先**从 `assets/类似业绩/<own_company_id>/业绩列表.csv` 中按"行业 + 规模 + 地区 + 技术"四维筛选,挑 3-5 个最相关的深读对应 .md 后展开。
- 联合体投标时可从 `assets/类似业绩/<partner_company_id>/` 筛选,**引用时必须**在业绩表的"备注"列或图注中标注 "由 [partner 公司名] 提供"。
- 🔴 **严禁**从 `references/knowledge_base/历史标书案例/` 中任何 `company_type=reference` 的案例提取业绩数据写入标书正文。这是高压线。
- 同样**严禁**从 `references/knowledge_base/` 中任何 `company_type=partner` 的案例提取未在 `assets/` 中登记的业绩数据。

### 7.3 撰写团队章节

- **只**从 `assets/团队简历/<own_company_id>/简历索引.csv` 挑选。
- 联合体情况下 partner 人员**必须**在文中明确标注"联合体成员 [partner 公司名] 派出"。
- 阶段 5 终审会自动检查证书有效期,**过期或临期证书会被标红**。
- 招标文件如有"项目经理必须持有 xxx 证书"的硬性要求,在撰写时直接对照 `关键证书` 字段验证。

### 7.4 引用通用图表

- 从 `assets/通用图表/<own_company_id>/图表索引.md` 中按"适用维度 + 适用项目类型"筛选。
- ⚠️ **架构图、流程图必须根据本项目业务模块名称重新调整**,严禁原样复用其他项目的图(评委一眼能看出"通用 PPT")。
- partner 提供的图表,引用时图注必须标注 "图源:[partner 公司名]"。
- 图注使用 `docx_builder.py::add_figure_caption` 自动 SEQ 编号。

### 7.5 引用标准话术

- 从 `assets/标准话术/<own_company_id>/话术索引.md` 中按"适用维度 + 适用场景"筛选。
- ⚠️ **必须本地化改写**,严禁原样复制粘贴。话术库提供的是"骨架",不是"成品"。
- 话术中涉及具体项目/数据/人员的占位符(如 `[项目名]`、`[XX 万元]`),**必须**替换为本项目的真实数据。

---

## 八、知识库利用(主工作流阶段 3-4 使用)

撰写阶段 3(提纲)和阶段 4(正文)前,**必须**先扫描 `references/knowledge_base/` 吸收上下文。

### 8.1 扫描历史标书案例

1. **不直接读正文**,先扫描 `references/knowledge_base/历史标书案例/` 下所有 .md 的 frontmatter。
2. 按 "项目类型 + 预算量级 + 行业" 与当前项目匹配,挑 1-3 份最相关的**深读**。
3. **吸收**:章节结构、应答策略、话术风格。
4. **严格禁止**:
   - 🔴 严禁复制任何 `company_type=reference` 案例的具体业绩、资质、人员、金额信息
   - 🔴 严禁复制 `company_type=partner` 案例中未在 `assets/` 中登记的素材
   - ⚠️ `company_type=own` 案例可作为结构和话术参考,**但不能整段复制**——具体素材应到 `assets/` 取

### 8.2 扫描其他子目录

同时浏览以下子目录,吸收与当前项目相关的内容:

- `references/knowledge_base/评标专家偏好/` —— 调整章节笔墨权重,把评委关注的点写得更扎实
- `references/knowledge_base/行业术语对照/` —— 确保正文术语符合本行业规范,避免"外行话"
- `references/knowledge_base/失败教训/` —— 在阶段 5 合规终审中作为额外检查项

---

## 九、辅助工作流:素材摄入(已知分类)

### 9.1 触发条件

用户**明确说出**类别和公司归属。例如:
- "处理业绩 inbox"(默认 own_default 公司,如有歧义需确认)
- "处理 own_jiao 公司的简历 inbox"
- "处理 partner_xinda 的资质 inbox"
- "把 _inbox 里的东西摄入"(必须先确认类别和公司)

### 9.2 执行步骤

**首选方式:调用现成脚本 `ingest_assets.py`,自动完成 a-g 全部子步骤。**

```
./run_script.bat ingest_assets.py <类别> <company_id>
# 例:./run_script.bat ingest_assets.py 业绩 own_default
# 类别支持中文(资质/业绩/简历/图表/话术)或英文别名(qualification/performance/resume/chart/phrase)
```

脚本会自动:
- 校验 `company_id` 存在于 `companies.yaml`(不存在则报错并提示走"新增公司"流程)
- 拒绝 `company_type=reference` 的公司(reference 不能进 assets 摄入流程)
- 遍历 `_inbox/` 下每个文件,自动跳过 `.gitkeep`
- 调用 `extract_text.py` 提取文本和 sha256
- 检查 `.ingest_history.json` 去重,重复文件跳过并在报告中列出
- 按 schema 生成结构化 .md(`company_id` / `company_type` 从目录推断,`review_status=pending`,缺失字段标 `TODO:待人工确认`)
- 追加索引行到对应 CSV 或 markdown 索引表
- 把原文件移动到 `_raw/`,文件名加时间戳前缀 `YYYYMMDD_<原文件名>`
- 更新 `.ingest_history.json`
- 输出"处理成功 / 重复跳过 / 处理失败"统计 + 每条新生成 .md 的 TODO 字段清单

**AI 在脚本跑完后必须做的事(脚本不能替代):**

1. **逐个 review** 新生成的 .md,补全脚本无法自动推断的 TODO 字段(尤其是甲方单位、合同金额、关键技术等关键字段——脚本只是用正则做粗糙的提取,该校验的还要校验)
2. **检查事实性**:脚本生成的字段是从原文里"猜"的,可能猜错。AI 应当通读 `_raw/` 下的归档原文,核对 frontmatter 是否真实
3. **不允许直接把 review_status 改为 approved**——这一步必须等用户人工确认后由用户或 AI 在用户明确指示下操作
4. 如果脚本报"处理失败",查看失败原因。最常见的是 .doc 旧格式不支持,需要用户先用 Word 另存为 .docx 后再放入 inbox

**手工兜底**:如果脚本因某种原因不可用(例如 Python 环境异常、用户在方式三纯对话 AI 下使用),AI 必须按以下手工步骤完成等价工作:

a. 通过 `./run_script.bat extract_text.py "<文件路径>"` 提取文本和 sha256(或在方式三下让用户手工提供文本)
b. 读取 `assets/.ingest_history.json`,**检查 sha256 去重**
c. 读取同类的 `<类别>schema.md`(业绩 schema / 简历 schema / ...)
d. **严格按 schema 输出结构化 .md**(`company_id` / `company_type` 从目录推断,`review_status=pending`,缺失字段标 `TODO:待人工确认`,文件末尾追加 `## TODO 清单`)
e. **追加索引**:业绩/简历追加一行到 CSV,资质/图表/话术追加一行到 .md 索引表(每行冗余 `company_id` 和 `company_type`)
f. **归档原文件**:从 `_inbox/` 移动到 `_raw/`,加时间戳前缀
g. **更新 `.ingest_history.json`**

**摄入完成后的报告必须包含**:
- ✅ 处理清单:本次摄入的所有文件
- 📂 生成路径:每份文件对应的目标 .md 路径
- ⏭️ 跳过清单:因 sha256 重复而跳过的文件
- 📋 TODO 清单:汇总所有待人工确认的字段
- 👀 待 review 清单:所有 `review_status=pending` 的新增条目

### 9.3 摄入完成后的人工动作

提醒用户:
- 逐个 review 新生成的 .md,补全 TODO 字段
- 把 `review_status` 从 `pending` 改为 `approved`
- 删除 .md 末尾的 `## TODO 清单` 区块
- **只有 `approved` 状态的素材才能被新标书引用**

---

## 十、辅助工作流:分类 triage(未知分类)

### 10.1 触发条件

用户的描述**含混或不确定分类**。例如:
- "处理 _inbox_unsorted"
- "我有一堆材料不知道怎么分类"
- "这堆东西里有简历有业绩有合同,你帮我分一下"

### 10.2 执行步骤

**首选方式:分两步调用 `triage_unsorted.py`,先看建议、再执行分发。**

```
# 第一步:只看建议,不分发(默认行为)
./run_script.bat triage_unsorted.py

# 第二步:用户确认建议后,再执行分发(会触发已知分类摄入流程)
./run_script.bat triage_unsorted.py --apply
```

第一步会:
- 扫描 `_inbox_unsorted/` 下所有非 `.gitkeep` 的文件
- 对每份文件调用 `extract_text.py` 提取文本
- 用关键词规则推断**目标类别**(业绩 / 简历 / 资质 / 历史案例 / 图表 / 话术)
- 通过文本和文件名匹配 `companies.yaml` 中已注册公司的名称和别名,推断**目标公司**
- 输出分类建议清单(每条含类别、公司、判断理由、目标路径)

**🔴 不允许直接执行 `--apply` 而跳过用户确认。** 必须先让用户逐条 review 第一步的建议:

- 类别建议是否准确(脚本只是基于关键词,可能误判)
- 公司归属是否正确(尤其是脚本未识别到公司归属时,显示为"【待确认】")
- 是否有新公司需要先注册(若有,触发章节十一"新增公司"工作流)

第二步 (`--apply`) 会:
- 对 `own` / `partner` 类别:把文件副本放入对应 `assets/<类别>/<公司>/_inbox/`,然后**自动触发** `ingest_assets.py` 完成已知分类摄入流程
- 对 `历史案例` / `reference` 类别:把副本放入 `references/knowledge_base/历史标书案例/_inbox/`(🔴 **严禁**进入 `assets/`)
- 公司归属未识别的文件**会被脚本跳过并标记为"未识别公司归属"**——这是预期行为,要求用户先注册公司后再重跑
- 原文件移动到 `_inbox_unsorted/_raw/`,文件名加时间戳前缀

**AI 必须做的事(脚本不能替代):**

1. **第一步建议输出后立即停下,与用户对齐**——脚本不会停下问你,但 AI 在 SKILL 工作流下必须停下确认
2. **关键词规则会有误判**——例如一份"投标文件"可能是 own/partner 的历史案例,也可能是 reference 的竞品分析,需要 AI 结合文件来源判断
3. **公司未识别时的处理**:脚本会在 `--apply` 中跳过未识别公司的文件。AI 应主动询问用户"这份文件应归属哪家公司?",必要时先走"新增公司"流程
4. **生成 triage 报告**:在脚本输出之外,AI 还要给用户写一份易读的总结报告,列出每份源文件被拆分到的所有目标位置(一份源文件可能产生多个目标 .md)

### 10.3 严格禁止(高压线,违反即停止)

- 🔴 **严禁未经用户确认就自动分类**
- 🔴 **严禁把任何材料默认归为 own**(必须明确询问公司归属)
- 🔴 **严禁把 `company_type=reference` 的材料写入 `assets/`**(只能进 `references/knowledge_base/`)
- 🔴 **对公司归属有任何不确定时,必须主动询问用户**,不允许"猜"
- 🔴 **严禁将招标文件本身或甲方提供的项目材料**(无论 own / partner / reference)摄入 `assets/` 或 `knowledge_base/`——这些是项目数据,应保留在 `projects/<项目名>/00_招标文件原件/` 下

---

## 十一、辅助工作流:新增公司

### 11.1 触发条件

- 用户说"新增公司"、"注册一家新合作方"、"加一个 partner"等
- 在执行其他工作流(尤其是章节九摄入和章节十 triage)时,检测到引用了 `companies.yaml` 中**未注册**的公司

### 11.2 执行步骤

1. **询问用户**:
   - 公司**全称**(必填)
   - 公司**简称 / 别名**(选填,作为 `aliases`,可有多个)
   - **类型**:own / partner / reference(必填,务必让用户明确选择)
   - 简要**描述**(选填)

2. **调用脚本完成注册和目录初始化**:

   ```
   ./run_script.bat add_company.py "公司全称" <own|partner|reference> [--alias 别名] [--description 描述] [--id 自定义id]
   # 例:./run_script.bat add_company.py "信达科技有限公司" partner --alias 信达
   ```

   脚本会自动:
   - 基于公司全称(优先用拼音,fallback 到 ASCII / sha1)生成简短 id,前缀按类型区分:`own_xxx` / `partner_xxx` / `ref_xxx`
   - 检查 id 是否已存在,冲突时自动加序号
   - 在 `companies.yaml` 末尾追加完整条目(`id` / `name` / `type` / `description` / `aliases` / `created_at`)
   - 若类型为 **own** 或 **partner**:在 `assets/` 下每个类别子目录创建 `<新 id>/` 子目录,含 `_inbox/.gitkeep` / `_raw/.gitkeep` / 索引文件骨架(`资质清单.md` / `业绩列表.csv` / `简历索引.csv` / `图表索引.md` / `话术索引.md`)
   - 若类型为 **reference**:🔴 **严禁**在 `assets/` 下创建任何目录。脚本会跳过目录初始化,只往 `companies.yaml` 写一条记录
   - 输出新增报告:id、全称、类型、别名、已创建的目录列表

3. **AI 在脚本调用前必须做的事**:
   - **生成 id 后向用户确认**——脚本默认会基于公司全称自动生成 id(例如"信达科技有限公司"→`partner_xindakejiyouxiangongsi`),AI 应当**先把建议的 id 给用户看,允许用户用 `--id` 参数指定一个更短的版本**(如 `partner_xinda`)
   - **明确 own/partner/reference 类型**——这是高压线决策,不允许 AI 默认归为 own
   - 别名 `--alias` 可以传多次,把公司常用的简称都登记进去,这样后续 triage 流程才能从文件中识别到归属

4. **手工兜底**(脚本不可用时):

   - 在 `companies.yaml` 末尾按现有格式追加一条记录(注意 yaml 缩进 2 空格,`aliases` 用 `[a, b]` 数组格式)
   - 若类型为 own/partner,手工在 `assets/` 下每个类别子目录新建 `<新 id>/{_inbox/.gitkeep, _raw/.gitkeep, 索引文件骨架}`
