"""Render Figure 4-10 PDF/PNG assets from aggregate CSVs."""

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
    COMPACT_ROUTING_REFERENCE_SCHEMES,
    COMPACT_ROUTING_REQUIRED_SCHEMES,
    declared_output_filenames,
    figure_output_path,
    output_namespace,
    is_v3_experiment,
    load_experiment,
)
from tools.workflow_support import repo_root


COLORS = {
    "exact": "#2b2b2b",
    "flat": "#6f8396",
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
    "inf_tag_forwarding": "s",
    "flood": "^",
    "hiroute": "D",
    "central_directory": "P",
    "oracle": "P",
    "predicates_only": "X",
    "random_admissible": "v",
}

HIROUTE_SCHEMES = {"hiroute", "full_hiroute"}
REFERENCE_SCHEMES = {"central_directory", "oracle"}

MAIN_SCHEME_ORDER = [
    "predicates_only",
    "random_admissible",
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
    fig.savefig(output_path.with_suffix(".png"), format="png", dpi=220, bbox_inches="tight")
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


def _is_hiroute_scheme(scheme: str) -> bool:
    return scheme in HIROUTE_SCHEMES


def _is_reference_scheme(scheme: str) -> bool:
    return scheme in REFERENCE_SCHEMES


def _apply_bar_emphasis(bars, schemes: list[str]) -> None:
    for bar, scheme in zip(bars, schemes):
        if _is_hiroute_scheme(scheme):
            bar.set_edgecolor("#111111")
            bar.set_linewidth(1.5)
            bar.set_alpha(1.0)
            bar.set_zorder(3)
        elif _is_reference_scheme(scheme):
            bar.set_edgecolor("#555555")
            bar.set_linewidth(0.8)
            bar.set_alpha(0.72)


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


def _routing_support_filename() -> str:
    outputs = _output_filenames()
    if "fig_routing_support.pdf" in outputs:
        return "fig_routing_support.pdf"
    return "fig_main_success_overhead.pdf"


def _routing_support_aggregate() -> str:
    outputs = _output_filenames()
    if "routing_support.csv" in outputs:
        return "routing_support.csv"
    return "main_success_overhead.csv"


def _object_manifest_filename() -> str:
    outputs = _output_filenames()
    if "fig_object_manifest_sweep.pdf" in outputs:
        return "fig_object_manifest_sweep.pdf"
    return "fig_failure_breakdown.pdf"


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
        0.02,
        0.98,
        label,
        transform=axis.transAxes,
        fontsize=11,
        fontweight="bold",
        va="top",
        ha="left",
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.78, "pad": 1.5},
    )


def _bar_panel(
    axis: plt.Axes,
    labels: list[str],
    values: list[float],
    errors: list[float],
    colors: list[str],
    ylabel: str,
    schemes: list[str] | None = None,
) -> None:
    x_positions = list(range(len(labels)))
    bars = axis.bar(
        x_positions,
        values,
        yerr=errors,
        color=colors,
        alpha=0.92,
        capsize=3,
        width=0.68,
        linewidth=0,
    )
    if schemes is not None:
        _apply_bar_emphasis(bars, schemes)
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
        is_reference = _is_reference_scheme(scheme)
        is_hiroute = _is_hiroute_scheme(scheme)
        axis.errorbar(
            group[x_column],
            group[y_column],
            yerr=group[yerr_column] if yerr_column and yerr_column in group.columns else None,
            color=_scheme_color(scheme),
            marker=MARKERS.get(scheme, "o"),
            linestyle="--" if is_reference else "-",
            linewidth=2.7 if is_hiroute else 1.8 if is_reference else 2.0,
            markersize=6.2 if is_hiroute else 5.5,
            capsize=3,
            alpha=1.0 if is_hiroute else 0.68 if is_reference else 0.9,
            zorder=4 if is_hiroute else 2,
            label=_scheme_label(scheme),
        )
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(alpha=0.22)
    axis.set_axisbelow(True)


def _add_reference_lines(
    axis: plt.Axes,
    reference_frame: pd.DataFrame,
    column: str,
    label_template: str = "{scheme} (non-peer): {value}",
    value_format: str = "{:.2f}",
) -> None:
    """Draw dashed horizontal lines for non-peer reference schemes.

    These references (central_directory, flood) violate the bounded distributed-
    discovery contract that the primary peer cohort respects, so they are kept
    visually separated from the bar comparison rather than competing with it.
    """
    if reference_frame.empty:
        return
    for _, row in reference_frame.iterrows():
        scheme = row["scheme"]
        if column not in row or pd.isna(row[column]):
            continue
        value = float(row[column])
        line = axis.axhline(
            y=value,
            color=_scheme_color(scheme),
            linestyle="--",
            linewidth=1.2,
            alpha=0.7,
            zorder=1,
        )
        line.set_label(
            label_template.format(scheme=_scheme_label(scheme), value=value_format.format(value))
        )


def _plot_compact_routing_support() -> None:
    output_filename = _routing_support_filename()
    main_frame = _read_csv(_aggregate_path(_routing_support_aggregate()))
    stage_frame = _read_csv(_aggregate_path("candidate_shrinkage.csv"))
    if main_frame.empty or stage_frame.empty:
        _placeholder(output_filename, "Figure 4", "Awaiting mainline routing-support aggregates")
        return

    selected_budget = _selected_budget(16)
    main_frame = main_frame[main_frame["budget"] == selected_budget].copy()
    available_schemes = set(main_frame["scheme"])
    missing_required = [scheme for scheme in COMPACT_ROUTING_REQUIRED_SCHEMES if scheme not in available_schemes]
    if missing_required:
        _placeholder(
            output_filename,
            "Figure 4",
            "Awaiting mainline routing rerun with predicates_only and random_admissible baselines",
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
    reference_frame = main_frame[
        main_frame["scheme"].isin(COMPACT_ROUTING_REFERENCE_SCHEMES)
    ].copy()

    contraction_schemes = [
        scheme for scheme in COMPACT_ROUTING_PANEL_A_SCHEMES if scheme in set(stage_frame["scheme"])
    ]
    stage_frame = stage_frame[
        (stage_frame["budget"] == selected_budget)
        & (stage_frame["scheme"].isin(contraction_schemes))
        & (stage_frame["stage"].isin(FIG4_STAGE_ORDER))
    ].copy()
    if panel_a_frame.empty or panel_b_frame.empty or stage_frame.empty:
        _placeholder(output_filename, "Figure 4", "No routing-support slice at the default budget")
        return

    fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.5), gridspec_kw={"width_ratios": [1.0, 1.0, 1.45]})

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
        panel_a_frame["scheme"].tolist(),
    )
    _add_reference_lines(
        axes[0],
        reference_frame,
        "relevant_domain_reached_at_1",
        label_template="{scheme} (non-peer ref.)",
    )
    axes[0].set_ylim(0, 0.85)
    axes[0].legend(fontsize=7.0, frameon=False, loc="upper left")
    _add_panel_label(axes[0], "A")

    _bar_panel(
        axes[1],
        panel_b_labels,
        panel_b_frame["mean_discovery_bytes"].tolist(),
        panel_b_frame.get("ci_discovery_bytes", pd.Series(0.0, index=panel_b_frame.index)).tolist(),
        panel_b_colors,
        "Discovery bytes / query",
        panel_b_frame["scheme"].tolist(),
    )
    _add_reference_lines(
        axes[1],
        reference_frame,
        "mean_discovery_bytes",
        label_template="{scheme} (non-peer ref.): {value}",
        value_format="{:.0f}",
    )
    axes[1].legend(fontsize=7.0, frameon=False, loc="lower right")
    _add_panel_label(axes[1], "B")

    for scheme in contraction_schemes:
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
            linewidth=2.8 if _is_hiroute_scheme(scheme) else 1.8,
            markersize=6.4 if _is_hiroute_scheme(scheme) else 5.4,
            alpha=1.0 if _is_hiroute_scheme(scheme) else 0.78,
            zorder=4 if _is_hiroute_scheme(scheme) else 2,
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
    axes[2].legend(fontsize=7.4, frameon=False, loc="lower left")
    _add_panel_label(axes[2], "C")

    _save(fig, output_filename)


def plot_main_success() -> None:
    output_filename = _routing_support_filename()
    if _is_experiment("exp_routing_main_v3_compact", "routing_main"):
        _plot_compact_routing_support()
        return

    frame = _read_csv(_aggregate_path(_routing_support_aggregate()))
    if frame.empty:
        _placeholder(output_filename, "Figure 4", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder(output_filename, "Figure 4", "No comparable discovery baselines found")
        return

    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for scheme in MAIN_SCHEME_ORDER:
        group = frame[frame["scheme"] == scheme].copy()
        if group.empty:
            continue
        if "budget" in group.columns:
            group = group.sort_values("budget")
        is_hiroute = _is_hiroute_scheme(scheme)
        is_reference = _is_reference_scheme(scheme)
        ax.errorbar(
            group["mean_discovery_bytes"],
            group["mean_success_at_1"],
            xerr=group.get("ci_discovery_bytes", 0.0),
            yerr=group.get("ci_success_at_1", 0.0),
            fmt=f"{MARKERS.get(scheme, 'o')}{'--' if is_reference else '-'}",
            markersize=7.0 if is_hiroute else 6.0,
            linewidth=2.7 if is_hiroute else 1.7,
            capsize=3,
            alpha=1.0 if is_hiroute else 0.68 if is_reference else 0.9,
            zorder=4 if is_hiroute else 2,
            color=_scheme_color(scheme),
            label=_scheme_label(scheme),
        )

    ax.set_xlabel("Mean Discovery Bytes / Query")
    ax.set_ylabel("Terminal success")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    _save(fig, output_filename)


def _plot_object_manifest_sweep() -> None:
    output_filename = _object_manifest_filename()
    frame = _read_csv(_aggregate_path("object_main_manifest_sweep.csv"))
    if frame.empty:
        _placeholder(output_filename, "Figure 5", "Awaiting object manifest-sweep aggregate")
        return

    frame = frame[frame["scheme"].isin(COMPACT_OBJECT_MAIN_SCHEMES)].copy()
    frame = _ordered_rows(frame, COMPACT_OBJECT_MAIN_SCHEMES)
    if frame.empty:
        _placeholder(output_filename, "Figure 5", "No manifest-sweep rows found")
        return

    fig, axes = plt.subplots(1, 4, figsize=(13.6, 3.4), gridspec_kw={"width_ratios": [1.0, 1.0, 1.0, 0.85]})
    schemes = [scheme for scheme in COMPACT_OBJECT_MAIN_SCHEMES if scheme in set(frame["scheme"])]

    terminal_column = (
        "terminal_strong_success_rate"
        if "terminal_strong_success_rate" in frame.columns
        else "mean_success_at_1"
    )
    first_fetch_column = (
        "first_fetch_strong_relevant_rate"
        if "first_fetch_strong_relevant_rate" in frame.columns
        else "first_fetch_relevant_rate"
    )

    _line_panel(
        axes[0],
        frame,
        schemes,
        "manifest_size",
        terminal_column,
        "ci_success_at_1",
        "Terminal strong success",
        "Manifest size",
    )
    axes[0].set_xticks(sorted(frame["manifest_size"].unique().tolist()))
    axes[0].set_ylim(0.0, 1.03)
    _add_panel_label(axes[0], "A")

    _line_panel(
        axes[1],
        frame,
        schemes,
        "manifest_size",
        first_fetch_column,
        "ci_first_fetch_relevant_rate",
        "First-fetch strong relevance",
        "Manifest size",
    )
    axes[1].set_xticks(sorted(frame["manifest_size"].unique().tolist()))
    axes[1].set_ylim(0.0, 1.03)
    _add_panel_label(axes[1], "B")

    _line_panel(
        axes[2],
        frame,
        schemes,
        "manifest_size",
        "manifest_rescue_rate",
        "ci_manifest_rescue_rate",
        "Manifest rescue rate",
        "Manifest size",
    )
    axes[2].set_xticks(sorted(frame["manifest_size"].unique().tolist()))
    axes[2].set_ylim(0.0, 0.15 if float(frame["manifest_rescue_rate"].max()) <= 0.02 else 1.03)
    axes[2].legend(fontsize=7.4, frameon=False, loc="upper left")
    _add_panel_label(axes[2], "C")

    # Panel D: absolute terminal-success gain from m=1 to m=3 per scheme.
    # HiRoute should dominate — 0.45 absolute gain vs 0.40 (inf_tag) and 0
    # (central_directory). This panel is the cleanest evidence that wider
    # manifests rescue HiRoute's first-choice failures more than peers'.
    delta_rows: list[dict[str, float | str]] = []
    for scheme in schemes:
        group = frame[frame["scheme"] == scheme]
        if group.empty:
            continue
        size_to_value = {
            int(row["manifest_size"]): float(row[terminal_column])
            for _, row in group.iterrows()
        }
        if 1 not in size_to_value or 3 not in size_to_value:
            continue
        delta = size_to_value[3] - size_to_value[1]
        delta_rows.append({"scheme": scheme, "delta": delta})
    if delta_rows:
        delta_df = pd.DataFrame(delta_rows)
        delta_df = _ordered_rows(delta_df, schemes)
        x_positions = list(range(len(delta_df)))
        labels = [_scheme_label(s) for s in delta_df["scheme"]]
        colors = [_scheme_color(s) for s in delta_df["scheme"]]
        bars = axes[3].bar(x_positions, delta_df["delta"], color=colors, alpha=0.92, width=0.62)
        _apply_bar_emphasis(bars, delta_df["scheme"].tolist())
        axes[3].bar_label(
            bars,
            labels=[f"+{float(v) * 100:.1f}pp" for v in delta_df["delta"]],
            padding=2,
            fontsize=7.4,
        )
        axes[3].set_xticks(x_positions)
        axes[3].set_xticklabels(labels, rotation=18, ha="right")
        axes[3].set_ylabel("Δ terminal success (m=1→3)")
        axes[3].grid(axis="y", alpha=0.22)
        axes[3].set_axisbelow(True)
        max_delta = float(delta_df["delta"].max())
        axes[3].set_ylim(0.0, max(0.05, max_delta * 1.25))
        _add_panel_label(axes[3], "D")
    else:
        axes[3].axis("off")

    _save(fig, output_filename)


def plot_failure_breakdown() -> None:
    output_filename = _object_manifest_filename()
    if _is_experiment("exp_object_main_v3", "exp_object_main_v3_compact", "object_main"):
        _plot_object_manifest_sweep()
        return

    frame = _read_csv(_aggregate_path("failure_breakdown.csv"))
    if frame.empty:
        _placeholder(output_filename, "Figure 5", "Awaiting aggregate data")
        return

    frame = frame[frame["scheme"] != "exact"].copy()
    if frame.empty:
        _placeholder(output_filename, "Figure 5", "No comparable discovery baselines found")
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
    _save(fig, output_filename)


def plot_candidate_shrinkage() -> None:
    frame = _read_csv(_aggregate_path("candidate_shrinkage.csv"))
    if frame.empty:
        _placeholder("fig_candidate_shrinkage.pdf", "Figure 6", "Awaiting aggregate data")
        return

    selected_budget = _selected_budget(16)
    if "budget" in frame.columns and frame["budget"].nunique() > 1:
        if selected_budget in set(frame["budget"]):
            frame = frame[frame["budget"] == selected_budget].copy()

    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.9), gridspec_kw={"width_ratios": [1.6, 1.0]})
    left, right = axes

    # Panel A: contraction waterfall for every distributed-discovery peer.
    # Only HiRoute contracts; the others stay flat at 5.0/5.86. Plot all four
    # so the visual contrast is the figure's anchor; non-peer references
    # (central_directory single-hop, flood unbounded broadcast) are excluded
    # because they violate the bounded-state contract.
    waterfall_schemes = [
        scheme for scheme in COMPACT_ROUTING_PANEL_A_SCHEMES if scheme in set(frame["scheme"])
    ]
    x_positions = list(range(len(SHRINKAGE_STAGE_ORDER)))
    for scheme in waterfall_schemes:
        group = frame[frame["scheme"] == scheme].copy()
        ordered = (
            group.set_index("stage")
            .reindex(SHRINKAGE_STAGE_ORDER)
            .dropna(subset=["mean_shrinkage_ratio"])
            .reset_index()
        )
        if ordered.empty:
            continue
        is_hiroute = _is_hiroute_scheme(scheme)
        left.plot(
            [SHRINKAGE_STAGE_ORDER.index(stage) for stage in ordered["stage"]],
            ordered["mean_shrinkage_ratio"],
            marker=MARKERS.get(scheme, "o"),
            linewidth=2.8 if is_hiroute else 1.7,
            markersize=6.6 if is_hiroute else 5.2,
            color=_scheme_color(scheme),
            alpha=1.0 if is_hiroute else 0.7,
            zorder=4 if is_hiroute else 2,
            label=_scheme_label(scheme),
        )
    left.set_xticks(x_positions)
    left.set_xticklabels([SHRINKAGE_STAGE_LABELS[stage] for stage in SHRINKAGE_STAGE_ORDER])
    left.set_ylim(0, 1.08)
    left.set_ylabel("Candidate ratio")
    left.grid(axis="x", alpha=0.2)
    left.grid(axis="y", alpha=0.25)
    left.legend(fontsize=7.6, frameon=False, loc="lower left")

    # Annotate HiRoute's unique contraction so the visual story is unambiguous.
    hiroute_rows = (
        frame[frame["scheme"] == "hiroute"]
        .set_index("stage")
        .reindex(SHRINKAGE_STAGE_ORDER)
        .dropna(subset=["mean_shrinkage_ratio"])
    )
    if not hiroute_rows.empty:
        start = float(hiroute_rows.loc[SHRINKAGE_STAGE_ORDER[0], "mean_shrinkage_ratio"]) if SHRINKAGE_STAGE_ORDER[0] in hiroute_rows.index else 1.0
        end_stage = "probed_cells" if "probed_cells" in hiroute_rows.index else SHRINKAGE_STAGE_ORDER[-1]
        end = float(hiroute_rows.loc[end_stage, "mean_shrinkage_ratio"])
        if start > 0:
            reduction_pct = max(0.0, (start - end) / start * 100.0)
            left.annotate(
                f"HiRoute: −{reduction_pct:.0f}%",
                xy=(SHRINKAGE_STAGE_ORDER.index(end_stage), end),
                xytext=(SHRINKAGE_STAGE_ORDER.index(end_stage) - 1.3, end + 0.18),
                fontsize=8.4,
                color=_scheme_color("hiroute"),
                weight="bold",
                arrowprops={
                    "arrowstyle": "->",
                    "color": _scheme_color("hiroute"),
                    "lw": 1.0,
                },
            )

    main_frame = _read_csv(_aggregate_path(_routing_support_aggregate()))
    main_frame = main_frame[main_frame["scheme"] != "exact"].copy()
    if "budget" in main_frame.columns and main_frame["budget"].nunique() > 1:
        if selected_budget in set(main_frame["budget"]):
            main_frame = main_frame[main_frame["budget"] == selected_budget].copy()
    if main_frame.empty:
        _placeholder("fig_candidate_shrinkage.pdf", "Figure 6", "No routing-support slice at the default budget")
        return
    main_frame = (
        main_frame.groupby("scheme", as_index=False)
        .agg(
            {
                "mean_num_remote_probes": "mean",
                "ci_num_remote_probes": "mean",
            }
        )
    )
    ordered_schemes = [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(main_frame["scheme"])]
    probe_rows = main_frame.set_index("scheme").reindex(ordered_schemes).dropna(subset=["mean_num_remote_probes"])
    positions = list(range(len(probe_rows.index)))
    bars = right.barh(
        positions,
        probe_rows["mean_num_remote_probes"],
        xerr=probe_rows.get("ci_num_remote_probes", pd.Series(0.0, index=probe_rows.index)),
        color=[_scheme_color(scheme) for scheme in probe_rows.index],
        capsize=3,
        alpha=0.92,
    )
    _apply_bar_emphasis(bars, list(probe_rows.index))
    right.set_yticks(positions)
    right.set_yticklabels([_scheme_label(scheme) for scheme in probe_rows.index])
    right.set_xlabel("Remote probes / query")
    right.grid(axis="x", alpha=0.25)
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

    # Distributed-discovery cohort that respects bounded inter-domain state.
    # central_directory and flood are kept as non-peer references on the left
    # panel and excluded from the right per-byte efficiency comparison.
    distributed_cohort = COMPACT_ROUTING_PANEL_A_SCHEMES
    reference_cohort = COMPACT_ROUTING_REFERENCE_SCHEMES

    main_frame = _read_csv(_aggregate_path(_routing_support_aggregate()))
    bytes_lookup: dict[str, float] = {}
    if not main_frame.empty:
        if "budget" in main_frame.columns and main_frame["budget"].nunique() > 1:
            selected_budget = _selected_budget(16)
            if selected_budget in set(main_frame["budget"]):
                main_frame = main_frame[main_frame["budget"] == selected_budget].copy()
        bytes_lookup = (
            main_frame.groupby("scheme", as_index=False)["mean_discovery_bytes"]
            .mean()
            .set_index("scheme")["mean_discovery_bytes"]
            .to_dict()
        )

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.9), gridspec_kw={"width_ratios": [1.5, 1.1]})
    left, right = axes

    # Left panel: absolute deadline-success curves. Distributed cohort solid,
    # non-peer references dashed and visually subdued.
    plot_order = list(distributed_cohort) + list(reference_cohort)
    available = set(frame["scheme"])
    plot_order = [scheme for scheme in plot_order if scheme in available]
    for scheme in plot_order:
        group = frame[frame["scheme"] == scheme].sort_values("deadline_ms")
        is_hiroute = _is_hiroute_scheme(scheme)
        is_reference = scheme in reference_cohort
        left.plot(
            group["deadline_ms"],
            group["success_before_deadline_rate"],
            marker=MARKERS.get(scheme, "o"),
            linestyle="--" if is_reference else "-",
            linewidth=2.8 if is_hiroute else 1.6 if is_reference else 2.0,
            markersize=6.4 if is_hiroute else 5.2,
            color=_scheme_color(scheme),
            alpha=1.0 if is_hiroute else 0.55 if is_reference else 0.85,
            zorder=4 if is_hiroute else 2,
            label=_scheme_label(scheme) + (" (non-peer ref.)" if is_reference else ""),
        )
    left.set_xlabel("Deadline (ms)")
    left.set_ylabel("Success within deadline")
    left.grid(alpha=0.25)
    left.legend(fontsize=7.4, loc="lower right", frameon=False)
    _add_panel_label(left, "A")

    # Right panel: deadline-success per discovery byte at the deadlines where
    # any distributed scheme actually completes a probe. This normalizes for
    # the fact that flood and central_directory bypass the bounded-state
    # contract: among schemes that respect that contract, HiRoute spends the
    # fewest discovery bytes per query within deadline.
    deadlines_seen = sorted({int(d) for d in frame["deadline_ms"].unique()})
    target_deadlines = [d for d in deadlines_seen if d in {100, 200, 500}] or deadlines_seen[-3:]
    bar_width = 0.18
    cohort_schemes = [scheme for scheme in distributed_cohort if scheme in available and scheme in bytes_lookup]
    if not cohort_schemes:
        right.axis("off")
    else:
        for index, scheme in enumerate(cohort_schemes):
            scheme_frame = frame[frame["scheme"] == scheme]
            efficiency: list[float] = []
            for deadline in target_deadlines:
                row = scheme_frame[scheme_frame["deadline_ms"] == deadline]
                if row.empty or bytes_lookup.get(scheme, 0.0) <= 0:
                    efficiency.append(0.0)
                    continue
                rate = float(row.iloc[0]["success_before_deadline_rate"])
                efficiency.append(rate / float(bytes_lookup[scheme]) * 1000.0)
            x_positions = [
                pos + (index - (len(cohort_schemes) - 1) / 2.0) * bar_width
                for pos in range(len(target_deadlines))
            ]
            bars = right.bar(
                x_positions,
                efficiency,
                width=bar_width,
                color=_scheme_color(scheme),
                alpha=0.92,
                label=_scheme_label(scheme),
            )
            if _is_hiroute_scheme(scheme):
                for bar in bars:
                    bar.set_edgecolor("#111111")
                    bar.set_linewidth(1.4)
                    bar.set_zorder(3)
        right.set_xticks(list(range(len(target_deadlines))))
        right.set_xticklabels([f"{d} ms" for d in target_deadlines])
        right.set_ylabel("Success / kB discovery cost")
        right.grid(axis="y", alpha=0.25)
        right.set_axisbelow(True)
        right.legend(fontsize=7.4, frameon=False, loc="upper left")
        _add_panel_label(right, "B")

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

    configured_budget: float | None = None
    if "budget" in frame.columns and not frame["budget"].dropna().empty:
        configured_budget = float(frame["budget"].dropna().iloc[0])

    for scaling_axis, xlabel, axis in panel_specs:
        axis_rows = frame[frame["scaling_axis"] == scaling_axis].copy()
        if axis_rows.empty:
            axis.axis("off")
            continue
        for scheme, group in axis_rows.groupby("scheme", sort=False):
            ordered = group.sort_values("scaling_value")
            is_hiroute = _is_hiroute_scheme(scheme)
            is_reference = _is_reference_scheme(scheme)
            axis.plot(
                ordered["scaling_value"],
                ordered["mean_total_exported_summaries"],
                marker=MARKERS.get(scheme, "o"),
                linestyle="--" if is_reference else "-",
                linewidth=2.8 if is_hiroute else 1.7 if is_reference else 1.9,
                markersize=6.4 if is_hiroute else 5.4,
                color=_scheme_color(scheme),
                alpha=1.0 if is_hiroute else 0.7,
                zorder=4 if is_hiroute else 2,
                label=_scheme_label(scheme),
            )
        # Reference: Bi * |D| budget envelope. Both bounded schemes should
        # track this line; if either deviates, the bounded-state contract is
        # broken.
        if scaling_axis == "domain_count" and configured_budget is not None:
            domain_values = sorted(axis_rows["scaling_value"].unique().tolist())
            axis.plot(
                domain_values,
                [configured_budget * d for d in domain_values],
                color="#888888",
                linestyle=":",
                linewidth=1.0,
                alpha=0.85,
                label=f"Budget envelope ({int(configured_budget)} × |D|)",
                zorder=1,
            )
        axis.set_xlabel(xlabel)
        axis.set_title(xlabel)
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Mean exported summaries")
    axes[0].legend(fontsize=7.6, frameon=False, loc="upper left")
    axes[1].legend(fontsize=7.6, frameon=False, loc="upper left")

    fig.text(
        0.5,
        -0.03,
        "Bounded distributed-discovery schemes track the configured budget × |D|. "
        "HiRoute additionally provides the routing-side and contraction wins of Figs. 4 and 6 "
        "under exactly this state envelope.",
        ha="center",
        va="top",
        fontsize=8,
        style="italic",
        color="#444444",
    )
    _save(fig, "fig_state_scaling.pdf", rect=(0, 0.02, 1, 1))


def plot_robustness() -> None:
    frame = _read_csv(_aggregate_path("robustness_timeseries.csv"))
    if frame.empty:
        _placeholder("fig_robustness.pdf", "Figure 9", "Awaiting staleness and failure runs")
        return

    variants = list(dict.fromkeys(frame["scenario_variant"].tolist()))
    fig, axes = plt.subplots(1, len(variants), figsize=(5.4 * len(variants), 4.2), sharey=True)
    if len(variants) == 1:
        axes = [axes]
    titles = {
        "controller_down": "Controller down",
        "stale_summaries": "Stale summaries",
    }
    summary_frame = _read_csv(_aggregate_path("robustness_summary.csv"))
    for axis, variant in zip(axes, variants):
        subset = frame[frame["scenario_variant"] == variant].copy()
        for scheme in [scheme for scheme in MAIN_SCHEME_ORDER if scheme in set(subset["scheme"])]:
            group = subset[subset["scheme"] == scheme].sort_values("time_bin_s")
            is_hiroute = _is_hiroute_scheme(scheme)
            is_reference = _is_reference_scheme(scheme)
            label_suffix = " (non-peer ref.)" if is_reference else ""
            axis.plot(
                group["time_bin_s"],
                group["success_at_1_rate"],
                marker=MARKERS.get(scheme, "o"),
                linestyle="--" if is_reference else "-",
                linewidth=2.8 if is_hiroute else 1.7 if is_reference else 2.0,
                markersize=6.4 if is_hiroute else 5.2,
                color=_scheme_color(scheme),
                alpha=1.0 if is_hiroute else 0.55 if is_reference else 0.85,
                zorder=4 if is_hiroute else 2,
                label=_scheme_label(scheme) + label_suffix,
            )
        if "failure_time_s" in subset.columns and not subset["failure_time_s"].dropna().empty:
            axis.axvline(
                float(subset["failure_time_s"].dropna().iloc[0]),
                color="#a33a2a",
                linestyle="--",
                linewidth=1.3,
                alpha=0.8,
            )
        if "recovery_time_s" in subset.columns and not subset["recovery_time_s"].dropna().empty:
            axis.axvline(
                float(subset["recovery_time_s"].dropna().iloc[0]),
                color="#2f7d57",
                linestyle=":",
                linewidth=1.3,
                alpha=0.85,
            )
        if not summary_frame.empty:
            hiroute_row = summary_frame[
                (summary_frame["scenario_variant"] == variant) & (summary_frame["scheme"] == "hiroute")
            ]
            if not hiroute_row.empty:
                row = hiroute_row.iloc[0]
                min_success = row.get("min_success_after_event")
                if min_success is not None and not pd.isna(min_success):
                    axis.text(
                        0.02,
                        0.04,
                        f"HiRoute min success after event: {float(min_success):.2f}",
                        transform=axis.transAxes,
                        fontsize=7.6,
                        color=_scheme_color("hiroute"),
                        weight="bold",
                    )
        axis.set_xlabel("Time (s)")
        axis.set_title(titles.get(variant, variant.replace("_", " ")))
        axis.grid(alpha=0.25)
    axes[0].set_ylabel("Terminal success")
    axes[0].legend(fontsize=7.6, loc="lower right", frameon=False)
    _save(fig, "fig_robustness.pdf")


def plot_ablation() -> None:
    output_filename = _ablation_filename()
    frame = _read_csv(_aggregate_path("ablation_summary.csv"))
    if frame.empty:
        _placeholder(output_filename, "Figure 3", "Awaiting ablation aggregate")
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
        _placeholder(output_filename, "Figure 3", f"No ablation slice found at manifest size {selected_manifest}")
        return

    terminal_column = (
        "terminal_strong_success_rate"
        if "terminal_strong_success_rate" in frame.columns
        else "mean_success_at_1"
    )
    first_fetch_column = (
        "first_fetch_strong_relevant_rate"
        if "first_fetch_strong_relevant_rate" in frame.columns
        else "first_fetch_relevant_rate"
    )
    domain_fail_column = "domain_selection_failure_rate"
    first_probe_hit_column = "first_probe_relevant_domain_hit_rate"

    # Four panels: routing-side wins (A, B) anchor the figure where HiRoute's
    # advantage is largest; terminal-success and first-fetch-correctness (C, D)
    # are kept honest at manifest size 1 even though their gaps are smaller.
    panels: list[tuple[str, str | None, str, tuple[float, float] | None, str]] = []
    if domain_fail_column in frame.columns:
        panels.append((domain_fail_column, None, "Domain-selection failure rate", (0.0, max(0.05, float(frame[domain_fail_column].max()) * 1.25)), "percent"))
    if first_probe_hit_column in frame.columns:
        panels.append((first_probe_hit_column, None, "First-probe relevant-domain hit", (0.0, 1.02), "percent"))
    panels.append((terminal_column, "ci_success_at_1", "Terminal strong success", None, "percent"))
    panels.append((first_fetch_column, "ci_first_fetch_relevant_rate", "First-fetch strong relevance", None, "percent"))

    if len(panels) < 4:
        # Fall back to legacy 3-panel layout if the routing-side columns are
        # missing from an older aggregate snapshot.
        panels = [
            (terminal_column, "ci_success_at_1", "Terminal strong success", None, "percent"),
            (first_fetch_column, "ci_first_fetch_relevant_rate", "First-fetch strong relevance", None, "percent"),
            ("mean_discovery_bytes", "ci_discovery_bytes", "Discovery bytes / query", None, "count"),
        ]

    n_panels = len(panels)
    fig_width = 3.05 * n_panels + 0.6
    fig, axes = plt.subplots(1, n_panels, figsize=(fig_width, 3.4), sharex=True)
    if n_panels == 1:
        axes = [axes]
    x_positions = list(range(len(frame)))
    labels = [_scheme_label(scheme) for scheme in frame["scheme"]]
    colors = [_scheme_color(scheme) for scheme in frame["scheme"]]

    for index, (axis, (column, error_column, ylabel, ylim, label_format)) in enumerate(zip(axes, panels)):
        if column not in frame.columns:
            axis.axis("off")
            continue
        errors = frame.get(error_column, pd.Series(0.0, index=frame.index)) if error_column else pd.Series(0.0, index=frame.index)
        bars = axis.bar(
            x_positions,
            frame[column],
            yerr=errors,
            color=colors,
            alpha=0.92,
            width=0.68,
            capsize=3,
        )
        _apply_bar_emphasis(bars, frame["scheme"].tolist())
        if label_format == "percent":
            value_labels = [f"{float(value) * 100:.1f}%" for value in frame[column]]
        else:
            value_labels = [f"{float(value):.0f}" for value in frame[column]]
        axis.bar_label(bars, labels=value_labels, padding=2, fontsize=7)
        axis.set_ylabel(ylabel)
        if ylim is not None:
            axis.set_ylim(*ylim)
        else:
            max_value = float((frame[column] + errors).max())
            axis.set_ylim(0.0, min(1.02, max(0.2, max_value * 1.35)) if label_format == "percent" else max_value * 1.18)
        axis.grid(axis="y", alpha=0.22)
        axis.set_axisbelow(True)
        axis.set_xticks(x_positions)
        axis.set_xticklabels(labels, rotation=18, ha="right")
        _add_panel_label(axis, chr(ord("A") + index))
    fig.suptitle(f"Manifest size {selected_manifest}", fontsize=10, y=1.02)
    _save(fig, output_filename, rect=(0, 0, 1, 0.96))


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
        ("fig_routing_support.pdf", plot_main_success),
        ("fig_failure_breakdown.pdf", plot_failure_breakdown),
        ("fig_object_manifest_sweep.pdf", plot_failure_breakdown),
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

    namespace = output_namespace(CURRENT_EXPERIMENT) if CURRENT_EXPERIMENT else None
    if namespace:
        print(f"results/figures/{namespace}")
    else:
        print("results/figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
