# -*- coding: utf-8 -*-
"""
_asset_type_mapping.py · asset_type → assets/ 类别 映射加载工具(V3-1)

由 CuratedLocalAssetsProvider 调用,把 manifest.yaml 中
assembly_order 的 spec.asset_type / asset_query.type 映射到现有 assets/
顶层 5 类中文类别名(公司资质 / 团队简历 / 标准话术 / 类似业绩 / 通用图表)。

映射表见 references/asset_type_mapping.yaml。

用法:
    from _asset_type_mapping import map_asset_type_to_category
    cat = map_asset_type_to_category("资质证书", "资质")
    # → "公司资质"
"""
from __future__ import annotations

from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise RuntimeError("缺少 PyYAML 依赖") from exc


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MAPPING_PATH = ROOT / "references" / "asset_type_mapping.yaml"

PLACEHOLDER_SENTINEL = "__placeholder__"


def load_mapping(path: Path | None = None) -> dict:
    """加载 asset_type 映射表,返回完整 dict。"""
    target = Path(path) if path else DEFAULT_MAPPING_PATH
    with open(target, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def map_asset_type_to_category(
    spec_asset_type: str,
    asset_query_type: str = "",
    mapping_path: Path | None = None,
) -> str:
    """把 spec.asset_type / asset_query.type 映射到 assets/ 类别中文名。

    命中规则:
    1. 精确匹配 spec_asset_type → mapping 命中即返回
    2. 回退匹配 asset_query_type → 命中即返回
    3. 兜底返回 fallback(yaml 中的 fallback 字段,默认 "__placeholder__")

    返回 "__placeholder__" 时调用方应产出 placeholder AssetRef + 日志告警,
    不应抛异常(保持 b_mode_fill 流程不中断)。
    """
    data = load_mapping(mapping_path)
    mappings = data.get("mappings", {}) or {}
    fallback = data.get("fallback", PLACEHOLDER_SENTINEL)

    if spec_asset_type and spec_asset_type in mappings:
        return mappings[spec_asset_type]
    if asset_query_type and asset_query_type in mappings:
        return mappings[asset_query_type]
    return fallback
