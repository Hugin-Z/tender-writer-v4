# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ops_common import (
    ASSETS_ROOT,
    CATEGORY_SPECS,
    append_company,
    ensure_dir,
    ensure_text_file,
    get_company,
    next_available_company_id,
    today_str,
)


def qualification_index_template(company_id: str) -> str:
    return f"""# {company_id} · 资质清单

| 资质名称 | 等级 | 颁证机构 | 颁证日期 | 有效期至 | review_status | 详情路径 |
|---|---|---|---|---|---|---|
| <!-- 待摄入 --> | | | | | | |
"""


def performance_index_template() -> str:
    return "项目名称|行业|规模万|甲方类型|完成时间|关键技术|验收结果|company_id|company_type|review_status|详情路径\n"


def resume_index_template() -> str:
    return "姓名|岗位|职称|关键证书|证书有效期|适配项目类型|company_id|company_type|review_status|详情路径\n"


def chart_index_template(company_id: str) -> str:
    return f"""# {company_id} · 图表索引

| 图表标题 | 类型 | 适用维度 | 适用项目类型 | review_status | 详情路径 |
|---|---|---|---|---|---|
| <!-- 待摄入 --> | | | | | |
"""


def phrase_index_template(company_id: str) -> str:
    return f"""# {company_id} · 话术索引

| 话术名称 | 适用维度 | 适用场景 | 字数 | 来源项目 | review_status | 详情路径 |
|---|---|---|---|---|---|---|
| <!-- 待摄入 --> | | | | | | |
"""


def init_company_asset_dirs(company_id: str) -> list[Path]:
    created: list[Path] = []
    for category, spec in CATEGORY_SPECS.items():
        company_dir = ASSETS_ROOT / spec["folder"] / company_id
        inbox = company_dir / "_inbox"
        raw = company_dir / "_raw"
        ensure_dir(inbox)
        ensure_dir(raw)
        ensure_text_file(inbox / ".gitkeep", "")
        ensure_text_file(raw / ".gitkeep", "")
        created.extend([company_dir, inbox, raw])

        index_path = company_dir / spec["index"]
        if category == "资质":
            ensure_text_file(index_path, qualification_index_template(company_id))
        elif category == "业绩":
            ensure_text_file(index_path, performance_index_template())
        elif category == "简历":
            ensure_text_file(index_path, resume_index_template())
        elif category == "图表":
            ensure_text_file(index_path, chart_index_template(company_id))
        elif category == "话术":
            ensure_text_file(index_path, phrase_index_template(company_id))
        created.append(index_path)

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="新增公司并初始化素材目录")
    parser.add_argument("name", help="公司全称")
    parser.add_argument("company_type", choices=["own", "partner", "reference"], help="公司类型")
    parser.add_argument("--id", dest="company_id", help="指定公司 id；不传则自动生成")
    parser.add_argument("--alias", action="append", default=[], help="可重复传入公司别名")
    parser.add_argument("--description", default="", help="公司描述")
    args = parser.parse_args()

    seed_name = args.alias[0] if args.alias else args.name
    company_id = args.company_id or next_available_company_id(args.company_type, seed_name)
    if get_company(company_id):
        print(f"[错误] company_id 已存在: {company_id}", file=sys.stderr)
        sys.exit(1)

    company = {
        "id": company_id,
        "name": args.name,
        "type": args.company_type,
        "description": args.description,
        "aliases": args.alias,
        "created_at": today_str(),
    }
    append_company(company)

    created_paths: list[Path] = []
    if args.company_type in {"own", "partner"}:
        created_paths = init_company_asset_dirs(company_id)

    print(f"[完成] 已新增公司: {company_id}")
    print(f"  名称: {args.name}")
    print(f"  类型: {args.company_type}")
    if args.alias:
        print(f"  别名: {', '.join(args.alias)}")
    if created_paths:
        print("  已初始化素材目录:")
        for path in created_paths:
            print(f"    - {path}")
    else:
        print("  reference 类型不创建 assets 目录，仅登记到 companies.yaml")


if __name__ == "__main__":
    main()
