"""Render Figure 4-10 PDFs from aggregate CSVs."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CACHE_ROOT = ROOT / "data" / "interim" / "cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_ROOT / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from tools.workflow_support import repo_root


COLORS = {
    "exact": "#2b2b2b",
    "flood": "#c94c3c",
    "flat": "#e4a52b",
    "flat_iroute": "#e4a52b",
    "oracle": "#2f7d57",
    "hiroute": "#2451a4",
    "predicates_only": "#b85c38",
    "flat_semantic_only": "#8c6a16",
    "predicates_plus_flat": "#4f7f2b",
    "full_hiroute": "#2451a4",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=False, type=Path)
    return parser.parse_args()


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _save(fig: plt.Figure, filename: str) -> None:
    output_path = repo_root() / "results" / "figures" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output_path, format="pdf", bbox_inches="tight")
    plt.close(fig)


def _placeholder(filename: str, title: str, message: str) -> None:
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    ax.axis("off")
    ax.text(0.5, 0.68, title, ha="center", va="center", fontsize=14, weight="bold")
    ax.text(0.5, 0.42, message, ha="center", va="center", fontsize=10)
    _save(fig, filename)


def _scheme_color(scheme: str) -> str:
    return COLORS.get(scheme, "#6d6d6d")


def plot_main_success() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "main_success_overhead.csv")
    if frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "Awaiting aggregate data")
        return

    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    for _, row in frame.iterrows():
        ax.scatter(
            row["mean_discovery_bytes"],
            row["mean_success_at_1"],
            s=90,
            color=_scheme_color(row["scheme"]),
            label=row["scheme"],
        )
        ax.text(row["mean_discovery_bytes"] + 3, row["mean_success_at_1"] + 0.005, row["scheme"], fontsize=9)
    ax.set_xlabel("Mean Discovery Bytes")
    ax.set_ylabel("ServiceSuccess@1")
    ax.set_title("Figure 4: Success vs Discovery Overhead")
    ax.grid(alpha=0.25)
    _save(fig, "fig_main_success_overhead.pdf")


def plot_failure_breakdown() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "failure_breakdown.csv")
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "Awaiting aggregate data")
        return

    pivot = frame.pivot(index="scheme", columns="failure_type", values="rate").fillna(0.0)
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    bottom = pd.Series(0.0, index=pivot.index)
    for failure_type in pivot.columns:
        ax.bar(
            pivot.index,
            pivot[failure_type],
            bottom=bottom,
            label=failure_type,
            alpha=0.9,
        )
        bottom += pivot[failure_type]
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Rate")
    ax.set_title("Figure 5: Failure Breakdown")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_failure_breakdown.pdf")


def plot_candidate_shrinkage() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "candidate_shrinkage.csv")
    if frame.empty:
        _placeholder("fig_candidate_shrinkage.pdf", "Figure 6", "Awaiting aggregate data")
        return

    frame = frame.sort_values("mean_candidate_shrinkage_ratio")
    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    ax.barh(
        frame["scheme"],
        frame["mean_candidate_shrinkage_ratio"],
        color=[_scheme_color(s) for s in frame["scheme"]],
    )
    ax.set_xlabel("Mean Candidate Shrinkage Ratio")
    ax.set_title("Figure 6: Candidate Shrinkage")
    ax.grid(axis="x", alpha=0.25)
    _save(fig, "fig_candidate_shrinkage.pdf")


def plot_deadlines() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "deadline_summary.csv")
    if frame.empty:
        _placeholder("fig_deadline_summary.pdf", "Figure 7", "Awaiting aggregate data")
        return

    fig, ax = plt.subplots(figsize=(6.8, 4.0))
    for scheme, group in frame.groupby("scheme", sort=False):
        ax.plot(
            group["deadline_ms"],
            group["success_before_deadline_rate"],
            marker="o",
            linewidth=2,
            color=_scheme_color(scheme),
            label=scheme,
        )
    ax.set_xlabel("Deadline (ms)")
    ax.set_ylabel("Success Before Deadline")
    ax.set_title("Figure 7: Deadline-Sensitive Success")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    _save(fig, "fig_deadline_summary.pdf")


def plot_state_scaling() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "state_scaling_summary.csv")
    if frame.empty:
        _placeholder("fig_state_scaling.pdf", "Figure 8", "Awaiting scaling runs")
        return

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    for scheme, group in frame.groupby("scheme", sort=False):
        ax.plot(
            group["node_count"],
            group["summary_count"],
            marker="o",
            linewidth=2,
            color=_scheme_color(scheme),
            label=scheme,
        )
    for _, row in frame.iterrows():
        ax.text(row["node_count"] + 1, row["summary_count"], row["topology_id"], fontsize=8)
    ax.set_xlabel("Topology Node Count")
    ax.set_ylabel("Exported Summary Count")
    ax.set_title("Figure 8: State Scaling")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    _save(fig, "fig_state_scaling.pdf")


def plot_robustness() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "robustness_summary.csv")
    if frame.empty:
        _placeholder("fig_robustness.pdf", "Figure 9", "Awaiting staleness and failure runs")
        return

    frame["scenario_label"] = frame.apply(
        lambda row: row["scenario_variant"] if isinstance(row["scenario_variant"], str) and row["scenario_variant"] else row["scenario"],
        axis=1,
    )
    pivot = frame.pivot(index="scenario_label", columns="scheme", values="mean_success_at_1").fillna(0.0)
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    width = 0.15
    x_positions = range(len(pivot.index))
    for idx, scheme in enumerate(pivot.columns):
        offsets = [x + (idx - (len(pivot.columns) - 1) / 2) * width for x in x_positions]
        ax.bar(offsets, pivot[scheme], width=width, color=_scheme_color(scheme), label=scheme)
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(list(pivot.index))
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("ServiceSuccess@1")
    ax.set_title("Figure 9: Robustness Under Staleness and Failures")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_robustness.pdf")


def plot_ablation() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "ablation_summary.csv")
    if frame.empty:
        _placeholder("fig_ablation.pdf", "Figure 10", "Awaiting ablation aggregate")
        return

    fig, ax1 = plt.subplots(figsize=(7.0, 4.2))
    schemes = frame["scheme"].tolist()
    x_positions = list(range(len(schemes)))
    width = 0.35
    ax1.bar(
        [position - width / 2 for position in x_positions],
        frame["mean_success_at_1"],
        width=width,
        color=[_scheme_color(s) for s in schemes],
        alpha=0.85,
        label="ServiceSuccess@1",
    )
    ax1.bar(
        [position + width / 2 for position in x_positions],
        frame["success_before_200ms_rate"],
        width=width,
        color="#d8d8d8",
        alpha=0.95,
        label="Success<=200ms",
    )
    ax1.set_ylabel("Rate")
    ax1.set_ylim(0, 1.0)
    ax1.set_title("Figure 10: Ablation Summary")
    ax1.grid(axis="y", alpha=0.25)
    ax1.set_xticks(x_positions)
    ax1.set_xticklabels(schemes, rotation=15, ha="right")
    ax1.legend(fontsize=8, loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(schemes, frame["mean_discovery_bytes"], color="#111111", marker="o", linewidth=2)
    ax2.set_ylabel("Mean Discovery Bytes")
    _save(fig, "fig_ablation.pdf")


def main() -> int:
    _ = parse_args()
    plt.rcParams.update(
        {
            "font.size": 10,
            "axes.titlesize": 12,
            "axes.labelsize": 10,
        }
    )
    plot_main_success()
    plot_failure_breakdown()
    plot_candidate_shrinkage()
    plot_deadlines()
    plot_state_scaling()
    plot_robustness()
    plot_ablation()
    print("results/figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
