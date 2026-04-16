from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io_utils import DATASET_DIR, ROOT_DIR, write_json


DEFAULT_OUTPUT_DIR = DATASET_DIR
DEFAULT_SOURCE_DIR = DATASET_DIR
DEFAULT_RASA_NLU = ROOT_DIR / "rasa" / "data" / "nlu.yml"
DEFAULT_LORA_JSONL = [ROOT_DIR / "LoRA" / "data" / "processed" / "eval_prompts_20.jsonl"]
BUSINESS_FAMILIES = {"recommendation", "order_query", "logistics_query", "after_sales_query"}


@dataclass(frozen=True)
class DatasetBuildStats:
    tier: str
    total_count: int
    family_counts: dict[str, int]


def infer_layer_score_profile(scenario_family: str) -> tuple[str, str]:
    family = (scenario_family or "").strip()
    if family in BUSINESS_FAMILIES:
        return "business", "structured_business"
    return "boundary", "boundary_safe"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise RuntimeError(f"Dataset record must be an object: {path}:{line_no}")
            records.append(payload)
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _normalize_record(record: dict[str, Any], *, family: str, tier: str) -> dict[str, Any]:
    normalized = dict(record)
    normalized["scenario_family"] = str(normalized.get("scenario_family") or family).strip()
    normalized["tier"] = str(normalized.get("tier") or tier).strip()
    layer, score_profile = infer_layer_score_profile(normalized["scenario_family"])
    normalized["layer"] = str(normalized.get("layer") or layer).strip()
    normalized["score_profile"] = str(normalized.get("score_profile") or score_profile).strip()
    return normalized


def _collect_tier_records(source_dir: Path, tier: str) -> dict[str, list[dict[str, Any]]]:
    tier_dir = source_dir / tier
    if not tier_dir.exists():
        raise RuntimeError(f"Missing dataset tier directory: {tier_dir}")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(tier_dir.glob("*.jsonl")):
        family = path.stem
        grouped[family] = [_normalize_record(record, family=family, tier=tier) for record in _read_jsonl(path)]
    if not grouped:
        raise RuntimeError(f"No dataset files found under: {tier_dir}")
    return grouped


def _compute_stats(tier: str, grouped: dict[str, list[dict[str, Any]]]) -> DatasetBuildStats:
    family_counts = {family: len(records) for family, records in sorted(grouped.items())}
    return DatasetBuildStats(tier=tier, total_count=sum(family_counts.values()), family_counts=family_counts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="重建 benchmark 数据集目录与 manifest。")
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--rasa-nlu", type=Path, default=DEFAULT_RASA_NLU)
    parser.add_argument("--lora-jsonl", nargs="*", type=Path, default=DEFAULT_LORA_JSONL)
    parser.add_argument("--seed", type=int, default=20260412)
    return parser.parse_args()


def build_dataset(*, source_dir: Path, output_dir: Path, seed: int, rasa_nlu: Path, lora_jsonl: list[Path]) -> dict[str, Any]:
    outputs: dict[str, dict[str, str]] = {"core": {}, "extended": {}}
    stats_payload: dict[str, dict[str, Any]] = {}

    for tier in ("core", "extended"):
        grouped = _collect_tier_records(source_dir, tier)
        for family, records in grouped.items():
            path = output_dir / tier / f"{family}.jsonl"
            _write_jsonl(path, records)
            outputs[tier][family] = str(path)
        stats = _compute_stats(tier, grouped)
        stats_payload[tier] = {
            "total_count": stats.total_count,
            "family_counts": stats.family_counts,
        }

    manifest = {
        "seed": seed,
        "outputs": outputs,
        "sources": {
            "source_dir": str(source_dir),
            "rasa_nlu": str(rasa_nlu),
            "lora_jsonl": [str(path) for path in lora_jsonl],
        },
        "stats": stats_payload,
    }
    write_json(output_dir / "manifest.json", manifest, indent=2)
    return manifest


def main() -> None:
    args = parse_args()
    manifest = build_dataset(
        source_dir=args.source_dir.resolve(),
        output_dir=args.output_dir.resolve(),
        seed=args.seed,
        rasa_nlu=args.rasa_nlu.resolve(),
        lora_jsonl=[path.resolve() for path in args.lora_jsonl],
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
