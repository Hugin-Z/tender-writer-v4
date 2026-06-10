# plans/v4-1a-fix-normalize.md — V4-1a fixture 对齐 + 字号归化

## 背景

V4-1a Phase 3 目检发现两件事,实测(Phase 0)查清根因:

1. 标题"业绩证明文件"蓝色 —— 根因 = 测试夹具 _inject_anchor_to_tmp_doc 未调 apply_default_styles,跟生产路径(b_mode_fill._main_body 调了)脱节。python-docx 默认 Heading2 是 accent1 蓝(4F81BD),apply_default_styles 把它改黑;生产端 Heading2 实测已是黑色(demo assembled.docx 验证)。蓝色仅是测试夹具假象,非产品行为。修法:夹具补 apply_default_styles 对齐生产。

2. 注入内容字号跟 master 不一致 —— 源 run 级 sz=24(12pt)/ szCs=21(10.5pt),master Normal 14pt。裁定(可能二·窄):归化字号 sz/szCs 让其回落 master,段间距/缩进保留源(中文排版的缩进/行距可能是合理的,不归化),字体 rFonts(V4-1a.6 补的显式宋体/Times New Roman)和强调 b/i/u 不剥。

这是 V4-1a 收尾(主 5 commit + 字体 fix 2 commit 均未 push)。本次作为 V4-1a.8/.9 延续 commit,跟前 7 个一起 push。

## scope 边界(钉死)

动:
- scripts/tests/test_b_mode_v4_1a.py(夹具 _inject_anchor_to_tmp_doc 补 apply_default_styles + 加字号归化测试 case)
- scripts/b_mode_fill.py(新增字号归化 helper + 调用)
- docs/changelog.md(更新 V4-1a entry:补 fixture 对齐 + 字号归化说明)
- plans/v4-1a-fix-normalize.md(本文件,入仓)

不动(越界即停下报告):
- master 端配置(docx_builder DEFAULT_STYLES / apply_default_styles / master styles/theme)—— 生产端 Heading2 已黑、字号已 master,不改 master
- rebind 逻辑 / 字体 fix 逻辑(_rebind_or_strip_refs / _apply_explicit_fonts_to_runs 不改)
- 段间距 spacing / 缩进 ind(裁定窄:保留源,不归化)
- 强调 b/i/u(尺度乙:保留)
- 字体 rFonts(V4-1a.6 成果,绝不剥 —— 剥了 MS 明朝 fallback 回来)
- 表格 tblGrid 列宽(内容结构,保留)
- 图片/页眉页脚/公章/provider/asset_query schema/其他 sub_mode/handbook

完成判定:6 条(见自检方式)。

## 子任务 + commit 序列

| # | commit message | 文件 |
|---|---|---|
| 8 | `V4-1a.8 测试夹具对齐生产:_inject_anchor_to_tmp_doc 补 apply_default_styles 消假蓝色` | test_b_mode_v4_1a.py |
| 9 | `V4-1a.9 字号归化:剥源 run 级 sz/szCs 回落 master,保留字体/强调/段距/缩进` | b_mode_fill.py / test_b_mode_v4_1a.py / docs/changelog.md / plans/v4-1a-fix-normalize.md |

2 commit。V4-1a.8 修 fixture bug(独立、先修、让目检假象消除)/ V4-1a.9 字号归化实现+测试+文档收尾。

## 实现指令(Phase 2 据实参照)

### V4-1a.8 — fixture 对齐生产

在 test_b_mode_v4_1a.py 的 _inject_anchor_to_tmp_doc 里,dst_doc = Document() 之后补 apply_default_styles(dst_doc)(import from docx_builder),跟生产路径 b_mode_fill._main_body 一致。
- 落盘后重生成 injected docx,确认标题 Heading2 变黑(实测 <w:color w:val="000000"> 或无 color 回落 master 黑)
- 这一步只改测试夹具,不碰生产代码;生产端本就黑,无需改

### V4-1a.9 — 字号归化 helper

新 helper(命名实测确认风格,如 _normalize_run_size):
- 遍历搬入 element 每个 <w:r> 的 <w:rPr>:删除 <w:sz> 和 <w:szCs> 子元素(让字号回落 style/master Normal)
- 不动 <w:rFonts>(字体,V4-1a.6 成果)、不动 <w:b>/<w:i>/<w:u>(强调)、不动 pPr 的 <w:spacing>/<w:ind>(段距缩进,裁定窄保留)
- 段落级若有 sz 也同理(实测确认 sz 是否出现在 pPr/rPr 之外,按实测处理)
- 返回剥了多少处
调用点:_handle_asset_lookup 内,在 _apply_explicit_fonts_to_runs 之后(顺序:deepcopy → rebind → 补字体 → 归化字号)
方式:删标签让其回落 style 系统(不覆盖成 master 值字面 —— 删更干净,依赖回落机制,跟字体 fix 的"仅不存在才 set"是互补的两种归化手法,各自适用:字体怕 fallback 所以显式 set,字号靠 master style 兜底所以删)

边界要点:
- 只删 sz/szCs,不碰 rFonts/b/i/u/spacing/ind —— 删错会推翻字体 fix 或抹掉强调/合理排版
- 删的是搬入 element 副本,不动源

### 测试 + changelog

test_b_mode_v4_1a:
- V4-1a.8 后:夹具产物标题 color 实测(黑/回落,不再蓝 4F81BD)
- V4-1a.9 加 case:注入后搬入 run 的 <w:sz>/<w:szCs> count = 0(已剥)+ <w:rFonts> 仍在(字体未被误剥)+ <w:spacing>/<w:ind> 仍在(段距缩进保留)+ b/i/u 若有仍在
- 确切值/count 对照,禁泛断言
changelog:更新 V4-1a entry 补两句(fixture 对齐生产消假蓝色 + 字号归化 sz/szCs 回落 master,段距/缩进/字体/强调保留)。changelog 字面我现在直接给(见下),不停轮。

## 关键执行约束(Phase 2)

- 每 commit 后跑 run_all.py + R10 scan,确认不破坏 + 基线持平
- V4-1a.8 后 + V4-1a.9 后各重生成 injected docx 覆盖 scripts/tests/_v4_1a_phase3_injected.docx,供 Hugin 目检(.8 验黑标题、.9 验字号统一)
- 硬停下:四种合法停下 + 删 sz/szCs 误伤 rFonts/b/i/u/spacing/ind(lxml 选择器写错)→ 停下报告 + 发现要碰 master 才能修字号 → 停下报告(实测已确认 master Normal 14pt 是归化目标,不该碰 master)

## 自检方式(Phase 3)

1. fixture 对齐:夹具产物标题 Heading2 不再蓝(实测无 4F81BD / 回落黑),跟生产 demo assembled.docx 一致
2. 字号归化:注入后搬入 run 的 <w:sz>/<w:szCs> count = 0(已剥回落 master Normal 14pt)
3. 字体未误剥(关键 R10):注入后 run 的 <w:rFonts w:eastAsia="宋体"> 仍在(V4-1a.6 成果未被字号归化推翻)+ 仅 hint 无字体名 = 0(MS 明朝隐患仍清零)
4. 保留项未误删:<w:spacing>/<w:ind> 仍在(段距缩进保留)+ b/i/u 若 anchor 有则仍在(anchor 实测 0 个,N/A)
5. scope 零越界:git diff --name-only 仅 4 文件;master/rebind/字体fix逻辑/表格列宽 0 改
6. 不回归 + 人工目检:run_all.py 全 PASS（case 数记录）+ R10 基线持平；重生成 injected docx，Hugin 目检：标题黑色 + 表格字号统一 master + 字体仍宋体/Times New Roman（未 fallback）+ 列宽仍对