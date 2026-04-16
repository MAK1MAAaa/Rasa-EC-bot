from __future__ import annotations

from typing import Any

import pandas as pd


def _to_record(row: pd.Series | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {key: row[key] for key in row.index}


def _pick_first(frame: pd.DataFrame, sort_columns: list[str], ascending: list[bool]) -> pd.Series | None:
    if frame.empty:
        return None
    return frame.sort_values(sort_columns, ascending=ascending).iloc[0]


def build_conclusions(
    *,
    overall_metrics: pd.DataFrame,
    leaders: pd.DataFrame,
    failure_breakdown: pd.DataFrame,
    business_boundary: pd.DataFrame,
    latency_by_concurrency: pd.DataFrame,
) -> dict[str, Any]:
    best_overall = _pick_first(
        overall_metrics,
        ["overall_pass_rate", "technical_success_rate", "avg_supported_p95_ms"],
        [False, False, True],
    )
    best_business = _pick_first(
        overall_metrics,
        ["business_pass_rate", "technical_success_rate", "avg_supported_p95_ms"],
        [False, False, True],
    )
    best_boundary = _pick_first(
        overall_metrics,
        ["boundary_safety_pass_rate", "technical_success_rate", "avg_supported_p95_ms"],
        [False, False, True],
    )
    risk_row = _pick_first(failure_breakdown, ["total_issue"], [False])
    latency_row = _pick_first(latency_by_concurrency, ["avg_p95_ms"], [True])

    dominant_failure: dict[str, Any] | None = None
    if not failure_breakdown.empty:
        failure_columns = [column for column in failure_breakdown.columns if column not in {"system", "system_label", "total_issue"}]
        aggregate = failure_breakdown[failure_columns].sum().sort_values(ascending=False)
        if not aggregate.empty:
            dominant_failure = {"failure_key": aggregate.index[0], "count": int(aggregate.iloc[0])}

    findings: list[str] = []
    if best_overall is not None:
        findings.append(
            f"综合最优系统为 {best_overall['system_label']}，整体通过率 {best_overall['overall_pass_rate']:.4f}。"
        )
    if best_business is not None:
        findings.append(
            f"业务层最优系统为 {best_business['system_label']}，业务通过率 {best_business['business_pass_rate']:.4f}。"
        )
    if best_boundary is not None:
        findings.append(
            f"边界安全最优系统为 {best_boundary['system_label']}，边界安全通过率 {best_boundary['boundary_safety_pass_rate']:.4f}。"
        )
    if risk_row is not None:
        findings.append(f"当前最高风险系统为 {risk_row['system_label']}，累计问题数 {int(risk_row['total_issue'])}。")
    if dominant_failure is not None:
        findings.append(
            f"主要失败类型为 {dominant_failure['failure_key']}，累计出现 {dominant_failure['count']} 次。"
        )
    if latency_row is not None:
        findings.append(
            f"最低平均 P95 时延出现在 {latency_row['system_label']}，并发 {int(latency_row['concurrency'])} 时为 {latency_row['avg_p95_ms']:.2f} ms。"
        )

    return {
        "best_overall": _to_record(best_overall),
        "best_business": _to_record(best_business),
        "best_boundary": _to_record(best_boundary),
        "scenario_leaders": leaders.to_dict(orient="records"),
        "top_risk": _to_record(risk_row),
        "dominant_failure": dominant_failure,
        "findings": findings,
        "business_boundary_rows": business_boundary.to_dict(orient="records"),
    }
