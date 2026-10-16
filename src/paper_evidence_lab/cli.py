"""Offline query interface; stdout is reserved for the requested result."""

import argparse
import json
import sys
import zipfile
from dataclasses import asdict
from pathlib import Path

from .benchmark import evaluate_bm25
from .corpus import load_corpus
from .report import render_markdown
from .retrieval import BM25Index
from .scifact import acquire_scifact


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="英文论文词项检索；检索相关不等于结论已证实")
    commands = parser.add_subparsers(dest="command", required=True)
    search = commands.add_parser("search", help="离线查询 JSONL 文献集合")
    search.add_argument("--corpus", type=Path, required=True)
    search.add_argument("--query", required=True)
    search.add_argument("--top-k", type=int, default=5)
    search.add_argument("--format", choices=("json", "markdown"), default="json")
    acquire = commands.add_parser("fetch-scifact", help="校验并保存固定 SciFact 数据到新目录")
    acquire.add_argument("--output", type=Path, required=True)
    acquire.add_argument("--archive", type=Path, help="可选：导入已下载的官方 ZIP，仍严格核对哈希")
    evaluate = commands.add_parser("evaluate", help="校验本地 SciFact 后运行固定 BM25 top-10 评测")
    evaluate.add_argument("--dataset", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "fetch-scifact":
            receipt = acquire_scifact(
                args.output, archive_bytes=args.archive.read_bytes() if args.archive else None
            )
            print(json.dumps(receipt, ensure_ascii=False, indent=2, allow_nan=False))
            return 0
        if args.command == "evaluate":
            print(
                json.dumps(
                    evaluate_bm25(args.dataset), ensure_ascii=False, indent=2, allow_nan=False
                )
            )
            return 0
        results = BM25Index(load_corpus(args.corpus)).search(args.query, args.top_k)
        output = (
            json.dumps(
                [asdict(row) for row in results], ensure_ascii=False, indent=2, allow_nan=False
            )
            if args.format == "json"
            else render_markdown(args.query, results)
        )
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    if not results:
        print("无匹配结果：预处理后无有效词项，或没有正分命中。", file=sys.stderr)
    print(output, end="" if output.endswith("\n") else "\n")
    return 0
