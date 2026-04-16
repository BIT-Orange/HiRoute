"""Build Figure 7 deadline-sensitive summary from canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import aggregate_output_path, load_experiment, log_frame, require_rows, sweep_field
from tools.workflow_support import write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "budget",
    "manifest_size",
    "run_count",
    "query_count",
    "deadline_ms",
    "success_before_deadline_rate",
    "timeout_or_failure_rate",
    "mean_latency_ms",
    "mean_success_latency_ms",
    "median_success_latency_ms",
    "source_run_ids",
]
DEFAULT_DEADLINES_MS = [50, 100, 200, 500]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    rows = require_rows(experiment, args.registry_source)
    frame = log_frame(rows, "query_log.csv")
    if frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    active_sweep_field = sweep_field(experiment)
    selected_budget = int(experiment.get("default_budget") or 0)
    selected_manifest_size = int(experiment.get("default_manifest_size") or 0)
    if active_sweep_field == "budget" and selected_budget:
        frame = frame[frame["budget"] == selected_budget].copy()
    if active_sweep_field == "manifest_size" and selected_manifest_size:
        frame = frame[frame["manifest_size"] == selected_manifest_size].copy()

    output_rows = []
    for (scheme, topology_id, budget), group in frame.groupby(
        ["registry_scheme", "registry_topology_id", "budget"], sort=False
    ):
        run_ids = sorted(group["run_id"].unique().tolist())
        success_rows = group[group["success_at_1"] == 1]
        mean_success_latency = float(success_rows["latency_ms"].mean()) if not success_rows.empty else float("nan")
        median_success_latency = float(success_rows["latency_ms"].median()) if not success_rows.empty else float("nan")
        for deadline_ms in DEFAULT_DEADLINES_MS:
            on_time = (group["success_at_1"] == 1) & (group["latency_ms"] <= deadline_ms)
            success_before_deadline = float(on_time.mean())
            output_rows.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "scheme": scheme,
                    "topology_id": topology_id,
                    "budget": int(budget),
                    "manifest_size": int(group["manifest_size"].max()),
                    "run_count": len(run_ids),
                    "query_count": int(len(group)),
                    "deadline_ms": deadline_ms,
                    "success_before_deadline_rate": round(success_before_deadline, 6),
                    "timeout_or_failure_rate": round(1.0 - success_before_deadline, 6),
                    "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                    "mean_success_latency_ms": round(mean_success_latency, 6),
                    "median_success_latency_ms": round(median_success_latency, 6),
                    "source_run_ids": "|".join(run_ids),
                }
            )

    aggregate_path = aggregate_output_path(experiment, "deadline_summary.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
