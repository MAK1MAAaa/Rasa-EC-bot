from __future__ import annotations

import argparse
import json
import math
import re
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from .io_utils import CONFIG_DIR, DATASET_DIR, load_json_file, load_structured_file, render_markdown_table, write_csv


DEFAULT_LABELS_PATH = CONFIG_DIR / "labels.zh-Hans.json"
DEFAULT_EXPERIMENT_CONFIG_PATH = CONFIG_DIR / "experiment.yaml"
SELECTION_MODE_DEFAULTS = {
    "quick": "sampled",
    "standard": "all_unique",
    "paper": "all_unique",
}
MULTI_LABEL_FAILURE_COLUMNS = [
    "missing_required_keywords",
    "contains_forbidden_keywords",
    "missing_required_cards",
    "missing_required_actions",
    "missing_confirmation_buttons",
    "missing_order_id",
    "hallucinated_order_id",
    "login_block_failure",
    "image_flow_failure",
    "pending_decision_failure",
    "technical_failure",
    "format_error",
]
CHART_PALETTE = ("#0b7285", "#1971c2", "#2f9e44", "#e67700", "#c2255c", "#5f3dc4", "#d9480f", "#1c7ed6")
REFERENCE_COLOR = "#adb5bd"
TRACK_COLOR = "#e9ecef"
GRID_COLOR = "#d0d7de"
TEXT_COLOR = "#1f2328"
SUBTLE_TEXT_COLOR = "#57606a"
BACKGROUND_COLOR = "#ffffff"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze benchmark result directory.")
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    return parser.parse_args()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _labels_section(labels: dict[str, Any], section: str) -> dict[str, Any]:
    value = labels.get(section)
    return value if isinstance(value, dict) else {}


def _label_of(mapping: dict[str, Any], key: str) -> str:
    return str(mapping.get(key) or key)


def _series_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _series_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _slugify(value: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "_", value).strip("_").lower()
    return slug or "chart"


def _format_percent(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    return f"{max(0.0, numeric) * 100:.1f}%"


def _chart_color(index: int) -> str:
    return CHART_PALETTE[index % len(CHART_PALETTE)]


def _write_svg(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_target_system(*, suite: str, system: str) -> bool:
    return not (suite == "agent_extension" and system == "rasa_only")


def _prepare_conversations(conversations: pd.DataFrame) -> pd.DataFrame:
    if conversations.empty:
        return conversations
    frame = conversations.copy()
    bool_columns = [
        "unsupported",
        "success",
        "conversation_success",
        "passed",
        "supported",
        "hallucination_free",
        *MULTI_LABEL_FAILURE_COLUMNS,
    ]
    for column in bool_columns:
        if column in frame.columns:
            frame[column] = _series_bool(frame[column])
    for column in ("latency_ms", "http_error_count", "repeat", "concurrency", "conversation_index", "turn_count", "executed_turns"):
        if column in frame.columns:
            frame[column] = _series_number(frame[column])
    if "benchmark_suite" not in frame.columns:
        frame["benchmark_suite"] = "shared_core"
    else:
        frame["benchmark_suite"] = frame["benchmark_suite"].fillna("shared_core")
    for column in ("scenario_family", "scenario", "sample_id", "system"):
        if column not in frame.columns:
            frame[column] = ""
        else:
            frame[column] = frame[column].fillna("")
    if "supported" not in frame.columns:
        frame["supported"] = ~frame["unsupported"]
    if "primary_failure_reason" not in frame.columns:
        frame["primary_failure_reason"] = ""
    frame["primary_failure_reason"] = frame["primary_failure_reason"].fillna("").astype(str)
    return frame


def _load_prompt_versions(result_dir: Path) -> list[dict[str, str]]:
    path = result_dir / "prompt_versions.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _infer_profile(result_dir: Path) -> str:
    name = result_dir.name.lower()
    for profile in ("paper", "standard", "quick"):
        if f"_{profile}_" in name or name.endswith(f"_{profile}_system_benchmark"):
            return profile
    return "standard"


def _resolve_selection_mode(profile: str, profile_cfg: dict[str, Any]) -> str:
    raw_mode = str(profile_cfg.get("selection_mode") or "").strip().lower()
    if raw_mode in {"sampled", "all_unique"}:
        return raw_mode
    return SELECTION_MODE_DEFAULTS.get(profile, "all_unique")


def _dataset_file_map(*, dataset_tier: str, scenario_families: list[str]) -> dict[str, str]:
    base_dir = (DATASET_DIR / dataset_tier).resolve()
    return {family: str((base_dir / f"{family}.jsonl").resolve()) for family in scenario_families}


def _load_dataset_samples(path: Path, profile: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            tags = {str(item).strip().lower() for item in payload.get("tags", []) if str(item).strip()}
            if "paper_only" in tags and profile != "paper":
                continue
            rows.append(
                {
                    "sample_id": str(payload.get("id") or "").strip(),
                    "benchmark_suite": str(payload.get("benchmark_suite") or "shared_core").strip(),
                    "scenario_family": str(payload.get("scenario_family") or payload.get("scenario") or path.stem).strip(),
                    "scenario": str(payload.get("scenario") or path.stem).strip(),
                    "tier": str(payload.get("tier") or path.parent.name).strip(),
                    "repeatable": bool(payload.get("repeatable", True)),
                }
            )
    return rows


def _load_run_metadata(result_dir: Path, conversations: pd.DataFrame) -> dict[str, Any]:
    metadata_path = result_dir / "run_metadata.json"
    if metadata_path.exists():
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload["metadata_source"] = "run_metadata"
            payload.setdefault("systems", sorted(conversations["system"].unique().tolist()) if not conversations.empty else [])
            payload.setdefault("expected_samples", [])
            payload.setdefault("sample_universe", [])
            return payload

    config = load_structured_file(DEFAULT_EXPERIMENT_CONFIG_PATH)
    profile = _infer_profile(result_dir)
    profiles = config.get("profiles") if isinstance(config.get("profiles"), dict) else {}
    profile_cfg = profiles.get(profile) if isinstance(profiles.get(profile), dict) else {}
    dataset_tier = str(profile_cfg.get("dataset_tier") or "core").strip()
    scenario_families = list(profile_cfg.get("scenarios") or sorted(conversations["scenario_family"].dropna().unique().tolist()))
    systems = sorted(conversations["system"].dropna().unique().tolist())
    selection_mode = _resolve_selection_mode(profile, profile_cfg)
    dataset_files = _dataset_file_map(dataset_tier=dataset_tier, scenario_families=scenario_families)
    sample_universe = [
        row
        for family, raw_path in dataset_files.items()
        for row in _load_dataset_samples(Path(raw_path), profile)
        if row["scenario_family"] == family
    ]

    if selection_mode == "all_unique":
        expected_samples = [{**row, "system": system, "selection_mode": selection_mode} for system in systems for row in sample_universe]
    else:
        executed_unique = conversations[["system", "benchmark_suite", "scenario_family", "scenario", "sample_id"]].drop_duplicates()
        universe_index = {(row["benchmark_suite"], row["scenario_family"], row["sample_id"]): row for row in sample_universe}
        expected_samples: list[dict[str, Any]] = []
        for row in executed_unique.to_dict(orient="records"):
            universe_row = universe_index.get((row["benchmark_suite"], row["scenario_family"], row["sample_id"]), {})
            expected_samples.append(
                {
                    "system": row["system"],
                    "benchmark_suite": row["benchmark_suite"],
                    "scenario_family": row["scenario_family"],
                    "scenario": row["scenario"],
                    "sample_id": row["sample_id"],
                    "tier": universe_row.get("tier", dataset_tier),
                    "repeatable": universe_row.get("repeatable", True),
                    "selection_mode": selection_mode,
                }
            )

    return {
        "profile": profile,
        "selection_mode": selection_mode,
        "dataset_tier": dataset_tier,
        "scenario_families": scenario_families,
        "systems": systems,
        "dataset_files": dataset_files,
        "sample_universe": sample_universe,
        "expected_samples": expected_samples,
        "metadata_source": "fallback_config",
    }


def _expected_unique_frame(metadata: dict[str, Any], conversations: pd.DataFrame) -> pd.DataFrame:
    rows = metadata.get("expected_samples")
    frame = pd.DataFrame(rows if isinstance(rows, list) else [])
    if frame.empty:
        if conversations.empty:
            return frame
        base = conversations[["system", "benchmark_suite", "scenario_family", "scenario", "sample_id"]].drop_duplicates()
        base["tier"] = metadata.get("dataset_tier", "")
        base["repeatable"] = True
        return base
    for column in ("system", "benchmark_suite", "scenario_family", "scenario", "sample_id", "tier"):
        if column not in frame.columns:
            frame[column] = ""
    if "repeatable" not in frame.columns:
        frame["repeatable"] = True
    return frame[["system", "benchmark_suite", "scenario_family", "scenario", "sample_id", "tier", "repeatable"]].drop_duplicates()


def _build_sample_aggregates(conversations: pd.DataFrame) -> pd.DataFrame:
    if conversations.empty:
        return pd.DataFrame(
            columns=[
                "system",
                "benchmark_suite",
                "scenario_family",
                "scenario",
                "sample_id",
                "attempts",
                "passed_attempts",
                "conversation_success_attempts",
                "supported_attempts",
                "sample_pass_rate",
                "sample_success_rate",
                "sample_eligible",
                "sample_stability",
            ]
        )

    grouped = (
        conversations.groupby(["system", "benchmark_suite", "scenario_family", "sample_id"], dropna=False)
        .agg(
            scenario=("scenario", "first"),
            attempts=("sample_id", "size"),
            passed_attempts=("passed", "sum"),
            conversation_success_attempts=("conversation_success", "sum"),
            supported_attempts=("supported", "sum"),
            min_pass=("passed", "min"),
            max_pass=("passed", "max"),
        )
        .reset_index()
    )
    grouped["sample_pass_rate"] = (grouped["passed_attempts"] / grouped["attempts"]).round(4)
    grouped["sample_success_rate"] = (grouped["conversation_success_attempts"] / grouped["attempts"]).round(4)
    grouped["sample_eligible"] = grouped["supported_attempts"] > 0
    grouped["sample_stability"] = grouped.apply(
        lambda row: 1.0 if int(row["attempts"]) <= 1 or bool(row["min_pass"] == row["max_pass"]) else 0.0,
        axis=1,
    )
    return grouped


def _join_expected_and_actual(expected_unique: pd.DataFrame, sample_agg: pd.DataFrame) -> pd.DataFrame:
    if expected_unique.empty:
        merged = sample_agg.copy()
        if merged.empty:
            return merged
        merged["tier"] = ""
        merged["repeatable"] = True
        merged["executed"] = True
        return merged

    merged = expected_unique.merge(
        sample_agg,
        how="left",
        on=["system", "benchmark_suite", "scenario_family", "sample_id"],
        suffixes=("_expected", ""),
    )
    merged["scenario"] = merged["scenario"].fillna(merged.get("scenario_expected", ""))
    for column, value in {
        "attempts": 0,
        "passed_attempts": 0,
        "conversation_success_attempts": 0,
        "supported_attempts": 0,
        "sample_pass_rate": 0.0,
        "sample_success_rate": 0.0,
        "sample_stability": 0.0,
    }.items():
        if column in merged.columns:
            merged[column] = merged[column].fillna(value)
    merged["sample_eligible"] = _series_bool(merged["sample_eligible"]) if "sample_eligible" in merged.columns else False
    merged["executed"] = merged["attempts"] > 0
    if "repeatable" not in merged.columns:
        merged["repeatable"] = True
    if "tier" not in merged.columns:
        merged["tier"] = ""
    return merged[
        [
            "system",
            "benchmark_suite",
            "scenario_family",
            "scenario",
            "sample_id",
            "tier",
            "repeatable",
            "attempts",
            "passed_attempts",
            "conversation_success_attempts",
            "supported_attempts",
            "sample_pass_rate",
            "sample_success_rate",
            "sample_eligible",
            "sample_stability",
            "executed",
        ]
    ]


def _build_sample_coverage(expected_joined: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if expected_joined.empty:
        return pd.DataFrame(rows)
    suite_labels = _labels_section(labels, "suites")
    scenario_labels = _labels_section(labels, "scenarios")
    system_labels = _labels_section(labels, "systems")
    for (suite, system, scenario_family), scoped in expected_joined.groupby(["benchmark_suite", "system", "scenario_family"], dropna=False):
        expected_ids = sorted(str(item) for item in scoped["sample_id"].tolist())
        executed_ids = sorted(str(item) for item in scoped.loc[scoped["executed"], "sample_id"].tolist())
        missing_ids = sorted(set(expected_ids).difference(executed_ids))
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, str(suite)),
                "system": system,
                "system_label": _label_of(system_labels, str(system)),
                "scenario_family": scenario_family,
                "scenario_label": _label_of(scenario_labels, str(scenario_family)),
                "expected_unique_samples": len(expected_ids),
                "executed_unique_samples": len(executed_ids),
                "coverage_rate": round(len(executed_ids) / max(1, len(expected_ids)), 4),
                "expected_sample_ids": ";".join(expected_ids),
                "executed_sample_ids": ";".join(executed_ids),
                "missing_sample_ids": ";".join(missing_ids),
            }
        )
    return pd.DataFrame(rows).sort_values(["suite", "scenario_family", "system_label"]).reset_index(drop=True)


def _build_family_metrics(expected_joined: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if expected_joined.empty:
        return pd.DataFrame(rows)
    suite_labels = _labels_section(labels, "suites")
    scenario_labels = _labels_section(labels, "scenarios")
    system_labels = _labels_section(labels, "systems")
    for (suite, system, scenario_family), scoped in expected_joined.groupby(["benchmark_suite", "system", "scenario_family"], dropna=False):
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, str(suite)),
                "system": system,
                "system_label": _label_of(system_labels, str(system)),
                "scenario_family": scenario_family,
                "scenario_label": _label_of(scenario_labels, str(scenario_family)),
                "family_unique_samples": int(len(scoped)),
                "executed_unique_samples": int(scoped["executed"].sum()),
                "coverage_rate": round(float(scoped["executed"].mean()), 4),
                "family_pass_rate": round(float(scoped["sample_pass_rate"].mean()), 4),
                "family_success_rate": round(float(scoped["sample_success_rate"].mean()), 4),
                "family_eligibility_rate": round(float(scoped["sample_eligible"].mean()), 4),
            }
        )
    return pd.DataFrame(rows).sort_values(["suite", "scenario_family", "system_label"]).reset_index(drop=True)


def _wilson_interval(p_hat: float, n: int, *, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return (0.0, 0.0)
    denominator = 1 + (z * z) / n
    center = (p_hat + (z * z) / (2 * n)) / denominator
    margin = (z / denominator) * math.sqrt((p_hat * (1 - p_hat) / n) + ((z * z) / (4 * n * n)))
    return (round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4))


def _repeat_stability_by_suite(sample_agg: pd.DataFrame) -> dict[tuple[str, str], float]:
    if sample_agg.empty:
        return {}
    values: dict[tuple[str, str], float] = {}
    for (suite, system), scoped in sample_agg.groupby(["benchmark_suite", "system"], dropna=False):
        repeated = scoped[scoped["attempts"] > 1]
        values[(str(suite), str(system))] = 1.0 if repeated.empty else round(float(repeated["sample_stability"].mean()), 4)
    return values


def _sort_suite_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    ordered = frame.sort_values(
        ["suite", "is_target_system", "suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_family_macro_success_rate", "eligibility_rate", "system_label"],
        ascending=[True, False, False, False, False, False, True],
    ).reset_index(drop=True)
    ranks: list[int | str] = []
    current_suite = ""
    rank = 0
    for row in ordered.itertuples(index=False):
        if row.suite != current_suite:
            current_suite = row.suite
            rank = 0
        if bool(row.is_target_system):
            rank += 1
            ranks.append(rank)
        else:
            ranks.append("")
    ordered.insert(0, "rank", ranks)
    return ordered


def _build_suite_metrics(
    expected_joined: pd.DataFrame,
    family_metrics: pd.DataFrame,
    sample_agg: pd.DataFrame,
    conversations: pd.DataFrame,
    labels: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if expected_joined.empty:
        return pd.DataFrame(rows)
    suite_labels = _labels_section(labels, "suites")
    system_labels = _labels_section(labels, "systems")
    repeat_stability = _repeat_stability_by_suite(sample_agg)
    raw_metrics = (
        conversations.groupby(["benchmark_suite", "system"], dropna=False)
        .agg(conversations=("sample_id", "size"), supported_conversations=("supported", "sum"), passed_total=("passed", "sum"), conversation_success_rate=("conversation_success", "mean"))
        .reset_index()
    )
    raw_index = {(str(row["benchmark_suite"]), str(row["system"])): row for row in raw_metrics.to_dict(orient="records")}
    family_index = {
        (str(row["suite"]), str(row["system"])): row
        for row in family_metrics.groupby(["suite", "system"], dropna=False)
        .agg(suite_family_macro_pass_rate=("family_pass_rate", "mean"), suite_family_macro_success_rate=("family_success_rate", "mean"))
        .reset_index()
        .to_dict(orient="records")
    }
    for (suite, system), scoped in expected_joined.groupby(["benchmark_suite", "system"], dropna=False):
        suite = str(suite)
        system = str(system)
        expected_unique_samples = int(len(scoped))
        executed_unique_samples = int(scoped["executed"].sum())
        suite_unique_micro_pass_rate = round(float(scoped["sample_pass_rate"].mean()), 4)
        ci_low, ci_high = _wilson_interval(suite_unique_micro_pass_rate, expected_unique_samples)
        raw_row = raw_index.get((suite, system), {})
        family_row = family_index.get((suite, system), {})
        conversations_count = int(raw_row.get("conversations", 0))
        supported_conversations = int(raw_row.get("supported_conversations", 0))
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, suite),
                "system": system,
                "system_label": _label_of(system_labels, system),
                "is_target_system": _is_target_system(suite=suite, system=system),
                "expected_unique_samples": expected_unique_samples,
                "executed_unique_samples": executed_unique_samples,
                "coverage_rate": round(executed_unique_samples / max(1, expected_unique_samples), 4),
                "suite_family_macro_pass_rate": round(float(family_row.get("suite_family_macro_pass_rate", 0.0)), 4),
                "suite_unique_micro_pass_rate": suite_unique_micro_pass_rate,
                "suite_unique_micro_pass_rate_ci_low": ci_low,
                "suite_unique_micro_pass_rate_ci_high": ci_high,
                "suite_family_macro_success_rate": round(float(family_row.get("suite_family_macro_success_rate", 0.0)), 4),
                "eligibility_rate": round(float(scoped["sample_eligible"].mean()), 4),
                "repeat_stability": repeat_stability.get((suite, system), 1.0),
                "conversations": conversations_count,
                "supported_conversations": supported_conversations,
                "support_rate": round(supported_conversations / max(1, conversations_count), 4),
                "suite_pass_rate": round(float(raw_row.get("passed_total", 0)) / max(1, conversations_count), 4),
                "supported_quality_pass_rate": round(float(raw_row.get("passed_total", 0)) / max(1, supported_conversations), 4),
                "conversation_success_rate": round(float(raw_row.get("conversation_success_rate", 0.0)), 4),
            }
        )
    return _sort_suite_metrics(pd.DataFrame(rows))


def _build_suite_scenario_leaders(family_metrics: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if family_metrics.empty:
        return pd.DataFrame(rows)
    scenario_labels = _labels_section(labels, "scenarios")
    suite_labels = _labels_section(labels, "suites")
    for (suite, scenario_family), scoped in family_metrics.groupby(["suite", "scenario_family"], dropna=False):
        scoped = scoped.copy()
        scoped["is_target_system"] = scoped.apply(lambda row: _is_target_system(suite=str(row["suite"]), system=str(row["system"])), axis=1)
        target_scoped = scoped[scoped["is_target_system"]]
        leaderboard = target_scoped if not target_scoped.empty else scoped
        if leaderboard.empty:
            continue
        highest_pass = float(leaderboard["family_pass_rate"].max())
        if highest_pass <= 0:
            rows.append(
                {
                    "suite": suite,
                    "suite_label": _label_of(suite_labels, str(suite)),
                    "scenario_family": scenario_family,
                    "scenario_label": _label_of(scenario_labels, str(scenario_family)),
                    "leader_status": "no_pass",
                    "leader_system": "",
                    "leader_system_label": "",
                    "leader_family_pass_rate": 0.0,
                    "leader_family_success_rate": 0.0,
                    "leader_coverage_rate": round(float(leaderboard["coverage_rate"].max()), 4),
                }
            )
            continue
        leader = leaderboard.sort_values(["family_pass_rate", "family_success_rate", "family_eligibility_rate", "system_label"], ascending=[False, False, False, True]).iloc[0]
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, str(suite)),
                "scenario_family": scenario_family,
                "scenario_label": _label_of(scenario_labels, str(scenario_family)),
                "leader_status": "leader",
                "leader_system": leader["system"],
                "leader_system_label": leader["system_label"],
                "leader_family_pass_rate": leader["family_pass_rate"],
                "leader_family_success_rate": leader["family_success_rate"],
                "leader_coverage_rate": leader["coverage_rate"],
            }
        )
    return pd.DataFrame(rows).sort_values(["suite", "scenario_family"]).reset_index(drop=True)


def _build_failure_breakdown(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if conversations.empty:
        return pd.DataFrame(rows)
    failure_labels = _labels_section(labels, "failures")
    suite_labels = _labels_section(labels, "suites")
    system_labels = _labels_section(labels, "systems")
    scoped = conversations[conversations["primary_failure_reason"].astype(str) != ""]
    if scoped.empty:
        return pd.DataFrame(rows)
    total_failures = scoped.groupby(["benchmark_suite", "system"], dropna=False).size().rename("total_failures").reset_index()
    total_index = {(str(row["benchmark_suite"]), str(row["system"])): int(row["total_failures"]) for row in total_failures.to_dict(orient="records")}
    breakdown = scoped.groupby(["benchmark_suite", "system", "primary_failure_reason"], dropna=False).size().rename("count").reset_index()
    for row in breakdown.to_dict(orient="records"):
        suite = str(row["benchmark_suite"])
        system = str(row["system"])
        reason = str(row["primary_failure_reason"])
        count = int(row["count"])
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, suite),
                "system": system,
                "system_label": _label_of(system_labels, system),
                "primary_failure_reason": reason,
                "primary_failure_label": _label_of(failure_labels, reason),
                "count": count,
                "failure_rate": round(count / max(1, total_index.get((suite, system), 0)), 4),
            }
        )
    return pd.DataFrame(rows).sort_values(["suite", "system_label", "count", "primary_failure_label"], ascending=[True, True, False, True]).reset_index(drop=True)


def _build_failure_flags(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if conversations.empty:
        return pd.DataFrame(rows)
    suite_labels = _labels_section(labels, "suites")
    system_labels = _labels_section(labels, "systems")
    for (suite, system), scoped in conversations.groupby(["benchmark_suite", "system"], dropna=False):
        failed_supported = scoped[(scoped["supported"]) & (~scoped["passed"])]
        row: dict[str, Any] = {
            "suite": suite,
            "suite_label": _label_of(suite_labels, str(suite)),
            "system": system,
            "system_label": _label_of(system_labels, str(system)),
            "failed_supported_conversations": int(len(failed_supported)),
            "unsupported_conversations": int(scoped["unsupported"].sum()),
        }
        for column in MULTI_LABEL_FAILURE_COLUMNS:
            row[column] = int(failed_supported[column].sum()) if column in failed_supported.columns else 0
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["suite", "system_label"]).reset_index(drop=True)


def _build_confidence_notes(suite_metrics: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if suite_metrics.empty:
        return pd.DataFrame(rows)
    suite_labels = _labels_section(labels, "suites")
    for suite, scoped in suite_metrics.groupby("suite", dropna=False):
        target = scoped[scoped["is_target_system"]]
        leaderboard = target if not target.empty else scoped
        ordered = leaderboard.sort_values(["suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_family_macro_success_rate", "eligibility_rate", "system_label"], ascending=[False, False, False, False, True]).reset_index(drop=True)
        if len(ordered) < 2:
            leader = ordered.iloc[0]
            rows.append(
                {
                    "suite": suite,
                    "suite_label": _label_of(suite_labels, str(suite)),
                    "leader_system_label": leader["system_label"],
                    "runner_up_system_label": "",
                    "leader_rate": leader["suite_unique_micro_pass_rate"],
                    "runner_up_rate": "",
                    "gap_note": "Not enough systems to assess stability",
                }
            )
            continue
        leader = ordered.iloc[0]
        runner_up = ordered.iloc[1]
        separated = float(leader["suite_unique_micro_pass_rate_ci_low"]) > float(runner_up["suite_unique_micro_pass_rate_ci_high"])
        rows.append(
            {
                "suite": suite,
                "suite_label": _label_of(suite_labels, str(suite)),
                "leader_system_label": leader["system_label"],
                "runner_up_system_label": runner_up["system_label"],
                "leader_rate": leader["suite_unique_micro_pass_rate"],
                "runner_up_rate": runner_up["suite_unique_micro_pass_rate"],
                "gap_note": "Wilson 95% CI separated" if separated else "Wilson 95% CI overlaps",
            }
        )
    return pd.DataFrame(rows).sort_values(["suite"]).reset_index(drop=True)


def _build_suite_chart_svg(*, suite_metrics: pd.DataFrame, suite: str, labels: dict[str, Any]) -> str | None:
    scoped = suite_metrics[suite_metrics["suite"] == suite].copy()
    if scoped.empty:
        return None
    scoped = scoped.sort_values(["is_target_system", "suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_family_macro_success_rate", "eligibility_rate", "system_label"], ascending=[False, False, False, False, False, True]).reset_index(drop=True)
    suite_label = _label_of(_labels_section(labels, "suites"), suite)
    width = 1080
    top = 96
    row_height = 92
    bottom = 56
    left = 340
    right = 120
    plot_width = width - left - right
    plot_height = len(scoped) * row_height
    height = top + plot_height + bottom
    max_value = max(1.0, float(scoped["suite_family_macro_pass_rate"].max()))
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(suite_label)} ranking">',
        f'<rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}" />',
        f'<text x="40" y="42" font-size="28" font-weight="700" fill="{TEXT_COLOR}">{escape(suite_label)} ranking</text>',
        f'<text x="40" y="70" font-size="14" fill="{SUBTLE_TEXT_COLOR}">Primary metric: suite_family_macro_pass_rate.</text>',
    ]
    for tick in range(5):
        ratio = tick / 4
        x = left + ratio * plot_width
        lines.append(f'<line x1="{x:.1f}" y1="{top - 10}" x2="{x:.1f}" y2="{top + plot_height}" stroke="{GRID_COLOR}" stroke-dasharray="4 4" />')
        lines.append(f'<text x="{x:.1f}" y="{top - 18}" font-size="12" text-anchor="middle" fill="{SUBTLE_TEXT_COLOR}">{ratio * max_value * 100:.0f}%</text>')
    for index, row in enumerate(scoped.itertuples(index=False)):
        y = top + index * row_height
        bar_y = y + 24
        label = str(row.system_label)
        if not bool(row.is_target_system):
            label = f"{label} (baseline)"
        bar_length = 0.0 if max_value <= 0 else plot_width * float(row.suite_family_macro_pass_rate) / max_value
        note = (
            f"macro { _format_percent(row.suite_family_macro_pass_rate) } | "
            f"micro { _format_percent(row.suite_unique_micro_pass_rate) } | "
            f"coverage { _format_percent(row.coverage_rate) } | "
            f"stability { _format_percent(row.repeat_stability) }"
        )
        lines.extend(
            [
                f'<text x="{left - 16}" y="{bar_y + 15}" font-size="16" font-weight="600" text-anchor="end" fill="{TEXT_COLOR}">{escape(label)}</text>',
                f'<rect x="{left}" y="{bar_y}" width="{plot_width}" height="22" rx="10" fill="{TRACK_COLOR}" />',
                f'<rect x="{left}" y="{bar_y}" width="{bar_length:.1f}" height="22" rx="10" fill="{_chart_color(index) if bool(row.is_target_system) else REFERENCE_COLOR}" />',
                f'<text x="{left + bar_length + 10:.1f}" y="{bar_y + 15}" font-size="14" fill="{TEXT_COLOR}">{_format_percent(row.suite_family_macro_pass_rate)}</text>',
                f'<text x="{left}" y="{bar_y + 47}" font-size="13" fill="{SUBTLE_TEXT_COLOR}">{escape(note)}</text>',
            ]
        )
    lines.append("</svg>")
    return "\n".join(lines)


def _polar_to_cartesian(cx: float, cy: float, radius: float, angle_deg: float) -> tuple[float, float]:
    radians = math.radians(angle_deg)
    return (cx + radius * math.cos(radians), cy + radius * math.sin(radians))


def _pie_slice_path(cx: float, cy: float, radius: float, start_angle: float, end_angle: float) -> str:
    start_x, start_y = _polar_to_cartesian(cx, cy, radius, start_angle)
    end_x, end_y = _polar_to_cartesian(cx, cy, radius, end_angle)
    large_arc_flag = 1 if end_angle - start_angle > 180 else 0
    return f"M {cx:.2f} {cy:.2f} L {start_x:.2f} {start_y:.2f} A {radius:.2f} {radius:.2f} 0 {large_arc_flag} 1 {end_x:.2f} {end_y:.2f} Z"


def _build_exclusive_failure_pie_svg(*, failure_breakdown: pd.DataFrame) -> str | None:
    if failure_breakdown.empty:
        return None
    totals = failure_breakdown.groupby("primary_failure_label", dropna=False)["count"].sum().sort_values(ascending=False)
    slices = [(str(label), int(value)) for label, value in totals.items() if int(value) > 0]
    if not slices:
        return None
    total = sum(value for _, value in slices)
    width = 980
    height = 560
    center_x = 250
    center_y = 290
    radius = 150
    legend_x = 470
    legend_y = 130
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="exclusive failure pie">',
        f'<rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}" />',
        f'<text x="40" y="42" font-size="28" font-weight="700" fill="{TEXT_COLOR}">Exclusive failure reasons</text>',
        f'<text x="40" y="70" font-size="14" fill="{SUBTLE_TEXT_COLOR}">The pie total equals the failed conversation count.</text>',
    ]
    current_angle = -90.0
    for index, (label, value) in enumerate(slices):
        angle = (value / total) * 360.0
        lines.append(f'<path d="{_pie_slice_path(center_x, center_y, radius, current_angle, current_angle + angle)}" fill="{_chart_color(index)}" />')
        current_angle += angle
        y = legend_y + index * 54
        lines.extend(
            [
                f'<rect x="{legend_x}" y="{y}" width="20" height="20" rx="4" fill="{_chart_color(index)}" />',
                f'<text x="{legend_x + 32}" y="{y + 15}" font-size="16" font-weight="600" fill="{TEXT_COLOR}">{escape(label)}</text>',
                f'<text x="{legend_x + 32}" y="{y + 36}" font-size="13" fill="{SUBTLE_TEXT_COLOR}">{_format_percent(value / max(1, total))} ({value})</text>',
            ]
        )
    lines.extend(
        [
            f'<circle cx="{center_x}" cy="{center_y}" r="74" fill="{BACKGROUND_COLOR}" />',
            f'<text x="{center_x}" y="{center_y - 4}" text-anchor="middle" font-size="16" font-weight="700" fill="{TEXT_COLOR}">Failures</text>',
            f'<text x="{center_x}" y="{center_y + 24}" text-anchor="middle" font-size="28" font-weight="700" fill="{TEXT_COLOR}">{total}</text>',
            "</svg>",
        ]
    )
    return "\n".join(lines)


def _build_failure_flags_bar_svg(*, failure_flags: pd.DataFrame, labels: dict[str, Any]) -> str | None:
    if failure_flags.empty:
        return None
    failure_labels = _labels_section(labels, "failures")
    totals = [(_label_of(failure_labels, column), int(failure_flags[column].sum())) for column in MULTI_LABEL_FAILURE_COLUMNS if column in failure_flags.columns and int(failure_flags[column].sum()) > 0]
    totals.sort(key=lambda item: item[1], reverse=True)
    if not totals:
        return None
    width = 1080
    top = 96
    row_height = 72
    bottom = 48
    left = 320
    right = 120
    plot_width = width - left - right
    plot_height = len(totals) * row_height
    height = top + plot_height + bottom
    max_value = max(value for _, value in totals)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="failure flags bar">',
        f'<rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}" />',
        f'<text x="40" y="42" font-size="28" font-weight="700" fill="{TEXT_COLOR}">Multi-label failure flags</text>',
        f'<text x="40" y="70" font-size="14" fill="{SUBTLE_TEXT_COLOR}">Diagnostic counts only.</text>',
    ]
    for index, (label, value) in enumerate(totals):
        y = top + index * row_height
        bar_y = y + 18
        bar_length = 0.0 if max_value <= 0 else plot_width * value / max_value
        lines.extend(
            [
                f'<text x="{left - 16}" y="{bar_y + 17}" font-size="16" font-weight="600" text-anchor="end" fill="{TEXT_COLOR}">{escape(label)}</text>',
                f'<rect x="{left}" y="{bar_y}" width="{plot_width}" height="24" rx="10" fill="{TRACK_COLOR}" />',
                f'<rect x="{left}" y="{bar_y}" width="{bar_length:.1f}" height="24" rx="10" fill="{_chart_color(index)}" />',
                f'<text x="{left + bar_length + 10:.1f}" y="{bar_y + 17}" font-size="14" fill="{TEXT_COLOR}">{value}</text>',
            ]
        )
    lines.append("</svg>")
    return "\n".join(lines)


def _build_chart_artifacts(*, analysis_dir: Path, suite_metrics: pd.DataFrame, failure_breakdown: pd.DataFrame, failure_flags: pd.DataFrame, labels: dict[str, Any]) -> list[dict[str, str]]:
    charts_dir = analysis_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    suite_labels = _labels_section(labels, "suites")
    artifacts: list[dict[str, str]] = []
    for suite in ("shared_core", "agent_extension"):
        svg = _build_suite_chart_svg(suite_metrics=suite_metrics, suite=suite, labels=labels)
        if svg is None:
            continue
        filename = f"{_slugify(suite)}_ranking.svg"
        _write_svg(charts_dir / filename, svg)
        artifacts.append({"title": f"{_label_of(suite_labels, suite)} ranking", "path": f"charts/{filename}"})
    pie_svg = _build_exclusive_failure_pie_svg(failure_breakdown=failure_breakdown)
    if pie_svg is not None:
        filename = "exclusive_failure_pie.svg"
        _write_svg(charts_dir / filename, pie_svg)
        artifacts.append({"title": "Exclusive failure pie", "path": f"charts/{filename}"})
    bar_svg = _build_failure_flags_bar_svg(failure_flags=failure_flags, labels=labels)
    if bar_svg is not None:
        filename = "failure_flags_bar.svg"
        _write_svg(charts_dir / filename, bar_svg)
        artifacts.append({"title": "Failure flags bar", "path": f"charts/{filename}"})
    return artifacts


def _table_subset(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    keep = [column for column in columns if column in frame.columns]
    return frame[keep].to_dict(orient="records")


def _render_report(*, analysis_dir: Path, metadata: dict[str, Any], suite_metrics: pd.DataFrame, family_metrics: pd.DataFrame, sample_coverage: pd.DataFrame, scenario_leaders: pd.DataFrame, failure_breakdown: pd.DataFrame, failure_flags: pd.DataFrame, confidence_notes: pd.DataFrame, prompt_versions: list[dict[str, str]], chart_artifacts: list[dict[str, str]]) -> str:
    shared_core_rows = suite_metrics[(suite_metrics["suite"] == "shared_core") & (suite_metrics["is_target_system"])]
    agent_target_rows = suite_metrics[(suite_metrics["suite"] == "agent_extension") & (suite_metrics["is_target_system"])]
    agent_baseline_rows = suite_metrics[(suite_metrics["suite"] == "agent_extension") & (~suite_metrics["is_target_system"])]
    repeat_rows = suite_metrics[["suite_label", "system_label", "repeat_stability", "suite_unique_micro_pass_rate", "suite_unique_micro_pass_rate_ci_low", "suite_unique_micro_pass_rate_ci_high"]] if not suite_metrics.empty else pd.DataFrame()
    lines = [
        "# Benchmark Analysis Report",
        "",
        f"Result Dir: `{analysis_dir.parent}`",
        f"Profile: `{metadata.get('profile', '')}`",
        f"Selection Mode: `{metadata.get('selection_mode', '')}`",
        f"Metadata Source: `{metadata.get('metadata_source', 'unknown')}`",
        "",
        "Ranking rule: `suite_family_macro_pass_rate > suite_unique_micro_pass_rate > suite_family_macro_success_rate > eligibility_rate`.",
        "`suite_pass_rate` is preserved as a raw attempt debug field only.",
        "",
    ]
    if prompt_versions:
        lines.extend(["## Prompt Versions", "", render_markdown_table(prompt_versions), ""])
    if chart_artifacts:
        lines.extend(["## Charts", ""])
        for chart in chart_artifacts:
            lines.extend([f"### {chart['title']}", "", f"![{chart['title']}]({chart['path']})", ""])
    lines.extend(
        [
            "## Coverage",
            "",
            render_markdown_table(_table_subset(sample_coverage, ["suite_label", "system_label", "scenario_label", "expected_unique_samples", "executed_unique_samples", "coverage_rate", "missing_sample_ids"])),
            "",
            "## shared_core Ranking",
            "",
            render_markdown_table(_table_subset(shared_core_rows, ["rank", "system_label", "expected_unique_samples", "executed_unique_samples", "coverage_rate", "suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_unique_micro_pass_rate_ci_low", "suite_unique_micro_pass_rate_ci_high", "suite_family_macro_success_rate", "eligibility_rate", "repeat_stability", "suite_pass_rate"])),
            "",
            "## agent_extension Ranking",
            "",
            render_markdown_table(_table_subset(agent_target_rows, ["rank", "system_label", "expected_unique_samples", "executed_unique_samples", "coverage_rate", "suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_unique_micro_pass_rate_ci_low", "suite_unique_micro_pass_rate_ci_high", "suite_family_macro_success_rate", "eligibility_rate", "repeat_stability", "suite_pass_rate"])),
            "",
        ]
    )
    if not agent_baseline_rows.empty:
        lines.extend(["### agent_extension Baseline", "", render_markdown_table(_table_subset(agent_baseline_rows, ["system_label", "coverage_rate", "suite_family_macro_pass_rate", "suite_unique_micro_pass_rate", "suite_family_macro_success_rate", "eligibility_rate", "repeat_stability", "suite_pass_rate"])), ""])
    lines.extend(
        [
            "## Family Metrics",
            "",
            render_markdown_table(_table_subset(family_metrics, ["suite_label", "scenario_label", "system_label", "family_unique_samples", "executed_unique_samples", "coverage_rate", "family_pass_rate", "family_success_rate", "family_eligibility_rate"])),
            "",
            "## Stability And CI Notes",
            "",
            render_markdown_table(repeat_rows.to_dict(orient="records")),
            "",
            render_markdown_table(confidence_notes.to_dict(orient="records")),
            "",
            "## Scenario Leaders",
            "",
            render_markdown_table(scenario_leaders.to_dict(orient="records")),
            "",
            "## Exclusive Failure Breakdown",
            "",
            render_markdown_table(failure_breakdown.to_dict(orient="records")),
            "",
            "## Multi-label Failure Flags",
            "",
            render_markdown_table(failure_flags.to_dict(orient="records")),
            "",
            "## Notes",
            "",
            "- Coverage uses expected unique sample ids.",
            "- `leader_status = no_pass` means no system achieved a positive family pass rate.",
            "- Wilson 95% CI is used for stability notes only.",
            "- `failure_breakdown.csv` is exclusive; `failure_flags.csv` keeps multi-label diagnostics.",
            "",
            f"Analysis Dir: `{analysis_dir}`",
        ]
    )
    return "\n".join(lines)


def analyze_result_dir(*, result_dir: Path, labels_path: Path) -> Path:
    labels = load_json_file(labels_path)
    result_dir = result_dir.resolve()
    analysis_dir = result_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    conversations = _prepare_conversations(_load_csv(result_dir / "conversation_summary.csv"))
    metadata = _load_run_metadata(result_dir, conversations)
    expected_unique = _expected_unique_frame(metadata, conversations)
    sample_agg = _build_sample_aggregates(conversations)
    expected_joined = _join_expected_and_actual(expected_unique, sample_agg)
    sample_coverage = _build_sample_coverage(expected_joined, labels)
    family_metrics = _build_family_metrics(expected_joined, labels)
    suite_metrics = _build_suite_metrics(expected_joined, family_metrics, sample_agg, conversations, labels)
    scenario_leaders = _build_suite_scenario_leaders(family_metrics, labels)
    failure_breakdown = _build_failure_breakdown(conversations, labels)
    failure_flags = _build_failure_flags(conversations, labels)
    confidence_notes = _build_confidence_notes(suite_metrics, labels)
    prompt_versions = _load_prompt_versions(result_dir)
    chart_artifacts = _build_chart_artifacts(analysis_dir=analysis_dir, suite_metrics=suite_metrics, failure_breakdown=failure_breakdown, failure_flags=failure_flags, labels=labels)
    write_csv(analysis_dir / "suite_metrics.csv", suite_metrics.to_dict(orient="records"))
    write_csv(analysis_dir / "family_metrics.csv", family_metrics.to_dict(orient="records"))
    write_csv(analysis_dir / "sample_coverage.csv", sample_coverage.to_dict(orient="records"))
    write_csv(analysis_dir / "suite_scenario_leaders.csv", scenario_leaders.to_dict(orient="records"))
    write_csv(analysis_dir / "failure_breakdown.csv", failure_breakdown.to_dict(orient="records"))
    write_csv(analysis_dir / "failure_flags.csv", failure_flags.to_dict(orient="records"))
    (analysis_dir / "report.md").write_text(
        _render_report(
            analysis_dir=analysis_dir,
            metadata=metadata,
            suite_metrics=suite_metrics,
            family_metrics=family_metrics,
            sample_coverage=sample_coverage,
            scenario_leaders=scenario_leaders,
            failure_breakdown=failure_breakdown,
            failure_flags=failure_flags,
            confidence_notes=confidence_notes,
            prompt_versions=prompt_versions,
            chart_artifacts=chart_artifacts,
        ),
        encoding="utf-8",
    )
    return analysis_dir


def main() -> None:
    args = parse_args()
    analysis_dir = analyze_result_dir(result_dir=args.result_dir, labels_path=args.labels)
    print(json.dumps({"analysis_dir": str(analysis_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
