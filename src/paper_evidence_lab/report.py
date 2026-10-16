"""A deterministic, escaped reading view of query + JSON result fields."""

import html
import json
import re
from dataclasses import asdict
from urllib.parse import quote

from .corpus import validate_url
from .models import SearchResult


def _text(value: str) -> str:
    escaped = html.escape(value, quote=True)
    return re.sub(r"([\\`*{}\[\]()#+.!_|>~=\-])", r"\\\1", escaped).replace("\n", "  \n")


def render_markdown(query: str, results: list[SearchResult]) -> str:
    lines = [
        "# Paper Evidence Lab 检索结果",
        "",
        f"查询：{_text(query)}",
        "",
        "分数仅用于词项相关性排序，不代表准确率、证据强度或结论已被证实。",
        "",
    ]
    if not results:
        lines.extend(["无匹配结果（预处理后无有效词项，或没有正分命中）。", ""])
    for rank, result in enumerate(results, 1):
        lines.extend([f"## {rank}. {_text(result.title) if result.title else '题名缺失'}", ""])
        for key, value in asdict(result).items():
            if value is None:
                rendered = "null（缺失）"
            elif key in {"source_url", "license_url"}:
                validate_url(value)
                safe = quote(value, safe="/:?#&=.%+~@")
                rendered = f"[链接](<{safe}>)"
            elif isinstance(value, str):
                rendered = _text(value)
            else:
                rendered = json.dumps(value, allow_nan=False)
            lines.extend([f"**{key}**: {rendered}", ""])
    return "\n".join(lines)
