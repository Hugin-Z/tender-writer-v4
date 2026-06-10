# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import date
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_ROOT = SKILL_ROOT / "assets"
REFERENCES_ROOT = SKILL_ROOT / "references"
COMPANIES_FILE = SKILL_ROOT / "companies.yaml"
INGEST_HISTORY_FILE = ASSETS_ROOT / ".ingest_history.json"

CATEGORY_SPECS = {
    "资质": {
        "folder": "公司资质",
        "schema": ASSETS_ROOT / "公司资质" / "资质schema.md",
        "index": "资质清单.md",
        "index_type": "markdown",
    },
    "业绩": {
        "folder": "类似业绩",
        "schema": ASSETS_ROOT / "类似业绩" / "业绩schema.md",
        "index": "业绩列表.csv",
        "index_type": "csv",
    },
    "简历": {
        "folder": "团队简历",
        "schema": ASSETS_ROOT / "团队简历" / "简历schema.md",
        "index": "简历索引.csv",
        "index_type": "csv",
    },
    "图表": {
        "folder": "通用图表",
        "schema": ASSETS_ROOT / "通用图表" / "图表schema.md",
        "index": "图表索引.md",
        "index_type": "markdown",
    },
    "话术": {
        "folder": "标准话术",
        "schema": ASSETS_ROOT / "标准话术" / "话术schema.md",
        "index": "话术索引.md",
        "index_type": "markdown",
    },
}

CATEGORY_ALIASES = {
    "资质": "资质",
    "公司资质": "资质",
    "qualification": "资质",
    "qual": "资质",
    "业绩": "业绩",
    "类似业绩": "业绩",
    "performance": "业绩",
    "project": "业绩",
    "简历": "简历",
    "团队简历": "简历",
    "resume": "简历",
    "cv": "简历",
    "图表": "图表",
    "通用图表": "图表",
    "chart": "图表",
    "diagram": "图表",
    "话术": "话术",
    "标准话术": "话术",
    "phrase": "话术",
    "phrases": "话术",
}


def normalize_category(raw: str) -> str:
    key = raw.strip().lower()
    if key not in CATEGORY_ALIASES:
        raise ValueError(f"不支持的类别: {raw}")
    return CATEGORY_ALIASES[key]


def today_str() -> str:
    return date.today().isoformat()


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\\\|?*]+', "_", name).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] or "item"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def ensure_text_file(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def parse_companies() -> list[dict]:
    lines = COMPANIES_FILE.read_text(encoding="utf-8").splitlines()
    companies: list[dict] = []
    current: dict | None = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                companies.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            continue
        if current is None:
            continue
        for field in ("name", "type", "description", "aliases", "created_at"):
            marker = f"{field}:"
            if stripped.startswith(marker):
                value = stripped.split(":", 1)[1].strip()
                if field == "aliases":
                    aliases = [part.strip() for part in value.strip("[]").split(",") if part.strip()]
                    current[field] = aliases
                else:
                    current[field] = value
                break

    if current:
        companies.append(current)
    return companies


def get_company(company_id: str) -> dict | None:
    for company in parse_companies():
        if company.get("id") == company_id:
            return company
    return None


def append_company(company: dict) -> None:
    with COMPANIES_FILE.open("a", encoding="utf-8") as handle:
        aliases = company.get("aliases", [])
        aliases_text = "[" + ", ".join(aliases) + "]" if aliases else "[]"
        handle.write("\n")
        handle.write(f"  - id: {company['id']}\n")
        handle.write(f"    name: {company['name']}\n")
        handle.write(f"    type: {company['type']}\n")
        handle.write(f"    description: {company.get('description', '')}\n")
        handle.write(f"    aliases: {aliases_text}\n")
        handle.write(f"    created_at: {company['created_at']}\n")


def slugify_company_name(name: str) -> str:
    try:
        from pypinyin import lazy_pinyin  # type: ignore

        slug = "_".join(part for part in lazy_pinyin(name) if part)
        slug = re.sub(r"[^a-zA-Z0-9_]+", "", slug).lower().strip("_")
        if slug:
            return slug
    except Exception:
        pass

    ascii_text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "_", ascii_text).lower().strip("_")
    if ascii_text:
        return ascii_text

    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"company_{digest}"


def next_available_company_id(company_type: str, name: str) -> str:
    prefix = {"own": "own", "partner": "partner", "reference": "ref"}[company_type]
    base = f"{prefix}_{slugify_company_name(name)}"
    existing_ids = {company["id"] for company in parse_companies()}
    if base not in existing_ids:
        return base
    counter = 2
    while True:
        candidate = f"{base}_{counter}"
        if candidate not in existing_ids:
            return candidate
        counter += 1


def load_ingest_history() -> dict:
    if not INGEST_HISTORY_FILE.exists():
        return {}
    try:
        return json.loads(INGEST_HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_ingest_history(data: dict) -> None:
    INGEST_HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_extract_text(file_path: Path) -> tuple[str, str]:
    if file_path.suffix.lower() not in {".pdf", ".docx", ".doc"}:
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest().lower()
        return "", digest

    script = Path(__file__).resolve().parent / "extract_text.py"
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(script), str(file_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"extract_text 失败: {file_path}")
    match = re.search(r"SHA256:\s*([0-9a-fA-F]{64})", result.stderr)
    if not match:
        raise RuntimeError(f"未能从 extract_text 输出中解析 sha256: {file_path}")
    return result.stdout, match.group(1).lower()


def mask_person_name(name: str) -> str:
    name = name.strip()
    if len(name) <= 1:
        return "某"
    return name[0] + "某" * (len(name) - 1)


def infer_company_from_text(text: str, file_name: str, companies: list[dict]) -> dict | None:
    haystacks = [text[:4000], file_name]
    for company in companies:
        names = [company.get("name", "")] + company.get("aliases", [])
        for token in names:
            token = token.strip()
            if not token:
                continue
            if any(token in haystack for haystack in haystacks):
                return company
    return None


def append_markdown_table_row(path: Path, row_text: str) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    placeholder_index = next((i for i, line in enumerate(lines) if "<!--" in line), None)
    if placeholder_index is not None:
        lines[placeholder_index] = row_text
    else:
        insert_index = next((i for i, line in enumerate(lines) if line.strip() == "---"), len(lines))
        lines.insert(insert_index, row_text)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_pipe_csv_row(path: Path, columns: list[str]) -> None:
    line = "|".join(columns)
    with path.open("a", encoding="utf-8-sig", newline="") as handle:
        if path.stat().st_size > 0:
            handle.write("\n")
        handle.write(line)


def copy_to_target_inbox(source: Path, target_inbox: Path) -> Path:
    ensure_dir(target_inbox)
    target = unique_path(target_inbox / source.name)
    shutil.copy2(source, target)
    return target


def move_to_raw(source: Path, raw_dir: Path) -> Path:
    ensure_dir(raw_dir)
    target = unique_path(raw_dir / f"{date.today().strftime('%Y%m%d')}_{source.name}")
    shutil.move(str(source), str(target))
    return target
