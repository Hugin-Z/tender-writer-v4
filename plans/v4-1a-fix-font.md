# plans/v4-1a-fix-font.md — V4-1a 字体 fallback 修复(deepcopy 注入后 CJK+西文显式 rFonts)

## 背景

V4-1a Phase 3 人工目检发现:注入后表格中文 fallback 到 MS 明朝(日文,L4 灾难类型)。
根因(Phase 0 实测坐实):搬入表格 run 的 <w:rFonts> 只有 w:hint="eastAsia" 无显式字体名 → 表格走 TableNormal→docDefaults 主题(非 Normal,Normal 的宋体救不了表格)→ master theme ea 空 → WPS/Word fallback 到系统 CJK 默认 MS 明朝。西文同理:无 ascii/hAnsi → 走 theme minorLatin=Cambria,跟 master 全局 Times New Roman 脱节。
裁定:搬入 run 补显式字体名,统一成 master 字体(中文宋体 / 西文 Times New Roman / cs Times New Roman),跟 master apply_default_styles 给 Normal 设的四组字体完全一致。断主题 fallback 路径(L4 应对策略「显式设 rFonts 不靠主题」在 asset 注入场景的复现)。

这是 V4-1a 自身引入 bug 的修复(V4-1a 5 commit 未 push,在收尾前发现),作为 V4-1a.6/.7 延续 commit,跟前 5 个一起 push,非"发布后补丁"。

## 字体确切值(Phase 0 实测三层确认 / 全跟 master apply_default_styles 一致)

- eastAsia(中文)= 宋体
- ascii(西文 ASCII)= Times New Roman
- hAnsi(西文高位 ANSI)= Times New Roman
- cs(复杂脚本)= Times New Roman(anchor 无 cs 字符,补全为跟 master 四组对齐的完整性,非功能必需)

## scope 边界(钉死)

动:
- scripts/b_mode_fill.py(新增 _apply_explicit_fonts_to_runs helper + 在 _handle_asset_lookup 的 rebind 后调用)
- scripts/tests/test_b_mode_v4_1a.py(加第 8 case 验显式字体)
- docs/changelog.md(更新 V4-1a entry:加字体 fallback 修复说明)
- plans/v4-1a-fix-font.md(本文件,入仓)

不动(越界即停下报告):
- master 端任何配置(docx_builder DEFAULT_STYLES / apply_default_styles / master styles.xml / theme1.xml)—— 修法选 A(run 级补),不碰 master(选项 B/C/D 改 master 均越界,Phase 0 已排除)
- rebind/strip 现有逻辑(_build_style_id_map / _rebind_or_strip_refs 不改,只在其后加新调用)
- 源 docx(只读)
- 图片/页眉页脚/公章/provider/asset_query schema/其他 sub_mode/handbook

完成判定:5 条(见自检方式)。

## 子任务 + commit 序列

| # | commit message | 文件 |
|---|---|---|
| 6 | `V4-1a.6 注入 run 补显式字体(中文宋体+西文 Times New Roman)防 MS 明朝 fallback` | b_mode_fill.py |
| 7 | `V4-1a.7 字体 fix 测试 + changelog 更新:deepcopy 注入显式 rFonts 防 fallback(L4 复现)` | test_b_mode_v4_1a.py / docs/changelog.md / plans/v4-1a-fix-font.md |

2 commit。V4-1a.6 实现 / V4-1a.7 测试+文档收尾。

## 实现指令(Phase 2 据实参照)

### V4-1a.6 — 补显式字体 helper

参照 Phase 0 实测给的框架 + master docx_builder.set_run_font / apply_default_styles 的 rFonts 设法。新 helper(命名实测确认风格,如 _apply_explicit_fonts_to_runs):
- 遍历 element 内每个 <w:r>:ensure <w:rPr> → ensure <w:rFonts>
- 对 rFonts:仅在对应属性「不存在」时 set(不覆盖源 docx 已有的显式字体名 —— 源若某 run 显式设了字体,尊重它;只补那些「无字体名靠主题」的)
  - w:eastAsia 不存在 → set "宋体"
  - w:ascii 不存在 → set "Times New Roman"
  - w:hAnsi 不存在 → set "Times New Roman"
  - w:cs 不存在 → set "Times New Roman"
- 返回补了多少处(供日志/测试)
调用点:_handle_asset_lookup 在 _rebind_or_strip_refs(new_elem, ...) 之后(deepcopy + rebind 完再补字体,顺序:deepcopy → rebind/strip → 补字体)

设计要点(防过度):
- 「仅不存在才 set」不是「无条件覆盖」—— 源 docx 若有 run 显式指定了某字体(非靠主题),保留源的,不强制改成宋体/Times。本 bug 修的是「靠主题导致 fallback」,不是「强制所有字体统一」。anchor 1.docx 的 run 都是靠主题(无显式字体名),所以会全部补上;但逻辑对「源有显式字体」的 run 是尊重的

### V4-1a.7 — 测试 + 文档

测试加第 8 case(test_b_mode_v4_1a):
- 注入后表格 run 的 <w:rFonts> 实测:w:eastAsia="宋体" count ≥ 表格 run 数 + w:ascii="Times New Roman" + w:hAnsi="Times New Roman" 同步在
- 断言 0 个表格 run 的 rFonts 是「只 hint 无字体名」(即 fallback 隐患清零)
- 禁泛断言,用确切字体名对照
changelog:更新 V4-1a entry(不是新 entry,是给 6727b80 那个 entry 补一句),加字体 fallback 修复:「注入 run 补显式 rFonts(中文宋体/西文 Times New Roman)防 WPS fallback MS 明朝,L4 在 asset 注入场景复现」
plan 入仓。

## 关键执行约束(Phase 2)

- 每 commit 后跑 run_all.py + R10 scan,确认不破坏 + 基线持平
- 重新生成 injected docx 到 scripts/tests/_v4_1a_phase3_injected.docx(覆盖旧的),供 Hugin 重新目检字体
- changelog 字面落盘前停下等 chat 端(它是给已有 entry 补字面,正文我给)—— 但这次「补一句」很短,可由我现在直接给(见下),不必再停一轮
- 硬停下:四种合法停下 + 「仅不存在才 set」在 lxml 落不下去 / 发现要碰 master 才能修 → 停下报告

## 自检方式(Phase 3)

1. 显式字体补上:注入后表格每个 run 的 rFonts 有 w:eastAsia="宋体" + w:ascii/hAnsi="Times New Roman"(实测 count)
2. fallback 隐患清零:0 个表格 run 是「只 w:hint 无字体名」
3. 源显式字体被尊重:若 anchor 有 run 原本显式设了字体(实测确认 anchor 全靠主题,预期此项 N/A),不被覆盖
4. scope 零越界:git diff --name-only 仅 4 文件;master docx_builder/styles/theme + rebind 现有逻辑 0 改
5. 不回归 + 人工目检:run_all.py 全 PASS（15→16，新增第 8 case）+ R10 基线持平；重生成 injected docx，Hugin 打开核对中文不再 MS 明朝(变宋体)+ 西文 Times New Roman