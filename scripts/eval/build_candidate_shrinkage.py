"""Build Figure 6 candidate shrinkage summary from staged search traces."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import aggregate_output_path, load_experiment, log_frame, require_rows, sweep_field
from tools.workflow_support import write_csv


STAGE_ORDER = [
    "all_domains",
    "predicate_filtered_domains",
    "level0_cells",
    "level1_cells",
    "refined_cells",
    "probed_cells",
    "manifest_candidates",
]

OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "budget",
    "manifest_size",
    "stage",
    "run_count",
    "query_count",
    "mean_candidate_count",
    "mean_selected_count",
    "mean_frontier_size",
    "mean_shrinkage_ratio",
    "median_shrinkage_ratio",
    "source_run_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    rows = require_rows(experiment, args.registry_source)
    frame = log_frame(rows, "search_trace.csv")
    if frame.empty:
        print("ERROR: staged search traces are missing")
        return 1
    query_frame = log_frame(rows, "query_log.csv")
    if query_frame.empty:
        print("ERROR: query logs are missing")
        return 1
    valid_queries = query_frame[["run_id", "query_id"]].drop_duplicates()
    frame = frame.merge(valid_queries, on=["run_id", "query_id"], how="inner")

    active_sweep_field = sweep_field(experiment)
    selected_budget = int(experiment.get("default_budget") or 0)
    selected_manifest_size = int(experiment.get("default_manifest_size") or 0)
    if active_sweep_field == "budget" and selected_budget:
        frame = frame[frame["budget"] == selected_budget].copy()
    if active_sweep_field == "manifest_size" and selected_manifest_size:
        frame = frame[frame["manifest_size"] == selected_manifest_size].copy()

    frame = frame[frame["stage"].isin(STAGE_ORDER)].copy()
    frame = frame[frame["registry_scheme"] != "exact"].copy()
    if frame.empty:
        print("ERROR: no discovery schemes with staged search traces are available")
        return 1

    for column in ["candidate_count", "selected_count", "frontier_size", "timestamp_ms"]:
        frame[column] = frame[column].astype(float)

    frame = frame.sort_values(["run_id", "query_id", "timestamp_ms"])
    per_query_stage = (
        frame.groupby(
            [
                "run_id",
                "registry_scheme",
                "registry_topology_id",
                "budget",
                "manifest_size",
                "query_id",
                "stage",
            ],
            as_index=False,
        )
        .agg(
            candidate_count=("candidate_count", "max"),
            selected_count=("selected_count", "max"),
            frontier_size=("frontier_size", "max"),
        )
    )

    baselines = (
        per_query_stage[per_query_stage["stage"] == "all_domains"][
            ["run_id", "query_id", "candidate_count"]
        ]
        .rename(columns={"candidate_count": "all_domain_count"})
    )
    per_query_stage = per_query_stage.merge(baselines, on=["run_id", "query_id"], how="left")
    per_query_stage["all_domain_count"] = per_query_stage["all_domain_count"].clip(lower=1.0)
    per_query_stage["shrinkage_ratio"] = (
        per_query_stage["candidate_count"] / per_query_stage["all_domain_count"]
    )

    output_rows = []
    for (scheme, topology_id), group in per_query_stage.groupby(
        ["registry_scheme", "registry_topology_id"], sort=False
    ):
        run_ids = sorted(group["run_id"].astype(str).unique().tolist())
        for stage in STAGE_ORDER:
            stage_rows = group[group["stage"] == stage]
            if stage_rows.empty:
                continue
            output_rows.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "scheme": scheme,
                    "topology_id": topology_id,
                    "budget": selected_budget if active_sweep_field == "budget" else int(group["budget"].max()),
                    "manifest_size": (
                        selected_manifest_size if active_sweep_field == "manifest_size" else int(group["manifest_size"].max())
                    ),
                    "stage": stage,
                    "run_count": len(run_ids),
                    "query_count": int(stage_rows["query_id"].nunique()),
                    "mean_candidate_count": round(stage_rows["candidate_count"].mean(), 6),
                    "mean_selected_count": round(stage_rows["selected_count"].mean(), 6),
                    "mean_frontier_size": round(stage_rows["frontier_size"].mean(), 6),
                    "mean_shrinkage_ratio": round(stage_rows["shrinkage_ratio"].mean(), 6),
                    "median_shrinkage_ratio": round(stage_rows["shrinkage_ratio"].median(), 6),
                    "source_run_ids": "|".join(run_ids),
                }
            )

    aggregate_path = aggregate_output_path(experiment, "candidate_shrinkage.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
