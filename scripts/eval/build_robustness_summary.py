"""Build Figure 9 robustness summary from staleness/failure experiments."""

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
    "source_experiment_id",
    "scenario",
    "scenario_variant",
    "scheme",
    "topology_id",
    "mean_success_at_1",
    "mean_latency_ms",
    "mean_discovery_bytes",
    "event_count",
]

ROBUSTNESS_EXPERIMENTS = {
    "exp_staleness_v1": ["exp_staleness_v1", "exp_failures_v1"],
    "exp_failures_v1": ["exp_staleness_v1", "exp_failures_v1"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    experiment_ids = ROBUSTNESS_EXPERIMENTS.get(experiment["experiment_id"], [experiment["experiment_id"]])
    rows = []
    for experiment_id in experiment_ids:
        companion_path = repo_root() / "configs" / "experiments" / f"{experiment_id}.yaml"
        companion = load_experiment(companion_path)
        rows.extend(require_rows(companion, args.registry_source))
    query_frame = log_frame(rows, "query_log.csv")
    failure_frame = log_frame(rows, "failure_event_log.csv")
    if query_frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    query_frame["discovery_bytes_total"] = query_frame["discovery_tx_bytes"] + query_frame["discovery_rx_bytes"]
    if failure_frame.empty:
        failure_counts = {}
    else:
        failure_counts = failure_frame.groupby("run_id").size().to_dict()

    output_rows = []
    for keys, group in query_frame.groupby(
        ["scenario", "scenario_variant", "registry_scheme", "registry_topology_id"], sort=False
    ):
        scenario, scenario_variant, scheme, topology_id = keys
        event_count = sum(failure_counts.get(run_id, 0) for run_id in group["run_id"].unique())
        source_experiment_ids = sorted(group["experiment_id"].unique().tolist())
        output_rows.append(
            {
                "experiment_id": "exp_robustness_v1",
                "source_experiment_id": "|".join(source_experiment_ids),
                "scenario": scenario,
                "scenario_variant": scenario_variant,
                "scheme": scheme,
                "topology_id": topology_id,
                "mean_success_at_1": round(group["success_at_1"].mean(), 6),
                "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                "mean_discovery_bytes": round(group["discovery_bytes_total"].mean(), 6),
                "event_count": int(event_count),
            }
        )

    aggregate_path = repo_root() / "results" / "aggregate" / "robustness_summary.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
