# 公司资质

## 用途

存放公司各类资质证书的结构化记录(资质名称、等级、有效期、证书号脱敏等),供阶段 4 撰写资质章节时调用。

## 公司归属规则

按 `<company_id>/` 子目录隔离:
- **own**:我方主体的资质,可直接引用
- **partner**:合作方资质,**仅联合体投标且招标文件允许时**才可引用
- **reference**:**严禁**出现在本目录(只能进 `references/knowledge_base/`)

## 摄入流程

1. 把资质证书的扫描件 PDF / 图片 / docx 复制到 `<company_id>/_inbox/`
2. 在 Claude Code 中说"处理 <company_id> 的资质 inbox"
3. AI 调用 `extract_text.py` 提取文字(扫描件需先 OCR),按 `资质schema.md` 结构化
4. 输出 `<资质名>.md`,frontmatter 中 `review_status=pending`
5. 同时追加索引到 `<company_id>/资质清单.md`
6. 原文件移动到 `_raw/`(加时间戳前缀)
7. 用户人工 review,把 `review_status` 改为 `approved`

## 阶段 5 终审协同

阶段 5 合规终审时会扫描 `<own_company_id>/资质清单.md` 中所有 `approved` 资质,检查证书有效期。**过期或临期(< 30 天)的证书会被标红**。
