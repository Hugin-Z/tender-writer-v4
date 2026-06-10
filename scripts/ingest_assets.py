# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ops_common import (
    ASSETS_ROOT,
    CATEGORY_SPECS,
    append_markdown_table_row,
    append_pipe_csv_row,
    get_company,
    load_ingest_history,
    mask_person_name,
    move_to_raw,
    normalize_category,
    run_extract_text,
    sanitize_filename,
    save_ingest_history,
    today_str,
    unique_path,
)


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:120]
    return ""


def infer_date(text: str) -> str:
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text)
    if not match:
        return "TODO"
    year, month, day = match.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def infer_amount(text: str) -> str:
    match = re.search(r"([1-9]\d{0,6}(?:\.\d+)?)\s*万元", text)
    if match:
        return match.group(1)
    match = re.search(r"([1-9]\d{4,10})\s*元", text)
    if match:
        return str(round(float(match.group(1)) / 10000, 2))
    return "TODO"


def infer_industry(text: str) -> str:
    mapping = {
        "智慧城市": "智慧城市",
        "数字乡村": "数字乡村",
        "政务": "政务系统",
        "医疗": "医疗",
        "医院": "医疗",
        "教育": "教育",
        "住建": "住建",
        "交通": "交通",
    }
    for keyword, value in mapping.items():
        if keyword in text:
            return value
    return "TODO"


def infer_company_type(company_id: str) -> str:
    if company_id.startswith("own_"):
        return "own"
    if company_id.startswith("partner_"):
        return "partner"
    return "TODO"


def yaml_value(value) -> str:
    if isinstance(value, list):
        return "[" + ", ".join(str(item) for item in value) + "]"
    if isinstance(value, dict):
        inner = ", ".join(f"{key}: {val}" for key, val in value.items())
        return "{ " + inner + " }"
    if value is None:
        return "null"
    return str(value)


def build_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for key, value in meta.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def collect_todos(meta: dict) -> list[str]:
    todos: list[str] = []
    for key, value in meta.items():
        if isinstance(value, str) and value in {"TODO", ""}:
            todos.append(key)
        elif value is None:
            todos.append(key)
        elif isinstance(value, list) and not value:
            todos.append(key)
        elif isinstance(value, dict) and not value:
            todos.append(key)
    return todos


def infer_resume_name(text: str, file_stem: str) -> str:
    for line in text.splitlines()[:8]:
        candidate = line.strip()
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", candidate):
            return mask_person_name(candidate)
    if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", file_stem):
        return mask_person_name(file_stem)
    return "某某"


def generate_detail(category: str, company_id: str, source_file: Path, text: str) -> tuple[str, str, list[str], list[str]]:
    company_type = infer_company_type(company_id)
    file_stem = source_file.stem
    preview = "\n".join(line.strip() for line in text.splitlines()[:20] if line.strip())[:1000]

    if category == "业绩":
        project_name = first_non_empty_line(text) or file_stem
        meta = {
            "company_id": company_id,
            "company_type": company_type,
            "review_status": "pending",
            "source_file": source_file.name,
            "ingest_date": today_str(),
            "项目名称": project_name,
            "甲方单位": "TODO",
            "甲方类型": "TODO",
            "合同金额": infer_amount(text),
            "项目周期": "TODO",
            "开始日期": infer_date(text),
            "结束日期": "TODO",
            "行业分类": infer_industry(text),
            "项目规模": "TODO",
            "关键技术": [],
            "验收结果": "TODO",
            "项目地点": "TODO",
        }
        title = sanitize_filename(project_name)
        body = (
            "## 一、项目背景\n"
            f"{preview or 'TODO:待人工确认'}\n\n"
            "## 二、建设内容\n"
            "TODO:待人工确认\n\n"
            "## 三、技术亮点\n"
            "TODO:待人工确认\n\n"
            "## 四、社会效益\n"
            "TODO:待人工确认\n\n"
            "## 五、可复用的话术片段\n"
            "TODO:待人工确认\n"
        )
        index_columns = [
            project_name,
            str(meta["行业分类"]),
            str(meta["合同金额"]),
            str(meta["甲方类型"]),
            str(meta["结束日期"] if meta["结束日期"] != "TODO" else meta["开始日期"]),
            "、".join(meta["关键技术"]),
            str(meta["验收结果"]),
            company_id,
            company_type,
            "pending",
            f"{title}.md",
        ]
    elif category == "简历":
        name = infer_resume_name(text, file_stem)
        meta = {
            "company_id": company_id,
            "company_type": company_type,
            "review_status": "pending",
            "source_file": source_file.name,
            "ingest_date": today_str(),
            "姓名": name,
            "性别": "TODO",
            "出生年份": "TODO",
            "学历": "TODO",
            "毕业院校": "TODO",
            "专业": "TODO",
            "工作年限": "TODO",
            "当前岗位": "TODO",
            "职称": "TODO",
            "关键证书": [],
            "证书有效期": {},
            "适配项目类型": [],
        }
        title = sanitize_filename(name)
        body = (
            "## 一、个人简介\n"
            f"{preview or 'TODO:待人工确认'}\n\n"
            "## 二、主要业绩\n"
            "TODO:待人工确认\n\n"
            "## 三、技术专长\n"
            "TODO:待人工确认\n\n"
            "## 四、培训与认证\n"
            "TODO:待人工确认\n"
        )
        index_columns = [
            name,
            str(meta["当前岗位"]),
            str(meta["职称"]),
            "、".join(meta["关键证书"]),
            str(meta["证书有效期"]),
            "、".join(meta["适配项目类型"]),
            company_id,
            company_type,
            "pending",
            f"{title}.md",
        ]
    elif category == "资质":
        qualification_name = first_non_empty_line(text) or file_stem
        cert_no_match = re.search(r"([A-Z0-9][A-Z0-9\-]{5,})", text)
        issue_date = infer_date(text)
        meta = {
            "company_id": company_id,
            "company_type": company_type,
            "review_status": "pending",
            "source_file": source_file.name,
            "ingest_date": today_str(),
            "资质名称": qualification_name,
            "资质等级": "TODO",
            "证书号": cert_no_match.group(1) if cert_no_match else "TODO",
            "颁证机构": "TODO",
            "颁证日期": issue_date,
            "有效期至": "TODO",
            "适用范围": "TODO",
            "是否年审": "TODO",
            "下次年审日期": None,
        }
        title = sanitize_filename(qualification_name)
        body = (
            "## 一、资质说明\n"
            f"{preview or 'TODO:待人工确认'}\n\n"
            "## 二、原始文件位置\n"
            "TODO:待人工确认\n"
        )
        index_columns = [
            qualification_name,
            str(meta["资质等级"]),
            str(meta["颁证机构"]),
            str(meta["颁证日期"]),
            str(meta["有效期至"]),
            "pending",
            f"{title}.md",
        ]
    elif category == "图表":
        chart_title = file_stem
        chart_type = "架构图" if "架构" in file_stem else "流程图" if "流程" in file_stem else "其他"
        meta = {
            "company_id": company_id,
            "company_type": company_type,
            "review_status": "pending",
            "source_file": source_file.name,
            "ingest_date": today_str(),
            "图表标题": chart_title,
            "图表类型": chart_type,
            "适用维度": [],
            "适用项目类型": [],
            "原图路径": "TODO",
            "原图格式": source_file.suffix.lstrip(".").upper() or "TODO",
            "原图分辨率": "TODO",
            "适配能力": [],
        }
        title = sanitize_filename(chart_title)
        body = (
            "## 一、内容说明\n"
            f"{preview or 'TODO:待人工确认'}\n\n"
            "## 二、引用建议\n"
            "TODO:待人工确认\n\n"
            "## 三、原图位置\n"
            "TODO:待人工确认\n"
        )
        index_columns = [
            chart_title,
            chart_type,
            "、".join(meta["适用维度"]),
            "、".join(meta["适用项目类型"]),
            "pending",
            f"{title}.md",
        ]
    else:
        phrase_name = file_stem
        word_count = len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))
        meta = {
            "company_id": company_id,
            "company_type": company_type,
            "review_status": "pending",
            "source_file": source_file.name,
            "ingest_date": today_str(),
            "话术名称": phrase_name,
            "适用维度": "TODO",
            "适用场景": [],
            "字数": word_count,
            "来源项目": "TODO",
            "中标证据": "TODO",
            "核心句式": "TODO",
        }
        title = sanitize_filename(phrase_name)
        body = (
            "## 一、话术正文（原文）\n"
            f"{preview or 'TODO:待人工确认'}\n\n"
            "## 二、改写建议\n"
            "TODO:待人工确认\n\n"
            "## 三、注意事项\n"
            "TODO:待人工确认\n"
        )
        index_columns = [
            phrase_name,
            str(meta["适用维度"]),
            "、".join(meta["适用场景"]),
            str(meta["字数"]),
            str(meta["来源项目"]),
            "pending",
            f"{title}.md",
        ]

    todos = collect_todos(meta)
    detail_text = (
        build_frontmatter(meta)
        + "\n\n"
        + body
        + "\n\n## TODO 清单\n"
        + "\n".join(f"- TODO:{field}" for field in todos)
        + "\n"
    )
    return title, detail_text, index_columns, todos


def build_markdown_index_row(category: str, index_columns: list[str]) -> str:
    if category == "资质":
        return f"| {index_columns[0]} | {index_columns[1]} | {index_columns[2]} | {index_columns[3]} | {index_columns[4]} | {index_columns[5]} | {index_columns[6]} |"
    if category == "图表":
        return f"| {index_columns[0]} | {index_columns[1]} | {index_columns[2]} | {index_columns[3]} | {index_columns[4]} | {index_columns[5]} |"
    return f"| {index_columns[0]} | {index_columns[1]} | {index_columns[2]} | {index_columns[3]} | {index_columns[4]} | {index_columns[5]} | {index_columns[6]} |"


def ingest_file(category: str, company_id: str, file_path: Path, history: dict) -> dict:
    company_dir = ASSETS_ROOT / CATEGORY_SPECS[category]["folder"] / company_id
    raw_dir = company_dir / "_raw"
    index_path = company_dir / CATEGORY_SPECS[category]["index"]

    text, sha256 = run_extract_text(file_path)
    if sha256 in history:
        return {"status": "skipped", "file": file_path.name, "reason": "sha256 duplicate", "target": history[sha256].get("target", "")}

    title, detail_text, index_columns, todos = generate_detail(category, company_id, file_path, text)
    detail_path = unique_path(company_dir / f"{title}.md")
    detail_path.write_text(detail_text, encoding="utf-8")

    detail_ref = detail_path.name
    index_columns[-1] = detail_ref
    if CATEGORY_SPECS[category]["index_type"] == "csv":
        append_pipe_csv_row(index_path, index_columns)
    else:
        append_markdown_table_row(index_path, build_markdown_index_row(category, index_columns))

    archived = move_to_raw(file_path, raw_dir)
    history[sha256] = {
        "time": today_str(),
        "target": str(detail_path.relative_to(ASSETS_ROOT)),
        "source_file": file_path.name,
        "archived_raw": str(archived.relative_to(ASSETS_ROOT)),
        "category": category,
        "company_id": company_id,
    }
    return {
        "status": "processed",
        "file": file_path.name,
        "detail": str(detail_path),
        "todos": todos,
    }


def process(category: str, company_id: str, selected_files: list[Path] | None = None) -> list[dict]:
    company = get_company(company_id)
    if not company:
        raise RuntimeError(f"company_id 不存在: {company_id}")
    if company.get("type") == "reference":
        raise RuntimeError("reference 公司不能进入 assets 摄入流程")

    spec = CATEGORY_SPECS[category]
    inbox_dir = ASSETS_ROOT / spec["folder"] / company_id / "_inbox"
    if selected_files is None:
        files = [path for path in inbox_dir.iterdir() if path.is_file() and path.name != ".gitkeep"]
    else:
        files = [path for path in selected_files if path.is_file()]

    history = load_ingest_history()
    results: list[dict] = []
    for file_path in files:
        try:
            results.append(ingest_file(category, company_id, file_path, history))
        except Exception as exc:
            reason = str(exc)
            # 给 .doc 旧格式一个明确的修复指引,避免用户被通用错误信息困住
            if file_path.suffix.lower() == ".doc":
                reason = (
                    "旧版 .doc 格式不支持。"
                    "请用 Word 打开后另存为 .docx,再放回 _inbox/ 重新摄入。"
                )
            results.append({"status": "error", "file": file_path.name, "reason": reason})
    save_ingest_history(history)
    return results


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="处理已知分类素材 inbox")
    parser.add_argument("category", help="类别: 资质/业绩/简历/图表/话术")
    parser.add_argument("company_id", help="公司 id")
    parser.add_argument("files", nargs="*", help="可选，指定只处理这些文件；默认处理整个 _inbox")
    args = parser.parse_args()

    category = normalize_category(args.category)
    selected_files = [Path(file) for file in args.files] if args.files else None

    try:
        results = process(category, args.company_id, selected_files)
    except Exception as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        sys.exit(1)

    processed = [row for row in results if row["status"] == "processed"]
    skipped = [row for row in results if row["status"] == "skipped"]
    errors = [row for row in results if row["status"] == "error"]

    print(f"[完成] {category} 摄入完成，公司: {args.company_id}")
    print(f"  处理成功: {len(processed)}")
    print(f"  重复跳过: {len(skipped)}")
    print(f"  处理失败: {len(errors)}")

    if processed:
        print("  新生成条目:")
        for row in processed:
            print(f"    - {row['file']} -> {row['detail']}")
            if row["todos"]:
                print(f"      TODO: {', '.join(row['todos'])}")

    if skipped:
        print("  重复文件:")
        for row in skipped:
            print(f"    - {row['file']} ({row['reason']})")

    if errors:
        print("  失败文件:")
        for row in errors:
            print(f"    - {row['file']}: {row['reason']}")


if __name__ == "__main__":
    main()
