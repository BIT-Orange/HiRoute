"""Build Figure 8 scaling summary from state logs and canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import load_experiment, log_frame, require_rows
from tools.workflow_support import repo_root, write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "node_count",
    "controller_count",
    "ingress_count",
    "summary_count",
    "object_count",
    "mean_success_at_1",
    "mean_latency_ms",
    "mean_discovery_bytes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    rows = require_rows(experiment["experiment_id"], args.registry_source)
    query_frame = log_frame(rows, "query_log.csv")
    state_frame = log_frame(rows, "state_log.csv")
    if query_frame.empty or state_frame.empty:
        print("ERROR: missing canonical query logs or state logs")
        return 1

    query_frame["discovery_bytes_total"] = query_frame["discovery_tx_bytes"] + query_frame["discovery_rx_bytes"]
    per_run_query = (
        query_frame.groupby("run_id", as_index=False)
        .agg(
            mean_success_at_1=("success_at_1", "mean"),
            mean_latency_ms=("latency_ms", "mean"),
            mean_discovery_bytes=("discovery_bytes_total", "mean"),
        )
    )
    per_run_state = (
        state_frame.groupby(["run_id", "registry_scheme", "registry_topology_id"], as_index=False)
        .agg(
            node_count=("node_count", "max"),
            controller_count=("controller_count", "max"),
            ingress_count=("ingress_count", "max"),
            summary_count=("summary_count", "max"),
            object_count=("object_count", "max"),
        )
    )
    merged = per_run_state.merge(per_run_query, on="run_id", how="left")

    output_rows = []
    for (scheme, topology_id), group in merged.groupby(["registry_scheme", "registry_topology_id"], sort=False):
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "node_count": int(group["node_count"].mean()),
                "controller_count": int(group["controller_count"].mean()),
                "ingress_count": int(group["ingress_count"].mean()),
                "summary_count": int(group["summary_count"].mean()),
                "object_count": int(group["object_count"].mean()),
                "mean_success_at_1": round(group["mean_success_at_1"].mean(), 6),
                "mean_latency_ms": round(group["mean_latency_ms"].mean(), 6),
                "mean_discovery_bytes": round(group["mean_discovery_bytes"].mean(), 6),
            }
        )

    aggregate_path = repo_root() / "results" / "aggregate" / "state_scaling_summary.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
