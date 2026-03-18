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

from scripts.eval.eval_support import (
    aggregate_output_path,
    COMPACT_ABLATION_SCHEMES,
    COMPACT_OBJECT_MAIN_SCHEMES,
    COMPACT_ROUTING_PANEL_A_SCHEMES,
    COMPACT_ROUTING_PANEL_B_SCHEMES,
    COMPACT_ROUTING_REQUIRED_SCHEMES,
    declared_output_filenames,
    figure_output_path,
    is_v3_experiment,
    load_experiment,
)
from tools.workflow_support import repo_root


COLORS = {
    "exact": "#2b2b2b",
    "flat": "#6f8396",
    "flat_iroute": "#6f8396",
    "inf_tag_forwarding": "#d98a3a",
    "flood": "#4a4a4a",
    "hiroute": "#2451a4",
    "central_directory": "#1f5f46",
    "oracle": "#1f5f46",
    "predicates_only": "#8e5a3c",
    "random_admissible": "#7a6aa8",
    "flat_semantic_only": "#c79a3a",
    "predicates_plus_flat": "#5f8773",
    "full_hiroute": "#2451a4",
}

FAILURE_COLORS = {
    "predicate_miss": "#b7b7b7",
    "wrong_domain": "#d98a3a",
    "wrong_object": "#c94c3c",
    "no_reply": "#7c5aa6",
    "fetch_timeout": "#4f7fbe",
    "success": "#2f7d57",
}

SCHEME_LABELS = {
    "exact": "Exact name",
    "flat": "Flat iRoute",
    "flat_iroute": "Flat iRoute",
    "inf_tag_forwarding": "INF-style tags",
    "flood": "Flood",
    "hiroute": "HiRoute",
    "central_directory": "Central directory",
    "oracle": "Central directory",
    "predicates_only": "Predicates only",
    "random_admissible": "Random admissible",
    "flat_semantic_only": "Flat semantic only",
    "predicates_plus_flat": "Predicates + flat",
    "full_hiroute": "Full HiRoute",
}

MARKERS = {
    "flat_iroute": "o",
    "inf_tag_forwarding": "s",
    "flood": "^",
    "hiroute": "D",
    "central_directory": "P",
    "oracle": "P",
    "predicates_only": "X",
    "random_admissible": "v",
}

MAIN_SCHEME_ORDER = [
    "predicates_only",
    "random_admissible",
    "flat_iroute",
    "inf_tag_forwarding",
    "flood",
    "hiroute",
    "central_directory",
    "oracle",
]
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

FIG4_STAGE_ORDER = [
    "all_domains",
    "predicate_filtered_domains",
    "refined_cells",
    "probed_cells",
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


def _save(fig: plt.Figure, filename: str, rect: tuple[float, float, float, float] | None = None) -> None:
    output_path = _figure_path(filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if rect is None:
        fig.tight_layout()
    else:
        fig.tight_layout(rect=rect)
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


CURRENT_EXPERIMENT: dict | None = None


def _aggregate_path(filename: str) -> Path:
    if CURRENT_EXPERIMENT is not None:
        return aggregate_output_path(CURRENT_EXPERIMENT, filename)
    return repo_root() / "results" / "aggregate" / filename


def _figure_path(filename: str) -> Path:
    if CURRENT_EXPERIMENT is not None:
        return figure_output_path(CURRENT_EXPERIMENT, filename)
    return repo_root() / "results" / "figures" / filename


def _output_filenames() -> set[str]:
    if CURRENT_EXPERIMENT is None:
        return set()
    return declared_output_filenames(CURRENT_EXPERIMENT)


def _ablation_filename() -> str:
    outputs = _output_filenames()
    if "fig_ablation_summary.pdf" in outputs:
        return "fig_ablation_summary.pdf"
    return "fig_ablation.pdf"


def _selected_budget(default: int = 16) -> int:
    if CURRENT_EXPERIMENT is None:
        return default
    selected = int(CURRENT_EXPERIMENT.get("default_budget") or 0)
    return selected or default


def _selected_manifest(default: int = 1) -> int:
    if CURRENT_EXPERIMENT is None:
        return default
    selected = int(CURRENT_EXPERIMENT.get("default_manifest_size") or 0)
    return selected or default


def _is_experiment(*experiment_ids: str) -> bool:
    if CURRENT_EXPERIMENT is None:
        return False
    return str(CURRENT_EXPERIMENT.get("experiment_id", "")) in set(experiment_ids)


def _ordered_rows(frame: pd.DataFrame, order: list[str], column: str = "scheme") -> pd.DataFrame:
    if frame.empty:
        return frame
    frame = frame.copy()
    rank = {value: index for index, value in enumerate(order)}
    frame["_order"] = frame[column].map(rank).fillna(len(order)).astype(int)
    frame = frame.sort_values(["_order", column]).drop(columns="_order")
    return frame


def _add_panel_label(axis: plt.Axes, label: str) -> None:
    axis.text(
        -0.15,
        1.05,
        label,
        transform=axis.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
    )


def _bar_panel(axis: plt.Axes, labels: list[str], values: list[float], errors: list[float], colors: list[str], ylabel: str) -> None:
    x_positions = list(range(len(labels)))
    axis.bar(
        x_positions,
        values,
        yerr=errors,
        color=colors,
        alpha=0.92,
        capsize=3,
        width=0.68,
        linewidth=0,
    )
    axis.set_xticks(x_positions)
    axis.set_xticklabels(labels, rotation=16, ha="right")
    axis.set_ylabel(ylabel)
    axis.grid(axis="y", alpha=0.22)
    axis.set_axisbelow(True)


def _line_panel(
    axis: plt.Axes,
    frame: pd.DataFrame,
    schemes: list[str],
    x_column: str,
    y_column: str,
    yerr_column: str | None,
    ylabel: str,
    xlabel: str,
) -> None:
    for scheme in schemes:
        group = frame[frame["scheme"] == scheme].sort_values(x_column)
        if group.empty:
            continue
        axis.errorbar(
            group[x_column],
            group[y_column],
            yerr=group[yerr_column] if yerr_column and yerr_column in group.columns else None,
            color=_scheme_color(scheme),
            marker=MARKERS.get(scheme, "o"),
            linewidth=2.0,
            markersize=5.5,
            capsize=3,
            label=_scheme_label(scheme),
        )
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.22)
    axis.set_axisbelow(True)


def _plot_compact_routing_support() -> None:
    main_frame = _read_csv(_aggregate_path("main_success_overhead.csv"))
    stage_frame = _read_csv(_aggregate_path("candidate_shrinkage.csv"))
    if main_frame.empty or stage_frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "Awaiting compact routing support aggregates")
        return

    selected_budget = _selected_budget(16)
    main_frame = main_frame[main_frame["budget"] == selected_budget].copy()
    available_schemes = set(main_frame["scheme"])
    missing_required = [scheme for scheme in COMPACT_ROUTING_REQUIRED_SCHEMES if scheme not in available_schemes]
    if missing_required:
        _placeholder(
            "fig_main_success_overhead.pdf",
            "Figure 4",
            "Awaiting compact routing rerun with predicates_only and random_admissible baselines",
        )
        return

    panel_a_frame = _ordered_rows(
        main_frame[main_frame["scheme"].isin(COMPACT_ROUTING_PANEL_A_SCHEMES)].copy(),
        COMPACT_ROUTING_PANEL_A_SCHEMES,
    )
    panel_b_frame = _ordered_rows(
        main_frame[main_frame["scheme"].isin(COMPACT_ROUTING_PANEL_B_SCHEMES)].copy(),
        COMPACT_ROUTING_PANEL_B_SCHEMES,
    )

    stage_frame = stage_frame[
        (stage_frame["budget"] == selected_budget)
        & (stage_frame["scheme"].isin(["flat_iroute", "hiroute"]))
        & (stage_frame["stage"].isin(FIG4_STAGE_ORDER))
    ].copy()
    if panel_a_frame.empty or panel_b_frame.empty or stage_frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "No compact routing support slice at the default budget")
        return

    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.35), gridspec_kw={"width_ratios": [1.0, 1.0, 1.45]})

    panel_a_labels = [_scheme_label(scheme) for scheme in panel_a_frame["scheme"]]
    panel_a_colors = [_scheme_color(scheme) for scheme in panel_a_frame["scheme"]]
    panel_b_labels = [_scheme_label(scheme) for scheme in panel_b_frame["scheme"]]
    panel_b_colors = [_scheme_color(scheme) for scheme in panel_b_frame["scheme"]]

    _bar_panel(
        axes[0],
        panel_a_labels,
        panel_a_frame["relevant_domain_reached_at_1"].tolist(),
        panel_a_frame.get("ci_relevant_domain_reached_at_1", pd.Series(0.0, index=panel_a_frame.index)).tolist(),
        panel_a_colors,
        "Relevant-domain reach@1",
    )
    axes[0].set_ylim(0, 0.8)
    _add_panel_label(axes[0], "A")

    _bar_panel(
        axes[1],
        panel_b_labels,
        panel_b_frame["mean_discovery_bytes"].tolist(),
        panel_b_frame.get("ci_discovery_bytes", pd.Series(0.0, index=panel_b_frame.index)).tolist(),
        panel_b_colors,
        "Discovery bytes / query",
    )
    _add_panel_label(axes[1], "B")

    for scheme in ["flat_iroute", "hiroute"]:
        group = stage_frame[stage_frame["scheme"] == scheme].copy()
        if group.empty:
            continue
        group["stage"] = pd.Categorical(group["stage"], categories=FIG4_STAGE_ORDER, ordered=True)
        group = group.sort_values("stage")
        x_positions = [FIG4_STAGE_ORDER.index(stage) for stage in group["stage"].astype(str)]
        axes[2].plot(
            x_positions,
            group["mean_shrinkage_ratio"],
            color=_scheme_color(scheme),
            marker=MARKERS.get(scheme, "o"),
            linewidth=2.0,
            markersize=5.5,
            label=_scheme_label(scheme),
        )
    axes[2].set_xticks(list(range(len(FIG4_STAGE_ORDER))))
    axes[2].set_xticklabels(
        [
            "All\ndomains",
            "Admissible\ndomains",
            "Refined\ncells",
            "Probed\ncells",
        ]
    )
    axes[2].set_ylabel("Candidate ratio")
    axes[2].grid(alpha=0.22)
    axes[2].set_axisbelow(True)
    axes[2].legend(fontsize=7.8, frameon=False, loc="upper right")
    _add_panel_label(axes[2], "C")

    _save(fig, "fig_main_success_overhead.pdf")


def plot_main_success() -> None:
    if _is_experiment("exp_routing_main_v3_compact"):
        _plot_compact_routing_support()
        return

    frame = _read_csv(_aggregate_path("main_success_overhead.csv"))
    if frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_main_success_overhead.pdf", "Figure 4", "No comparable discovery baselines found")
        return

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for scheme in MAIN_SCHEME_ORDER:
        group = frame[frame["scheme"] == scheme].copy()
        if group.empty:
            continue
        if "budget" in group.columns:
            group = group.sort_values("budget")
        ax.errorbar(
            group["mean_discovery_bytes"],
            group["mean_success_at_1"],
            xerr=group.get("ci_discovery_bytes", 0.0),
            yerr=group.get("ci_success_at_1", 0.0),
            fmt=f"{MARKERS.get(scheme, 'o')}-",
            markersize=6.5,
            linewidth=1.8,
            capsize=3,
            color=_scheme_color(scheme),
            label=_scheme_label(scheme),
        )

    ax.set_xlabel("Mean Discovery Bytes / Query")
    ax.set_ylabel("ServiceSuccess@1")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    _save(fig, "fig_main_success_overhead.pdf")


def _plot_object_manifest_sweep() -> None:
    frame = _read_csv(_aggregate_path("object_main_manifest_sweep.csv"))
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "Awaiting object manifest-sweep aggregate")
        return

    frame = frame[frame["scheme"].isin(COMPACT_OBJECT_MAIN_SCHEMES)].copy()
    frame = _ordered_rows(frame, COMPACT_OBJECT_MAIN_SCHEMES)
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "No manifest-sweep rows found")
        return

    fig, axes = plt.subplots(1, 2, figsize=(8.7, 3.35), sharex=True)
    schemes = [scheme for scheme in COMPACT_OBJECT_MAIN_SCHEMES if scheme in set(frame["scheme"])]

    _line_panel(
        axes[0],
        frame,
        schemes,
        "manifest_size",
        "mean_success_at_1",
        "ci_success_at_1",
        "ServiceSuccess@1",
        "Manifest size",
    )
    axes[0].set_xticks(sorted(frame["manifest_size"].unique().tolist()))
    axes[0].set_ylim(0.5, 1.03)
    _add_panel_label(axes[0], "A")

    _line_panel(
        axes[1],
        frame,
        schemes,
        "manifest_size",
        "wrong_object_rate",
        "ci_wrong_object_rate",
        "Wrong-object rate",
        "Manifest size",
    )
    axes[1].set_xticks(sorted(frame["manifest_size"].unique().tolist()))
    axes[1].set_ylim(0.0, max(0.22, float(frame["wrong_object_rate"].max()) + 0.03))
    axes[1].legend(fontsize=7.8, frameon=False, loc="upper right")
    _add_panel_label(axes[1], "B")

    _save(fig, "fig_failure_breakdown.pdf")


def plot_failure_breakdown() -> None:
    if _is_experiment("exp_object_main_v3", "exp_object_main_v3_compact"):
        _plot_object_manifest_sweep()
        return

    frame = _read_csv(_aggregate_path("failure_breakdown.csv"))
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_failure_breakdown.pdf", "Figure 5", "No comparable discovery baselines found")
        return
    if CURRENT_EXPERIMENT and CURRENT_EXPERIMENT.get("manifest_sizes"):
        selected_manifest = _selected_manifest()
        frame = frame[frame["manifest_size"] == selected_manifest].copy()
    elif "budget" in frame.columns and frame["budget"].nunique() > 1:
        selected_budget = _selected_budget()
        selected_budget = selected_budget if selected_budget in set(frame["budget"]) else sorted(set(frame["budget"]))[0]
        frame = frame[frame["budget"] == selected_budget].copy()

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
    ax.legend(fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.18), frameon=False)
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_failure_breakdown.pdf")


def plot_candidate_shrinkage() -> None:
    frame = _read_csv(_aggregate_path("candidate_shrinkage.csv"))
    if frame.empty:
        _placeholder("fig_candidate_shrinkage.pdf", "Figure 6", "Awaiting aggregate data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(10.0, 3.9), gridspec_kw={"width_ratios": [1.6, 1.0]})
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
        marker=MARKERS["hiroute"],
        linewidth=2.0,
        color=_scheme_color("hiroute"),
    )
    left.set_xticks(x_positions)
    left.set_xticklabels([SHRINKAGE_STAGE_LABELS[stage] for stage in SHRINKAGE_STAGE_ORDER])
    left.set_ylim(0, 1.05)
    left.set_ylabel("Candidate ratio")
    left.grid(axis="x", alpha=0.2)
    left.grid(axis="y", alpha=0.25)

    main_frame = _read_csv(_aggregate_path("main_success_overhead.csv"))
    main_frame = main_frame[main_frame["scheme"] != "exact"].copy()
    if CURRENT_EXPERIMENT and CURRENT_EXPERIMENT.get("budgets"):
        selected_budget = _selected_budget()
        if selected_budget:
            main_frame = main_frame[main_frame["budget"] == selected_budget].copy()
    ordered_schemes = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(main_frame["scheme"])]
    probe_rows = main_frame.set_index("scheme").reindex(ordered_schemes).dropna(subset=["mean_num_remote_probes"])
    right.bar(
        [_scheme_label(scheme) for scheme in probe_rows.index],
        probe_rows["mean_num_remote_probes"],
        yerr=probe_rows.get("ci_num_remote_probes", pd.Series(0.0, index=probe_rows.index)),
        color=[_scheme_color(scheme) for scheme in probe_rows.index],
        capsize=3,
        alpha=0.92,
    )
    right.set_ylabel("Remote probes / query")
    right.grid(axis="y", alpha=0.25)
    _save(fig, "fig_candidate_shrinkage.pdf")


def plot_deadlines() -> None:
    frame = _read_csv(_aggregate_path("deadline_summary.csv"))
    if frame.empty:
        _placeholder("fig_deadline_summary.pdf", "Figure 7", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder("fig_deadline_summary.pdf", "Figure 7", "No comparable discovery baselines found")
        return
    if CURRENT_EXPERIMENT and CURRENT_EXPERIMENT.get("budgets"):
        selected_budget = _selected_budget()
        if selected_budget:
            frame = frame[frame["budget"] == selected_budget].copy()

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 3.9), gridspec_kw={"width_ratios": [1.5, 1.0]})
    left, right = axes
    ordered_schemes = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(frame["scheme"])]
    for scheme in ordered_schemes:
        group = frame[frame["scheme"] == scheme].sort_values("deadline_ms")
        left.plot(
            group["deadline_ms"],
            group["success_before_deadline_rate"],
            marker=MARKERS.get(scheme, "o"),
            linewidth=2.0,
            color=_scheme_color(scheme),
            label=_scheme_label(scheme),
        )
    left.set_xlabel("Deadline (ms)")
    left.set_ylabel("Success within deadline")
    left.grid(alpha=0.25)
    left.legend(fontsize=7.8, loc="lower right", frameon=False)

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
        alpha=0.92,
    )
    right.set_ylabel("Median successful latency (ms)")
    right.grid(axis="y", alpha=0.25)
    _save(fig, "fig_deadline_summary.pdf")


def plot_state_scaling() -> None:
    frame = _read_csv(_aggregate_path("state_scaling_summary.csv"))
    if frame.empty:
        _placeholder("fig_state_scaling.pdf", "Figure 8", "Awaiting scaling runs")
        return

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
        for scheme, group in axis_rows.groupby("scheme", sort=False):
            ordered = group.sort_values("scaling_value")
            axis.plot(
                ordered["scaling_value"],
                ordered["mean_total_exported_summaries"],
                marker=MARKERS.get(scheme, "o"),
                linewidth=2,
                color=_scheme_color(scheme),
                label=_scheme_label(scheme),
            )
        axis.set_xlabel(xlabel)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Mean exported summaries")
    axes[0].legend(fontsize=8, frameon=False)
    axes[1].legend(fontsize=8, frameon=False)
    _save(fig, "fig_state_scaling.pdf")


def plot_robustness() -> None:
    frame = _read_csv(_aggregate_path("robustness_timeseries.csv"))
    if frame.empty:
        _placeholder("fig_robustness.pdf", "Figure 9", "Awaiting staleness and failure runs")
        return

    variants = list(dict.fromkeys(frame["scenario_variant"].tolist()))
    fig, axes = plt.subplots(1, len(variants), figsize=(5.2 * len(variants), 4.2), sharey=True)
    if len(variants) == 1:
        axes = [axes]
    for axis, variant in zip(axes, variants):
        subset = frame[frame["scenario_variant"] == variant].copy()
        for scheme in [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(subset["scheme"])]:
            group = subset[subset["scheme"] == scheme].sort_values("time_bin_s")
            axis.plot(
                group["time_bin_s"],
                group["success_at_1_rate"],
                marker=MARKERS.get(scheme, "o"),
                linewidth=2,
                color=_scheme_color(scheme),
                label=_scheme_label(scheme),
            )
        axis.set_xlabel("Time (s)")
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("ServiceSuccess@1")
    axes[0].legend(fontsize=8, loc="lower right", frameon=False)
    _save(fig, "fig_robustness.pdf")


def plot_ablation() -> None:
    output_filename = _ablation_filename()
    frame = _read_csv(_aggregate_path("ablation_summary.csv"))
    if frame.empty:
        _placeholder(output_filename, "Figure 10", "Awaiting ablation aggregate")
        return

    selected_manifest = _selected_manifest(1)
    if "manifest_size" in frame.columns:
        frame = frame[frame["manifest_size"] == selected_manifest].copy()
    elif "budget" in frame.columns and frame["budget"].nunique() > 1:
        selected_budget = _selected_budget()
        selected_budget = selected_budget if selected_budget in set(frame["budget"]) else sorted(set(frame["budget"]))[0]
        frame = frame[frame["budget"] == selected_budget].copy()

    schemes = [scheme for scheme in COMPACT_ABLATION_SCHEMES if scheme in set(frame["scheme"])]
    frame = _ordered_rows(frame[frame["scheme"].isin(schemes)].copy(), COMPACT_ABLATION_SCHEMES)
    if frame.empty:
        _placeholder(output_filename, "Figure 10", "No ablation slice found at manifest size 1")
        return

    fig, axes = plt.subplots(1, 3, figsize=(11.6, 3.4), sharex=True)
    x_positions = list(range(len(frame)))
    labels = [_scheme_label(scheme) for scheme in frame["scheme"]]
    colors = [_scheme_color(scheme) for scheme in frame["scheme"]]

    panels = [
        ("mean_success_at_1", "ServiceSuccess@1", (0.0, 1.02)),
        ("wrong_object_rate", "Wrong-object rate", (0.0, max(0.22, float(frame["wrong_object_rate"].max()) + 0.03))),
        ("mean_discovery_bytes", "Discovery bytes / query", None),
    ]
    for index, (axis, (column, ylabel, ylim)) in enumerate(zip(axes, panels)):
        axis.bar(x_positions, frame[column], color=colors, alpha=0.92, width=0.68)
        axis.set_ylabel(ylabel)
        if ylim is not None:
            axis.set_ylim(*ylim)
        axis.grid(axis="y", alpha=0.22)
        axis.set_axisbelow(True)
        axis.set_xticks(x_positions)
        axis.set_xticklabels(labels, rotation=18, ha="right")
        _add_panel_label(axis, chr(ord("A") + index))
    _save(fig, output_filename)


def main() -> int:
    global CURRENT_EXPERIMENT
    args = parse_args()
    if args.experiment:
        CURRENT_EXPERIMENT = load_experiment(args.experiment)
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.labelsize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
        }
    )

    plotters = [
        ("fig_main_success_overhead.pdf", plot_main_success),
        ("fig_failure_breakdown.pdf", plot_failure_breakdown),
        ("fig_candidate_shrinkage.pdf", plot_candidate_shrinkage),
        ("fig_deadline_summary.pdf", plot_deadlines),
        ("fig_state_scaling.pdf", plot_state_scaling),
        ("fig_robustness.pdf", plot_robustness),
        ("fig_ablation.pdf", plot_ablation),
        ("fig_ablation_summary.pdf", plot_ablation),
    ]

    if CURRENT_EXPERIMENT is None:
        seen = set()
        for _, plotter in plotters:
            if plotter in seen:
                continue
            plotter()
            seen.add(plotter)
    else:
        outputs = _output_filenames()
        for filename, plotter in plotters:
            if filename in outputs:
                plotter()

    if CURRENT_EXPERIMENT and is_v3_experiment(CURRENT_EXPERIMENT):
        print("results/figures/v3")
    else:
        print("results/figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
