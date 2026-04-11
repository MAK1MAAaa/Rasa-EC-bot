#!/usr/bin/env python
"""Filter SFT JSONL splits by allowed source values."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


READ_ENCODINGS = ("utf-8", "utf-8-sig", "gb18030", "gbk", "latin-1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter SFT JSONL by source.")
    parser.add_argument("--input-train", type=Path, default=Path("data/processed/train.jsonl"))
    parser.add_argument("--input-val", type=Path, default=Path("data/processed/val.jsonl"))
    parser.add_argument("--input-test", type=Path, default=Path("data/processed/test.jsonl"))
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--allowed-sources",
        type=str,
        default="ecommerce_dialogue_train,ecommerce_faq",
        help="Comma-separated allowed source values.",
    )
    return parser.parse_args()


def iter_lines_with_fallback(path: Path):
    last_error: UnicodeDecodeError | None = None
    for encoding in READ_ENCODINGS:
        try:
            with path.open("r", encoding=encoding) as f:
                for line in f:
                    yield line
            return
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error


def filter_file(input_path: Path, output_path: Path, allowed: set[str]) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kept_rows: list[str] = []
    total = 0
    parse_failed = 0
    kept = 0
    source_counter: Counter[str] = Counter()

    for raw_line in iter_lines_with_fallback(input_path):
        line = raw_line.strip()
        if not line:
            continue
        total += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            parse_failed += 1
            continue
        if not isinstance(obj, dict):
            parse_failed += 1
            continue
        source = str(obj.get("source", "")).strip()
        if source in allowed:
            kept_rows.append(line)
            kept += 1
            source_counter[source] += 1

    with output_path.open("w", encoding="utf-8") as f:
        for row in kept_rows:
            f.write(row + "\n")

    return {
        "input": str(input_path),
        "output": str(output_path),
        "total_rows": total,
        "parse_failed": parse_failed,
        "kept_rows": kept,
        "kept_source_distribution": dict(source_counter),
    }


def main() -> None:
    args = parse_args()
    allowed = {x.strip() for x in args.allowed_sources.split(",") if x.strip()}
    if not allowed:
        raise ValueError("--allowed-sources cannot be empty")

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    train_result = filter_file(args.input_train, out_dir / "train.jsonl", allowed)
    val_result = filter_file(args.input_val, out_dir / "val.jsonl", allowed)
    test_result = filter_file(args.input_test, out_dir / "test.jsonl", allowed)

    summary = {
        "allowed_sources": sorted(allowed),
        "train": train_result,
        "val": val_result,
        "test": test_result,
    }
    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Source filtering completed.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
