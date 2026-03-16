"""Build Figure 7 deadline-sensitive summary from canonical query logs."""

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
    "budget",
    "deadline_ms",
    "success_before_deadline_rate",
    "timeout_or_failure_rate",
    "mean_latency_ms",
    "mean_success_latency_ms",
    "median_success_latency_ms",
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

    selected_budget = int(experiment.get("default_budget") or 0)
    if selected_budget:
        frame = frame[frame["budget"] == selected_budget].copy()

    output_rows = []
    for (scheme, topology_id, budget), group in frame.groupby(
        ["registry_scheme", "registry_topology_id", "budget"], sort=False
    ):
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
                    "deadline_ms": deadline_ms,
                    "success_before_deadline_rate": round(success_before_deadline, 6),
                    "timeout_or_failure_rate": round(1.0 - success_before_deadline, 6),
                    "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                    "mean_success_latency_ms": round(mean_success_latency, 6),
                    "median_success_latency_ms": round(median_success_latency, 6),
                }
            )

    aggregate_path = repo_root() / "results" / "aggregate" / "deadline_summary.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
