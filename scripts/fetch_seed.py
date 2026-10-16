"""Run from the repository after uv sync; writes ignored local data by default."""

import argparse
import json
import sys
from pathlib import Path

from paper_evidence_lab.sources import fetch_corpus


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="获取两篇固定版本论文；不要频繁重复运行")
    parser.add_argument("--output", type=Path, default=root / "data/local/seeds.jsonl")
    args = parser.parse_args()
    try:
        sources = json.loads((root / "data/seed_sources.json").read_text(encoding="utf-8"))
        docs = fetch_corpus(sources, args.output)
    except (OSError, ValueError) as exc:
        print(f"获取失败: {exc}", file=sys.stderr)
        return 2
    print(f"已获取并校验 {len(docs)} 篇固定版本文献：{args.output}")
    for doc in docs:
        if doc.abstract is None:
            print(f"摘要缺失: {doc.doc_id}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
