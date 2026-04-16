from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


def _prepare_figure(width: float = 10, height: float = 6) -> tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=(width, height))
    return fig, ax


def _finish_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def plot_bar_chart(
    *,
    path: Path,
    frame: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    ylabel: str,
    color: str = "#2563eb",
) -> None:
    fig, ax = _prepare_figure()
    positions = list(range(len(frame)))
    ax.bar(positions, frame[value_col], color=color)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels(frame[label_col], rotation=25, ha="right")
    _finish_figure(fig, path)


def plot_grouped_bar_chart(
    *,
    path: Path,
    frame: pd.DataFrame,
    label_col: str,
    series_cols: list[str],
    series_labels: list[str],
    title: str,
    ylabel: str,
) -> None:
    fig, ax = _prepare_figure()
    positions = list(range(len(frame)))
    width = 0.8 / max(1, len(series_cols))
    start = -((len(series_cols) - 1) * width / 2)
    colors = ["#2563eb", "#059669", "#dc2626", "#d97706"]
    for index, column in enumerate(series_cols):
        offset = start + index * width
        ax.bar(
            [item + offset for item in positions],
            frame[column],
            width=width,
            label=series_labels[index],
            color=colors[index % len(colors)],
        )
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels(frame[label_col], rotation=25, ha="right")
    ax.legend()
    _finish_figure(fig, path)


def plot_heatmap(
    *,
    path: Path,
    matrix: pd.DataFrame,
    title: str,
    xlabel: str,
    ylabel: str,
    cmap: str = "Blues",
) -> None:
    fig, ax = _prepare_figure(width=11, height=6)
    im = ax.imshow(matrix.values, cmap=cmap, aspect="auto")
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xticks(range(len(matrix.columns)))
    ax.set_xticklabels(list(matrix.columns), rotation=30, ha="right")
    ax.set_yticks(range(len(matrix.index)))
    ax.set_yticklabels(list(matrix.index))
    for row_index, row in enumerate(matrix.values):
        for col_index, value in enumerate(row):
            ax.text(col_index, row_index, f"{value:.2f}", ha="center", va="center", color="black", fontsize=9)
    fig.colorbar(im, ax=ax)
    _finish_figure(fig, path)


def plot_stacked_bar_chart(
    *,
    path: Path,
    frame: pd.DataFrame,
    label_col: str,
    stack_cols: list[str],
    stack_labels: list[str],
    title: str,
    ylabel: str,
) -> None:
    fig, ax = _prepare_figure(width=11, height=6)
    positions = list(range(len(frame)))
    bottom = pd.Series([0] * len(frame), dtype="float64")
    palette = ["#dc2626", "#f59e0b", "#7c3aed", "#0891b2", "#4f46e5", "#16a34a", "#6b7280"]
    for index, column in enumerate(stack_cols):
        values = pd.to_numeric(frame[column], errors="coerce").fillna(0.0)
        ax.bar(positions, values, bottom=bottom, label=stack_labels[index], color=palette[index % len(palette)])
        bottom = bottom + values
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions)
    ax.set_xticklabels(frame[label_col], rotation=25, ha="right")
    ax.legend()
    _finish_figure(fig, path)


def plot_latency_by_concurrency(
    *,
    path: Path,
    frame: pd.DataFrame,
    title: str,
    ylabel: str,
) -> None:
    fig, ax = _prepare_figure()
    for system_label, scoped in frame.groupby("system_label"):
        ordered = scoped.sort_values("concurrency")
        ax.plot(ordered["concurrency"], ordered["avg_p95_ms"], marker="o", label=system_label)
    ax.set_title(title)
    ax.set_xlabel("并发数")
    ax.set_ylabel(ylabel)
    ax.legend()
    _finish_figure(fig, path)


def plot_quality_latency_scatter(
    *,
    path: Path,
    frame: pd.DataFrame,
    title: str,
) -> None:
    fig, ax = _prepare_figure()
    ax.scatter(frame["avg_supported_p95_ms"], frame["overall_pass_rate"], s=120, color="#2563eb")
    for _, row in frame.iterrows():
        ax.annotate(
            row["system_label"],
            (row["avg_supported_p95_ms"], row["overall_pass_rate"]),
            textcoords="offset points",
            xytext=(6, 6),
        )
    ax.set_title(title)
    ax.set_xlabel("支持场景 P95 时延（ms）")
    ax.set_ylabel("整体通过率")
    _finish_figure(fig, path)
