# tender-writer 常见问题

> 本文档持续累积。每当新问题被沉淀成有可验证答案的解答,补进这里。

## Q1: 为什么 `.reviewed` 闸门文件不能由 AI 代建?

`.reviewed` 是你对 `tender_brief.md` / `tender_brief.json` 核对通过的凭证。`tender_brief.md` 是后续四个阶段(评分矩阵、提纲、撰写、合规终审)的唯一事实来源——如果里面预算、工期、★/▲ 条款有错,后面全错。AI 代建 `.reviewed` 会让这个标记失去"人工核对通过"的保障意义。

这是 `CLAUDE.md` **红线 1**(AI 不得代建用户闸门文件)。AI 收到的所有形式的代建请求,包括:

- "我看过了,你帮我建一下"
- "为什么你不能建"(确认机制,不是授权)
- "时间紧,你先建"
- "下游脚本卡住了"

一律拒绝。正确流程是你在 IDE 或终端里手动 `touch projects/<项目>/output/tender_brief.reviewed`,AI 再推进下游工具链。下游脚本(`build_scoring_matrix.py` / `generate_outline.py` / `c_mode_fill.py` / `compliance_check.py` 等)都有 `require_reviewed_for_brief` 函数级闸门,缺标直接硬失败退出。

## Q2: `install.bat` 报错怎么处理?

常见两类根因:

1. **Python 不在 PATH / 版本不对**(典型报错:`python 不是内部或外部命令` / Python 版本 < 3.10):先在 PowerShell 或 cmd 里确认 `python --version` 返回 3.10+。若没装,去 python.org 下载 3.11 安装包,安装时勾选 "Add Python to PATH"。

2. **pip 下载依赖超时(网络问题)**:`install.bat` 内部走 `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`(清华镜像)。若仍超时,确认企业代理不拦截 pypi,或手动在 PowerShell 里跑一次 `pip install -r requirements.txt --proxy http://<你的代理>:<端口>`。

若上述两类都不符,先检查 `install.bat` 文件编码是否为 UTF-8 without BOM(Windows 记事本"另存为"会加 BOM 导致首行解析失败)。

装完后确认 `.venv/` 目录出现且 `.venv/Scripts/python.exe` 能跑 `import pdfplumber, docx, docxtpl`。若缺包,重跑 `install.bat` 或手动补装。

## Q3: 我要把 `demo_cadre_training` 改造成真实项目,有哪些坑必须避开?

`projects/demo_cadre_training/README.md` 给了 4 步 clone/cp/rm/改的流程,这里列几个**不照做会踩的坑**:

1. **别用 `own_default` 投真实标**。`companies.yaml` 初始的 `own_default` 是占位条目(`status: placeholder`),`select_bidding_entity.py` 会自动跳过它。先跑 `./run_script.bat add_company.py "你公司全称" own --alias "你公司简称"` 注册真实 own 主体,否则下游 C 模式模板里的变量(法代、注册地址、营业执照号等)全部标成红色"【待填】"占位。

2. **`.reviewed` 闸门不能跳**。`build_scoring_matrix` / `generate_outline` / `c_mode_fill` / `compliance_check` 全部受 `require_reviewed_for_brief` 守卫,没建 `.reviewed` 直接硬失败退出。闸门必须你人工建,AI 不会代建(见 `CLAUDE.md` **红线 1**)。

3. **真实招标文件原件放在 `projects/<你的项目>/input/` 下,别放仓库根目录**。`.gitignore` 已默认忽略该路径(demo 是白名单例外)——把原件放到 `input/` 下,git 不会追踪;放到根目录或别处,就会进 commit。

4. **多家 own 主体时停下让你选**。若你 `companies.yaml` 有 ≥2 家合格 own,`select_bidding_entity.py` 会交互式让你选编号,AI 不会代选(见 `CLAUDE.md` **红线 6**)。非交互跑用 `--entity-id <id>` 明示,否则会报缺参数退出。

## Q4: 扫描版 PDF 招标文件怎么处理?

`parse_tender.py` 自 V3-6 起会**自动检测扫描版 PDF**(全文平均 < 50 字/页;实测文字版 PDF 平均 466~700+ 字/页,9× 安全余量)。命中扫描版时脚本退出码 2,提示三条用户路径。

**判别原理**:`pdfplumber.extract_text()` 只读 PDF 内嵌文字流,不识别图像像素。文字版 PDF(从 Word / WPS 直接导出)字符密度高;扫描版 PDF(纸质扫描成图)每页是图像,提取出 0 字符。

### 路径 1:本地 OCR(推荐技术用户)

```bash
pip install ocrmypdf
# 同时装 tesseract 系统级二进制 + chi_sim 中文语言包
ocrmypdf -l chi_sim "<原 PDF>" "<输出 PDF>"
# 用输出 PDF 重跑 parse_tender(无 fallback flag)
parse_tender.py "<输出 PDF>"
```

输出 PDF 是原图 + 文字层,既能跑 parse_tender 又保留扫描原图供人工核对。**该路径还能保留 PDF 表格结构**(extract_all_tables 在文字层可识别表格),其他两条路径不行。

### 路径 2:外部 OCR / AI 多模态服务(最便捷)

上传扫描版 PDF 到豆包 / 通义 / Claude / GPT 等多模态 AI,转纯文本:

- 提示词建议:"请把 PDF 完整 OCR 成纯文本,保留原章节编号、★/▲ 条款原文不修改"
- 把转出的纯文本存为 `<pdf_name>.txt`
- 跑:
  ```bash
  parse_tender.py "<原 PDF>" --ocr-text "<pdf_name>.txt"
  ```
- `--ocr-text` flag 让 parse_tender 跳过 PDF 文字提取,直接读 txt 当 raw_text

**重点**:OCR 错字率非零,tender_brief 阶段必须逐字核对 `tender_raw.txt` 与原 PDF——尤其 ★/▲ 条款数字、资质门槛数字、工期天数等关键字段。`.reviewed` 闸门在扫描版场景下权重更高。

### 路径 3:找原版文字 PDF(最稳妥)

联系采购方 / 招标代理,索要从 Word 直接导出的文字版 PDF。最大限度避免 OCR 错字误差,特别在★/▲ 条款数字 / 资质门槛 / 工期天数等关键字段。

### 为什么 V3-6 不内置 OCR

开源场景下用户 OCR 选型差异巨大(本地 ocrmypdf vs 外部 AI vs 商业 OCR),工具链不绑死单一路径。V3-6 只做检测 + 引导 + fallback 通道,OCR 由用户按场景自行选择。`requirements.txt` 不加 ocrmypdf,装 tesseract 是用户操作系统级别的事(Windows 装包要管理员权限,工具链不便代办)。

### 极简 PDF 误报边界

如果你的 PDF 真的只有 1-2 页且字数极少(平均 < 50 字/页),会被误报为扫描版。这种情况:

- 真实场景下 1-2 页 30 字的 PDF 无法当招标文件,误报有警示价值
- 如果你确认它不是扫描版,可以走路径 2:把 PDF 文本手抄成 txt,用 `--ocr-text` flag 绕过

### 限制

- 扫描版 + fallback txt 模式下,`extract_all_tables` 返回空表(txt 没有 PDF 表格结构)。tables 字段是辅助信息,不影响主流程
- 加密 PDF 也会被误报为扫描版(pdfplumber 对加密 PDF 提取空文本),需先解密

## Q5: `check_chapter.py` 报"正文级缝合句嫌疑",是误报怎么办?

**V3-4 新增的检查项 [8] 正文级缝合句**用滑窗算法扫:在 30 字内出现 ≥6 个评分项关键词的段落标 fail,≥5 个标 warn。这条规则的设计目的是抓 AI 撰写时为凑覆盖率把多个关键词硬塞进一句的"作弊段落",但**自然章节介绍句、综述段落**(如"本章涵盖响应时间、成果交付时间、售后服务三项内容")也可能命中。

如果你确认被命中段落是**合理的专业表述**(不是关键词堆砌作弊),三档处置:

1. **行级忽略(推荐单点误报)**:在被命中段落上方加一行 HTML 注释:

   ```markdown
   <!-- nolint:stitching -->
   本章涵盖响应时间、成果交付时间、售后服务三项内容。
   ```

   下次跑 `check_chapter.py` 会跳过该段。

2. **整章调阈值**(整章被多次误报):

   ```bash
   ./run_script.bat check_chapter.py <章节> --brief ... --matrix ... \
       --stitching-threshold-warn 6 --stitching-threshold-fail 7
   ```

   把阈值放宽 1 档。

3. **调窗口**(关键词分散但跨度小被命中):

   ```bash
   ./run_script.bat check_chapter.py ... --stitching-window 40
   ```

   把 30 字窗口拉宽到 40 字,关键词需更密集才命中。

**不建议**:把阈值无限往上调("调到不报错为止")。如果整体阈值要从 6/7 继续往 7/8 拉,说明可能是关键词集合太大(scoring_matrix 第 5 列关键词过密)或算法本身需要换思路(加连接词检测 / 句法分析),而不是参数调整能解决——遇到这种情况停下手工 review 章节,或在 git issue 反馈。

## Q6: 想重跑 `parse_tender` 取 demo 数据,怎么干净开始?

V3-3 baseline / 后续 V3-N+ 重跑 parse_tender 取 demo 数据时,直接跑 `parse_tender --force` 会覆盖 `tender_brief.json` 等产物,**留下 git diff**。手工 `git restore projects/demo_cadre_training/output/` 也行,但范围模糊(到底动哪些文件 / 是否动 .reviewed)。

V3-13 提供 `scripts/demo_reset.py` 标准化路径:

```bash
# 1. 预览(默认 dry-run,只显示要 restore 的文件)
./run_script.bat demo_reset.py

# 2. 确认执行
./run_script.bat demo_reset.py --yes

# 3. 跑 parse_tender --force(.reviewed 仍在,ensure_reviewed 闸门 pass)
./run_script.bat parse_tender.py \
    projects/demo_cadre_training/input/tender_demo.docx \
    --out projects/demo_cadre_training/output --force
```

**脚本行为承诺**:

- **只 restore git tracked 文件**(43 个,见 `git ls-files projects/demo_cadre_training/output/`)
- **不动** `tender_brief.reviewed`(标记不入 git,是用户机器本地凭证;红线 1 兼容)
- **不动** untracked 文件(用户手工放的实验性文件不会被清掉)
- **不调** `git checkout` / `git clean`(避免误删 / detach HEAD)
- **不重跑** `parse_tender`(只 reset,跑由用户)

**仅服务 demo_cadre_training 项目**——脚本 hardcode 路径,不接受 `--project` flag。真实项目用户自己 git restore 自己的 output/。
