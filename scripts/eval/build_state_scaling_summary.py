"""Build Figure 8 scaling summary from state logs and canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import aggregate_output_path, load_experiment, log_frame, require_rows
from tools.workflow_support import write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "scaling_axis",
    "scaling_value",
    "budget",
    "run_count",
    "query_count",
    "mean_total_exported_summaries",
    "mean_total_exported_summary_bytes",
    "mean_total_summary_updates_sent",
    "mean_objects_in_domain",
    "domains_total",
    "mean_success_at_1",
    "mean_latency_ms",
    "mean_discovery_bytes",
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
    query_frame = log_frame(rows, "query_log.csv")
    state_frame = log_frame(rows, "state_log.csv")
    if state_frame.empty:
        print("ERROR: state logs are missing")
        return 1
    if "scaling_axis" not in state_frame.columns or "scaling_value" not in state_frame.columns:
        print("ERROR: state logs do not expose scaling_axis/scaling_value")
        return 1

    state_frame = state_frame[state_frame["scaling_axis"].isin({"objects_per_domain", "domain_count"})].copy()
    if state_frame.empty:
        print("ERROR: state logs do not contain object/domain scaling sweeps")
        return 1

    for column in [
        "num_exported_summaries",
        "exported_summary_bytes",
        "summary_updates_sent",
        "objects_in_domain",
        "domains_total",
        "budget",
        "scaling_value",
    ]:
        state_frame[column] = state_frame[column].astype(float)

    if not query_frame.empty:
        query_frame["discovery_bytes_total"] = (
            query_frame["discovery_tx_bytes"] + query_frame["discovery_rx_bytes"]
        )
        query_count_by_run = query_frame.groupby("run_id").size().to_dict()
        per_run_query = (
            query_frame.groupby("run_id", as_index=False)
            .agg(
                mean_success_at_1=("success_at_1", "mean"),
                mean_latency_ms=("latency_ms", "mean"),
                mean_discovery_bytes=("discovery_bytes_total", "mean"),
            )
        )
    else:
        query_count_by_run = {}
        per_run_query = None

    per_run_state = (
        state_frame.groupby(
            ["run_id", "registry_scheme", "registry_topology_id", "scaling_axis", "scaling_value"],
            as_index=False,
        )
        .agg(
            total_exported_summaries=("num_exported_summaries", "sum"),
            total_exported_summary_bytes=("exported_summary_bytes", "sum"),
            total_summary_updates_sent=("summary_updates_sent", "sum"),
            mean_objects_in_domain=("objects_in_domain", "mean"),
            domains_total=("domains_total", "max"),
            budget=("budget", "max"),
        )
    )
    if per_run_query is not None:
        per_run_state = per_run_state.merge(per_run_query, on="run_id", how="left")
    else:
        per_run_state["mean_success_at_1"] = float("nan")
        per_run_state["mean_latency_ms"] = float("nan")
        per_run_state["mean_discovery_bytes"] = float("nan")

    output_rows = []
    for (scheme, topology_id, scaling_axis), group in per_run_state.groupby(
        ["registry_scheme", "registry_topology_id", "scaling_axis"], sort=False
    ):
        for scaling_value, point_rows in group.groupby("scaling_value", sort=True):
            run_ids = sorted(point_rows["run_id"].astype(str).unique().tolist())
            output_rows.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "scheme": scheme,
                    "topology_id": topology_id,
                    "scaling_axis": scaling_axis,
                    "scaling_value": round(float(scaling_value), 6),
                    "budget": int(point_rows["budget"].max()),
                    "run_count": len(run_ids),
                    "query_count": int(sum(int(query_count_by_run.get(run_id, 0)) for run_id in run_ids)),
                    "mean_total_exported_summaries": round(
                        point_rows["total_exported_summaries"].mean(), 6
                    ),
                    "mean_total_exported_summary_bytes": round(
                        point_rows["total_exported_summary_bytes"].mean(), 6
                    ),
                    "mean_total_summary_updates_sent": round(
                        point_rows["total_summary_updates_sent"].mean(), 6
                    ),
                    "mean_objects_in_domain": round(point_rows["mean_objects_in_domain"].mean(), 6),
                    "domains_total": int(point_rows["domains_total"].max()),
                    "mean_success_at_1": round(point_rows["mean_success_at_1"].mean(), 6),
                    "mean_latency_ms": round(point_rows["mean_latency_ms"].mean(), 6),
                    "mean_discovery_bytes": round(point_rows["mean_discovery_bytes"].mean(), 6),
                    "source_run_ids": "|".join(run_ids),
                }
            )

    aggregate_path = aggregate_output_path(experiment, "state_scaling_summary.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
