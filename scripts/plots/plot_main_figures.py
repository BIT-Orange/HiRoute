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

FAILURE_COLORS = {
    "predicate_miss": "#b7b7b7",
    "wrong_domain": "#d97a3a",
    "wrong_object": "#c94c3c",
    "no_reply": "#7c5aa6",
    "fetch_timeout": "#4f7fbe",
    "success": "#2f7d57",
}

SCHEME_LABELS = {
    "exact": "Exact name",
    "flood": "Flood",
    "flat": "Flat iRoute",
    "flat_iroute": "Flat iRoute",
    "oracle": "Central directory",
    "hiroute": "HiRoute",
    "predicates_only": "Predicates only",
    "flat_semantic_only": "Flat semantic only",
    "predicates_plus_flat": "Predicates + flat",
    "full_hiroute": "Full HiRoute",
}

MAIN_SCHEME_ORDER = ["flat_iroute", "flood", "hiroute", "oracle"]
FAILURE_ORDER = ["predicate_miss", "wrong_domain", "wrong_object", "no_reply", "fetch_timeout", "success"]

SHRINKAGE_STAGE_ORDER = [
    "all_domains",
    "predicate_filtered_domains",
    "level0_cells",
    "level1_cells",
    "refined_cells",
    "probed_cells",
    "manifest_candidates",
]

SHRINKAGE_STAGE_LABELS = {
    "all_domains": "All\ndomains",
    "predicate_filtered_domains": "Predicate\nfiltered",
    "level0_cells": "Level-0\ncells",
    "level1_cells": "Level-1\ncells",
    "refined_cells": "Refined\ncells",
    "probed_cells": "Probed\ncells",
    "manifest_candidates": "Manifest\ncandidates",
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


def _scheme_label(scheme: str) -> str:
    return SCHEME_LABELS.get(scheme, scheme.replace("_", " "))


def plot_main_success() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "main_success_overhead.csv")
    if frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "No comparable discovery baselines found")
        return

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for scheme in MAIN_SCHEME_ORDER:
        group = frame[frame["scheme"] == scheme]
        if group.empty:
            continue
        row = group.iloc[0]
        marker = "*" if scheme == "oracle" else "o"
        markersize = 14 if scheme == "oracle" else 8
        ax.errorbar(
            row["mean_discovery_bytes"],
            row["mean_success_at_1"],
            xerr=row.get("ci_discovery_bytes", 0.0),
            yerr=row.get("ci_success_at_1", 0.0),
            fmt=marker,
            markersize=markersize,
            linewidth=1.8,
            capsize=3,
            color=_scheme_color(scheme),
            label=_scheme_label(scheme),
        )

    ax.set_xlabel("Mean Discovery Bytes / Query")
    ax.set_ylabel("ServiceSuccess@1")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower right")
    _save(fig, "fig_main_success_overhead.pdf")


def plot_failure_breakdown() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "failure_breakdown.csv")
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "No comparable discovery baselines found")
        return

    pivot = frame.pivot(index="scheme", columns="failure_type", values="rate").fillna(0.0)
    ordered_index = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in pivot.index]
    pivot = pivot.reindex(index=ordered_index, columns=FAILURE_ORDER, fill_value=0.0)

    fig, ax = plt.subplots(figsize=(7.2, 4.1))
    bottom = pd.Series(0.0, index=pivot.index)
    for failure_type in FAILURE_ORDER:
        ax.bar(
            [_scheme_label(scheme) for scheme in pivot.index],
            pivot[failure_type],
            bottom=bottom,
            label=failure_type.replace("_", " "),
            color=FAILURE_COLORS[failure_type],
            alpha=0.9,
        )
        bottom += pivot[failure_type]
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Query Fraction")
    ax.legend(fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.18))
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_failure_breakdown.pdf")


def plot_candidate_shrinkage() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "candidate_shrinkage.csv")
    if frame.empty:
        _placeholder("fig_candidate_shrinkage.pdf", "Figure 6", "Awaiting aggregate data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.1), gridspec_kw={"width_ratios": [1.65, 1.0]})
    left, right = axes

    hiroute = frame[frame["scheme"] == "hiroute"].copy()
    ordered = (
        hiroute.set_index("stage")
        .reindex(SHRINKAGE_STAGE_ORDER)
        .dropna(subset=["mean_shrinkage_ratio"])
        .reset_index()
    )
    x_positions = list(range(len(SHRINKAGE_STAGE_ORDER)))
    left.plot(
        [SHRINKAGE_STAGE_ORDER.index(stage) for stage in ordered["stage"]],
        ordered["mean_shrinkage_ratio"],
        marker="o",
        linewidth=2.2,
        color=_scheme_color("hiroute"),
    )
    left.set_xticks(x_positions)
    left.set_xticklabels([SHRINKAGE_STAGE_LABELS[stage] for stage in SHRINKAGE_STAGE_ORDER])
    left.set_ylim(0, 1.05)
    left.set_ylabel("Candidate Ratio vs All Domains")
    left.set_title("HiRoute staged contraction", fontsize=10)
    left.grid(axis="x", alpha=0.2)
    left.grid(axis="y", alpha=0.25)

    main_frame = _read_csv(repo_root() / "results" / "aggregate" / "main_success_overhead.csv")
    main_frame = main_frame[main_frame["scheme"] != "exact"].copy()
    ordered_schemes = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(main_frame["scheme"])]
    probe_rows = main_frame.set_index("scheme").reindex(ordered_schemes).dropna(subset=["mean_num_remote_probes"])
    right.bar(
        [_scheme_label(scheme) for scheme in probe_rows.index],
        probe_rows["mean_num_remote_probes"],
        yerr=probe_rows.get("ci_num_remote_probes", pd.Series(0.0, index=probe_rows.index)),
        color=[_scheme_color(scheme) for scheme in probe_rows.index],
        capsize=3,
        alpha=0.9,
    )
    right.set_ylabel("Mean Remote Probes / Query")
    right.set_title("Cross-method discovery breadth", fontsize=10)
    right.grid(axis="y", alpha=0.25)
    _save(fig, "fig_candidate_shrinkage.pdf")


def plot_deadlines() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "deadline_summary.csv")
    if frame.empty:
        _placeholder("fig_deadline_summary.pdf", "Figure 7", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_deadline_summary.pdf", "Figure 7", "No comparable discovery baselines found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 4.0), gridspec_kw={"width_ratios": [1.5, 1.0]})
    left, right = axes
    ordered_schemes = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(frame["scheme"])]
    for scheme in ordered_schemes:
        group = frame[frame["scheme"] == scheme].sort_values("deadline_ms")
        left.plot(
            group["deadline_ms"],
            group["success_before_deadline_rate"],
            marker="o",
            linewidth=2,
            color=_scheme_color(scheme),
            label=_scheme_label(scheme),
        )
    left.set_xlabel("Deadline (ms)")
    left.set_ylabel("Success Within Deadline")
    left.grid(alpha=0.25)
    left.legend(fontsize=8, loc="lower right")

    latency_rows = (
        frame.groupby("scheme", as_index=False)["median_success_latency_ms"]
        .max()
        .set_index("scheme")
        .reindex(ordered_schemes)
        .dropna(subset=["median_success_latency_ms"])
    )
    right.bar(
        [_scheme_label(scheme) for scheme in latency_rows.index],
        latency_rows["median_success_latency_ms"],
        color=[_scheme_color(scheme) for scheme in latency_rows.index],
        alpha=0.9,
    )
    right.set_ylabel("Median Successful Latency (ms)")
    right.grid(axis="y", alpha=0.25)
    _save(fig, "fig_deadline_summary.pdf")


def plot_state_scaling() -> None:
    frame = _read_csv(repo_root() / "results" / "aggregate" / "state_scaling_summary.csv")
    if frame.empty:
        _placeholder("fig_state_scaling.pdf", "Figure 8", "Awaiting scaling runs")
        return

    if "hiroute" in set(frame["scheme"]):
        frame = frame[frame["scheme"] == "hiroute"].copy()

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2), sharey=True)
    panel_specs = [
        ("objects_per_domain", "Objects per Domain", axes[0]),
        ("domain_count", "Active Domains", axes[1]),
    ]

    for scaling_axis, xlabel, axis in panel_specs:
        axis_rows = frame[frame["scaling_axis"] == scaling_axis].copy()
        if axis_rows.empty:
            axis.axis("off")
            continue
        for topology_id, group in axis_rows.groupby("topology_id", sort=False):
            ordered = group.sort_values("scaling_value")
            axis.plot(
                ordered["scaling_value"],
                ordered["mean_total_exported_summaries"],
                marker="o",
                linewidth=2,
                color=_scheme_color("hiroute") if topology_id == "rf_3967_exodus" else "#1d7a74",
                label=topology_id,
            )
        axis.set_xlabel(xlabel)
        axis.grid(alpha=0.25)
        axis.set_title(f"{xlabel} Sweep")
    axes[0].set_ylabel("Mean Exported Summaries")
    axes[0].legend(fontsize=8)
    axes[1].legend(fontsize=8)
    fig.suptitle("Figure 8: Routing-State Scaling Under Fixed Export Budget", fontsize=12)
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
