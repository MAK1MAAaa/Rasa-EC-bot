from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
BENCHMARK_DIR = ROOT_DIR / "benchmark"
CONFIG_DIR = BENCHMARK_DIR / "config"
DATASET_DIR = BENCHMARK_DIR / "datasets"
RESULTS_DIR = BENCHMARK_DIR / "results"
DATA_DIR = BENCHMARK_DIR / "data"
ASSETS_DIR = BENCHMARK_DIR / "assets"
KB_SEED_DIR = BENCHMARK_DIR / "kb_seed"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def require_string(mapping: dict[str, Any], key: str, *, default: str = "") -> str:
    value = mapping.get(key, default)
    return str(value or "").strip()


def load_structured_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        import yaml  # type: ignore

        payload = yaml.safe_load(text)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Structured file must contain an object: {path}")
    return payload


def load_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON file must contain an object: {path}")
    return payload


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            pass
    return str(value)


def write_json(path: Path, payload: Any, *, indent: int | None = None) -> None:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=indent, default=_json_default), encoding="utf-8")


def write_jsonl(path: Path, records: list[Any]) -> None:
    ensure_directory(path.parent)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_directory(path.parent)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def render_markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "_无数据_"
    headers = list(rows[0].keys())
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)
