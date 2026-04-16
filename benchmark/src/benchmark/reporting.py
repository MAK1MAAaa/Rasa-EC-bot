from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from .conclusions import build_conclusions
from .io_utils import CONFIG_DIR, load_json_file, render_markdown_table, write_csv, write_json
from .plotting import (
    plot_bar_chart,
    plot_grouped_bar_chart,
    plot_heatmap,
    plot_latency_by_concurrency,
    plot_quality_latency_scatter,
    plot_stacked_bar_chart,
)


DEFAULT_LABELS_PATH = CONFIG_DIR / "labels.zh-Hans.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分析 benchmark 结果目录并生成图表、结论与 Markdown 报告。")
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS_PATH)
    return parser.parse_args()


def _load_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def _label_of(mapping: dict[str, Any], key: str) -> str:
    return str(mapping.get(key) or key)


def _series_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def _labels_section(labels: dict[str, Any], section: str) -> dict[str, Any]:
    value = labels.get(section)
    return value if isinstance(value, dict) else {}


def _text(labels: dict[str, Any], section: str, key: str, fallback: str) -> str:
    return str(_labels_section(labels, section).get(key) or fallback)


def _prepare_conversations(conversations: pd.DataFrame) -> pd.DataFrame:
    if conversations.empty:
        return conversations
    frame = conversations.copy()
    bool_columns = [
        "unsupported",
        "success",
        "conversation_success",
        "passed",
        "hallucination_free",
        "hallucinated_order_id",
    ]
    for column in bool_columns:
        if column in frame.columns:
            frame[column] = _series_bool(frame[column])
    if "latency_ms" in frame.columns:
        frame["latency_ms"] = pd.to_numeric(frame["latency_ms"], errors="coerce").fillna(0.0)
    return frame


def _build_overall_metrics(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    system_labels = _labels_section(labels, "systems")
    rows: list[dict[str, Any]] = []
    if conversations.empty:
        return pd.DataFrame(rows)
    for system, scoped in conversations.groupby("system"):
        eligible = scoped[~scoped["unsupported"]]
        business = eligible[eligible["layer"] == "business"]
        boundary = eligible[eligible["layer"] == "boundary"]
        rows.append(
            {
                "system": system,
                "system_label": _label_of(system_labels, system),
                "overall_pass_rate": round(float(eligible["passed"].mean()) if not eligible.empty else 0.0, 4),
                "technical_success_rate": round(float(eligible["success"].mean()) if not eligible.empty else 0.0, 4),
                "conversation_success_rate": round(
                    float(eligible["conversation_success"].mean()) if not eligible.empty else 0.0,
                    4,
                ),
                "business_pass_rate": round(float(business["passed"].mean()) if not business.empty else 0.0, 4),
                "boundary_safety_pass_rate": round(float(boundary["passed"].mean()) if not boundary.empty else 0.0, 4),
                "hallucination_free_rate": round(
                    float((~eligible["hallucinated_order_id"]).mean()) if not eligible.empty else 0.0,
                    4,
                ),
                "unsupported_rate": round(float(scoped["unsupported"].mean()) if not scoped.empty else 0.0, 4),
                "avg_supported_p95_ms": round(float(eligible["latency_ms"].quantile(0.95)) if not eligible.empty else 0.0, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["overall_pass_rate", "technical_success_rate", "avg_supported_p95_ms"],
        ascending=[False, False, True],
    )


def _build_scenario_leaders(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    scenario_labels = _labels_section(labels, "scenarios")
    system_labels = _labels_section(labels, "systems")
    rows: list[dict[str, Any]] = []
    if conversations.empty:
        return pd.DataFrame(rows)
    for family, scoped in conversations.groupby("scenario_family"):
        family_rows: list[dict[str, Any]] = []
        for system, system_scoped in scoped.groupby("system"):
            eligible = system_scoped[~system_scoped["unsupported"]]
            family_rows.append(
                {
                    "system": system,
                    "system_label": _label_of(system_labels, system),
                    "scenario_family": family,
                    "scenario_label": _label_of(scenario_labels, family),
                    "pass_rate": round(float(eligible["passed"].mean()) if not eligible.empty else 0.0, 4),
                    "conversation_success_rate": round(
                        float(eligible["conversation_success"].mean()) if not eligible.empty else 0.0,
                        4,
                    ),
                    "unsupported_rate": round(float(system_scoped["unsupported"].mean()) if not system_scoped.empty else 0.0, 4),
                    "p95_ms": round(float(eligible["latency_ms"].quantile(0.95)) if not eligible.empty else 0.0, 2),
                }
            )
        leader = (
            pd.DataFrame(family_rows)
            .sort_values(["pass_rate", "conversation_success_rate", "unsupported_rate", "p95_ms"], ascending=[False, False, True, True])
            .iloc[0]
        )
        rows.append(leader.to_dict())
    return pd.DataFrame(rows)


def _build_failure_breakdown(quality: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    failure_labels = _labels_section(labels, "failures")
    system_labels = _labels_section(labels, "systems")
    if quality.empty:
        return pd.DataFrame()
    excluded = {
        "system",
        "scenario_family",
        "layer",
        "score_profile",
        "conversations",
        "eligible_conversations",
        "unsupported_conversations",
        "conversation_success",
        "quality_pass",
    }
    failure_columns = [column for column in quality.columns if column not in excluded]
    rows: list[dict[str, Any]] = []
    for system, scoped in quality.groupby("system"):
        row: dict[str, Any] = {"system": system, "system_label": _label_of(system_labels, system)}
        total_issue = 0
        for column in failure_columns:
            value = int(pd.to_numeric(scoped[column], errors="coerce").fillna(0).sum())
            row[_label_of(failure_labels, column)] = value
            total_issue += value
        row["total_issue"] = total_issue
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["total_issue"], ascending=[False])


def _build_latency_by_concurrency(summary: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    system_labels = _labels_section(labels, "systems")
    if summary.empty:
        return pd.DataFrame()
    frame = summary.copy()
    for column in ["concurrency", "p95_ms", "eligible_conversations"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").fillna(0)
    frame = frame[frame["eligible_conversations"] > 0]
    rows: list[dict[str, Any]] = []
    for (system, concurrency), scoped in frame.groupby(["system", "concurrency"]):
        rows.append(
            {
                "system": system,
                "system_label": _label_of(system_labels, system),
                "concurrency": int(concurrency),
                "avg_p95_ms": round(float(scoped["p95_ms"].mean()), 2),
            }
        )
    return pd.DataFrame(rows).sort_values(["system", "concurrency"])


def _build_business_vs_boundary(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    system_labels = _labels_section(labels, "systems")
    if conversations.empty:
        return pd.DataFrame()
    scoped = conversations[~conversations["unsupported"]]
    rows: list[dict[str, Any]] = []
    for (system, layer), group in scoped.groupby(["system", "layer"]):
        rows.append(
            {
                "system": system,
                "system_label": _label_of(system_labels, system),
                "layer": layer,
                "pass_rate": round(float(group["passed"].mean()) if not group.empty else 0.0, 4),
                "conversation_success_rate": round(
                    float(group["conversation_success"].mean()) if not group.empty else 0.0,
                    4,
                ),
                "avg_latency_ms": round(float(group["latency_ms"].mean()) if not group.empty else 0.0, 2),
            }
        )
    return pd.DataFrame(rows).sort_values(["system", "layer"])


def _build_hallucination_breakdown(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    system_labels = _labels_section(labels, "systems")
    if conversations.empty:
        return pd.DataFrame()
    scoped = conversations[~conversations["unsupported"]]
    rows: list[dict[str, Any]] = []
    for (system, layer), group in scoped.groupby(["system", "layer"]):
        failures = int(group["hallucinated_order_id"].sum()) if "hallucinated_order_id" in group else 0
        rows.append(
            {
                "system": system,
                "system_label": _label_of(system_labels, system),
                "layer": layer,
                "conversations": int(len(group)),
                "hallucination_failures": failures,
                "hallucination_failure_rate": round(failures / max(1, len(group)), 4),
            }
        )
    return pd.DataFrame(rows).sort_values(["hallucination_failures", "system"], ascending=[False, True])


def _build_scenario_heatmap(conversations: pd.DataFrame, labels: dict[str, Any]) -> pd.DataFrame:
    scenario_labels = _labels_section(labels, "scenarios")
    system_labels = _labels_section(labels, "systems")
    rows: list[dict[str, Any]] = []
    if conversations.empty:
        return pd.DataFrame()
    for (system, family), scoped in conversations.groupby(["system", "scenario_family"]):
        eligible = scoped[~scoped["unsupported"]]
        rows.append(
            {
                "system_label": _label_of(system_labels, system),
                "scenario_label": _label_of(scenario_labels, family),
                "pass_rate": round(float(eligible["passed"].mean()) if not eligible.empty else 0.0, 4),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).pivot(index="system_label", columns="scenario_label", values="pass_rate").fillna(0.0)


def _render_report(
    *,
    analysis_dir: Path,
    overall_metrics: pd.DataFrame,
    leaders: pd.DataFrame,
    failure_breakdown: pd.DataFrame,
    latency_by_concurrency: pd.DataFrame,
    conclusions: dict[str, Any],
    labels: dict[str, Any],
) -> str:
    report_text = _labels_section(labels, "report")
    title = str(report_text.get("title") or "Benchmark 分析报告")
    sections = [
        f"# {title}",
        "",
        f"结果目录：`{analysis_dir.parent}`",
        "",
        f"## {report_text.get('overall_heading') or '整体指标'}",
        "",
        render_markdown_table(overall_metrics.to_dict(orient='records')),
        "",
        f"## {report_text.get('leaders_heading') or '分场景最优系统'}",
        "",
        render_markdown_table(leaders.to_dict(orient='records')),
        "",
        f"## {report_text.get('failures_heading') or '失败类型统计'}",
        "",
        render_markdown_table(failure_breakdown.to_dict(orient='records')),
        "",
        f"## {report_text.get('latency_heading') or '并发与时延'}",
        "",
        render_markdown_table(latency_by_concurrency.to_dict(orient='records')),
        "",
        f"## {report_text.get('figures_heading') or '图表'}",
        "",
        "![整体通过率](plots/overall_pass_rate.png)",
        "",
        "![业务与边界通过率](plots/business_boundary_pass_rate.png)",
        "",
        "![场景热力图](plots/scenario_heatmap.png)",
        "",
        "![失败类型堆叠图](plots/failure_stacked_bar.png)",
        "",
        "![并发时延曲线](plots/latency_concurrency.png)",
        "",
        "![质量与时延散点图](plots/system_scatter_quality_latency.png)",
        "",
        f"## {report_text.get('conclusions_heading') or '实验结论'}",
        "",
    ]
    for index, finding in enumerate(conclusions.get("findings", []), start=1):
        sections.append(f"{index}. {finding}")
    sections.extend(["", f"分析目录：`{analysis_dir}`"])
    return "\n".join(sections)


def analyze_result_dir(*, result_dir: Path, labels_path: Path) -> Path:
    labels = load_json_file(labels_path)
    result_dir = result_dir.resolve()
    analysis_dir = result_dir / "analysis"
    plots_dir = analysis_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    summary = _load_csv(result_dir / "summary.csv")
    quality = _load_csv(result_dir / "scenario_quality.csv")
    conversations = _prepare_conversations(_load_csv(result_dir / "conversation_summary.csv"))

    overall_metrics = _build_overall_metrics(conversations, labels)
    leaders = _build_scenario_leaders(conversations, labels)
    failure_breakdown = _build_failure_breakdown(quality, labels)
    latency_by_concurrency = _build_latency_by_concurrency(summary, labels)
    business_vs_boundary = _build_business_vs_boundary(conversations, labels)
    hallucination_breakdown = _build_hallucination_breakdown(conversations, labels)
    scenario_heatmap = _build_scenario_heatmap(conversations, labels)
    conclusions = build_conclusions(
        overall_metrics=overall_metrics,
        leaders=leaders,
        failure_breakdown=failure_breakdown,
        business_boundary=business_vs_boundary,
        latency_by_concurrency=latency_by_concurrency,
    )

    write_csv(analysis_dir / "overall_metrics.csv", overall_metrics.to_dict(orient="records"))
    write_csv(analysis_dir / "scenario_leaders.csv", leaders.to_dict(orient="records"))
    write_csv(analysis_dir / "failure_breakdown.csv", failure_breakdown.to_dict(orient="records"))
    write_csv(analysis_dir / "latency_by_concurrency.csv", latency_by_concurrency.to_dict(orient="records"))
    write_csv(analysis_dir / "business_vs_boundary.csv", business_vs_boundary.to_dict(orient="records"))
    write_csv(analysis_dir / "hallucination_breakdown.csv", hallucination_breakdown.to_dict(orient="records"))
    write_json(analysis_dir / "conclusions.json", conclusions, indent=2)

    chart_labels = _labels_section(labels, "charts")
    if not overall_metrics.empty:
        plot_bar_chart(
            path=plots_dir / "overall_pass_rate.png",
            frame=overall_metrics,
            label_col="system_label",
            value_col="overall_pass_rate",
            title=_text(labels, "charts", "overall_pass_rate_title", "整体通过率"),
            ylabel=_text(labels, "charts", "pass_rate_ylabel", "通过率"),
        )
        plot_grouped_bar_chart(
            path=plots_dir / "business_boundary_pass_rate.png",
            frame=overall_metrics,
            label_col="system_label",
            series_cols=["business_pass_rate", "boundary_safety_pass_rate"],
            series_labels=[
                _text(labels, "charts", "business_series_label", "业务层"),
                _text(labels, "charts", "boundary_series_label", "边界安全"),
            ],
            title=_text(labels, "charts", "business_boundary_title", "业务层与边界安全通过率"),
            ylabel=_text(labels, "charts", "pass_rate_ylabel", "通过率"),
        )
        plot_quality_latency_scatter(
            path=plots_dir / "system_scatter_quality_latency.png",
            frame=overall_metrics,
            title=_text(labels, "charts", "quality_latency_title", "质量与时延取舍"),
        )

    if not scenario_heatmap.empty:
        plot_heatmap(
            path=plots_dir / "scenario_heatmap.png",
            matrix=scenario_heatmap,
            title=_text(labels, "charts", "scenario_heatmap_title", "各系统分场景通过率"),
            xlabel=_text(labels, "charts", "scenario_heatmap_xlabel", "场景"),
            ylabel=_text(labels, "charts", "scenario_heatmap_ylabel", "系统"),
        )

    if not failure_breakdown.empty:
        stack_cols = [column for column in failure_breakdown.columns if column not in {"system", "system_label", "total_issue"}]
        plot_stacked_bar_chart(
            path=plots_dir / "failure_stacked_bar.png",
            frame=failure_breakdown,
            label_col="system_label",
            stack_cols=stack_cols,
            stack_labels=stack_cols,
            title=_text(labels, "charts", "failure_stacked_title", "失败类型分布"),
            ylabel=_text(labels, "charts", "failure_count_ylabel", "失败次数"),
        )

    if not latency_by_concurrency.empty:
        plot_latency_by_concurrency(
            path=plots_dir / "latency_concurrency.png",
            frame=latency_by_concurrency,
            title=_text(labels, "charts", "latency_concurrency_title", "并发与时延"),
            ylabel=_text(labels, "charts", "latency_ylabel", "平均 P95 时延（ms）"),
        )

    report = _render_report(
        analysis_dir=analysis_dir,
        overall_metrics=overall_metrics,
        leaders=leaders,
        failure_breakdown=failure_breakdown,
        latency_by_concurrency=latency_by_concurrency,
        conclusions=conclusions,
        labels=labels,
    )
    (analysis_dir / "report.md").write_text(report, encoding="utf-8")
    return analysis_dir


def main() -> None:
    args = parse_args()
    analysis_dir = analyze_result_dir(result_dir=args.result_dir, labels_path=args.labels)
    print(json.dumps({"analysis_dir": str(analysis_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
