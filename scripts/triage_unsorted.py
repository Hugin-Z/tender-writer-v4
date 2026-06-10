# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path

from ingest_assets import process as ingest_known_assets
from ops_common import (
    ASSETS_ROOT,
    REFERENCES_ROOT,
    copy_to_target_inbox,
    ensure_dir,
    infer_company_from_text,
    move_to_raw,
    parse_companies,
    run_extract_text,
)


UNSORTED_DIR = Path(__file__).resolve().parent.parent / "_inbox_unsorted"
REFERENCE_INBOX = REFERENCES_ROOT / "knowledge_base" / "历史标书案例" / "_inbox"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg", ".vsdx", ".webp", ".bmp"}
RESUME_NAME_KEYWORDS = ("简历", "resume", "cv", "履历", "人员")
RESUME_TEXT_KEYWORDS = ("学历", "工作经历", "职称", "项目经理", "工程师", "任职", "出生", "毕业院校")
QUALIFICATION_NAME_KEYWORDS = ("资质", "证书", "认证", "许可证", "获奖", "奖项", "专利")
QUALIFICATION_TEXT_KEYWORDS = ("证书编号", "有效期至", "认证", "发证机关", "CMMI", "ISO", "许可证")
PERFORMANCE_NAME_KEYWORDS = ("业绩", "合同", "验收", "项目", "中标")
PERFORMANCE_TEXT_KEYWORDS = ("中标通知书", "合同金额", "项目名称", "采购人", "验收", "合同编号")
REFERENCE_NAME_KEYWORDS = ("投标文件", "技术方案", "标书", "评分办法", "评标办法", "案例")
REFERENCE_TEXT_KEYWORDS = ("投标文件", "技术方案", "评分办法", "评标办法", "目录", "采购需求")
PHRASE_NAME_KEYWORDS = ("话术", "模板", "响应", "承诺", "方案")
PHRASE_TEXT_KEYWORDS = ("承诺", "保障机制", "响应时限", "服务方案", "实施方案")
CHART_NAME_KEYWORDS = ("架构", "流程", "拓扑", "diagram", "chart", "流程图", "架构图", "组织图")


def has_any(haystacks: list[str], keywords: tuple[str, ...]) -> bool:
    for haystack in haystacks:
        for keyword in keywords:
            if keyword and keyword.lower() in haystack.lower():
                return True
    return False


def suggest_category(file_path: Path, text: str) -> tuple[str, list[str]]:
    name = file_path.name
    stem = file_path.stem
    haystacks = [name, stem, text[:4000]]
    reasons: list[str] = []

    if file_path.suffix.lower() in IMAGE_SUFFIXES:
        return "图表", [f"扩展名 {file_path.suffix.lower()} 属于图片或图表文件"]

    if has_any([name, stem], CHART_NAME_KEYWORDS):
        return "图表", ["文件名命中架构图/流程图/diagram/chart 等图表关键词"]

    if has_any([name, stem], RESUME_NAME_KEYWORDS) or has_any(haystacks, RESUME_TEXT_KEYWORDS):
        if has_any([name, stem], RESUME_NAME_KEYWORDS):
            reasons.append("文件名命中简历/resume/cv 等关键词")
        if has_any(haystacks, RESUME_TEXT_KEYWORDS):
            reasons.append("正文包含学历/工作经历/职称等简历特征")
        return "简历", reasons

    if has_any([name, stem], QUALIFICATION_NAME_KEYWORDS) or has_any(haystacks, QUALIFICATION_TEXT_KEYWORDS):
        if has_any([name, stem], QUALIFICATION_NAME_KEYWORDS):
            reasons.append("文件名命中资质/证书/认证/专利等关键词")
        if has_any(haystacks, QUALIFICATION_TEXT_KEYWORDS):
            reasons.append("正文包含证书编号/有效期/认证/发证机关等资质特征")
        return "资质", reasons

    if has_any([name, stem], REFERENCE_NAME_KEYWORDS) or has_any(haystacks, REFERENCE_TEXT_KEYWORDS):
        if has_any([name, stem], REFERENCE_NAME_KEYWORDS):
            reasons.append("文件名命中标书/技术方案/评分办法/案例等参考资料关键词")
        if has_any(haystacks, REFERENCE_TEXT_KEYWORDS):
            reasons.append("正文包含投标文件/评分办法/采购需求等历史案例特征")
        return "历史案例", reasons

    if has_any([name, stem], PHRASE_NAME_KEYWORDS) or has_any(haystacks, PHRASE_TEXT_KEYWORDS):
        if has_any([name, stem], PHRASE_NAME_KEYWORDS):
            reasons.append("文件名命中话术/模板/响应/承诺等复用文段关键词")
        if has_any(haystacks, PHRASE_TEXT_KEYWORDS):
            reasons.append("正文更像承诺或响应文段，而非单项证书或完整项目业绩")
        return "话术", reasons

    if has_any([name, stem], PERFORMANCE_NAME_KEYWORDS) or has_any(haystacks, PERFORMANCE_TEXT_KEYWORDS):
        if has_any([name, stem], PERFORMANCE_NAME_KEYWORDS):
            reasons.append("文件名命中业绩/合同/验收/项目等关键词")
        if has_any(haystacks, PERFORMANCE_TEXT_KEYWORDS):
            reasons.append("正文包含中标/合同金额/采购人/验收等项目业绩特征")
        return "业绩", reasons

    return "业绩", ["未命中强规则，暂按业绩材料建议处理，需人工复核"]


def build_target_path(category: str, company_id: str | None, company_type: str | None) -> str:
    if category == "历史案例" or company_type == "reference":
        return str(REFERENCE_INBOX)
    if not company_id:
        return "【待确认公司归属后再分发】"

    folder_map = {
        "资质": "公司资质",
        "业绩": "类似业绩",
        "简历": "团队简历",
        "图表": "通用图表",
        "话术": "标准话术",
    }
    return str(ASSETS_ROOT / folder_map[category] / company_id / "_inbox")


def scan_unsorted() -> list[Path]:
    if not UNSORTED_DIR.exists():
        return []
    return [
        path
        for path in UNSORTED_DIR.iterdir()
        if path.is_file() and path.name not in {".gitkeep", "README.md"}
    ]


def build_suggestions(files: list[Path]) -> list[dict]:
    companies = parse_companies()
    suggestions: list[dict] = []

    for file_path in files:
        try:
            text, _sha = run_extract_text(file_path)
        except Exception as exc:
            suggestions.append({
                "file": str(file_path),
                "status": "error",
                "reason": str(exc),
            })
            continue

        category, category_reasons = suggest_category(file_path, text)
        matched_company = infer_company_from_text(text, file_path.name, companies)
        company_id = matched_company.get("id") if matched_company else None
        company_type = matched_company.get("type") if matched_company else None

        if category == "历史案例" and company_type is None:
            company_type = "reference"

        reason_parts = list(category_reasons)
        if matched_company:
            reason_parts.append(f"识别到公司: {matched_company['name']}")
        else:
            reason_parts.append("未识别到公司归属，需人工确认")

        suggestions.append({
            "file": str(file_path),
            "status": "ok",
            "category": category,
            "company_id": company_id,
            "company_type": company_type,
            "reason": "；".join(reason_parts),
            "target": build_target_path(category, company_id, company_type),
        })

    return suggestions


def apply_suggestions(suggestions: list[dict]) -> list[str]:
    applied: list[str] = []
    unsorted_raw = UNSORTED_DIR / "_raw"
    ensure_dir(unsorted_raw)

    folder_map = {
        "资质": "公司资质",
        "业绩": "类似业绩",
        "简历": "团队简历",
        "图表": "通用图表",
        "话术": "标准话术",
    }

    for item in suggestions:
        if item.get("status") != "ok":
            continue

        source = Path(item["file"])
        category = item["category"]
        company_id = item.get("company_id")
        company_type = item.get("company_type")

        if category == "历史案例" or company_type == "reference":
            copied = copy_to_target_inbox(source, REFERENCE_INBOX)
            move_to_raw(source, unsorted_raw)
            applied.append(f"{source.name} -> {copied}")
            continue

        if not company_id:
            applied.append(f"{source.name} -> 跳过（未识别公司归属）")
            continue

        target_inbox = ASSETS_ROOT / folder_map[category] / company_id / "_inbox"
        copied = copy_to_target_inbox(source, target_inbox)
        move_to_raw(source, unsorted_raw)
        ingest_known_assets(category, company_id, [copied])
        applied.append(f"{source.name} -> {copied} -> 已触发摄入")

    return applied


def main() -> None:
    parser = argparse.ArgumentParser(description="扫描 _inbox_unsorted 并输出分类建议")
    parser.add_argument("--apply", action="store_true", help="按当前建议执行分发；默认仅输出建议报告")
    args = parser.parse_args()

    files = scan_unsorted()
    if not files:
        print("[信息] _inbox_unsorted 当前没有待处理文件。")
        return

    suggestions = build_suggestions(files)
    print("[完成] 已生成分类建议")
    for item in suggestions:
        if item.get("status") == "error":
            print(f"  - {Path(item['file']).name}: 错误 -> {item['reason']}")
            continue
        print(f"  - {Path(item['file']).name}")
        print(f"    类别建议: {item['category']}")
        print(f"    公司建议: {item.get('company_id') or '【待确认】'}")
        print(f"    公司类型: {item.get('company_type') or '【待确认】'}")
        print(f"    目标路径: {item['target']}")
        print(f"    判断理由: {item['reason']}")

    if args.apply:
        applied = apply_suggestions(suggestions)
        print("[完成] 已按建议执行分发:")
        for line in applied:
            print(f"  - {line}")
    else:
        print("未执行分发。确认建议无误后，可重新运行并加上 --apply。")


if __name__ == "__main__":
    main()
