"""Build Figure 5 failure breakdown from canonical query logs."""

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
    "query_count",
    "failure_type",
    "count",
    "rate",
    "source_run_ids",
]

FAILURE_ORDER = [
    "predicate_miss",
    "wrong_domain",
    "wrong_object",
    "no_reply",
    "fetch_timeout",
    "success",
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
    frame = log_frame(rows, "query_log.csv")
    if frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    if "success_at_1" in frame.columns:
        frame = frame.copy()
        frame["normalized_failure_type"] = frame["failure_type"].fillna("")
        frame.loc[frame["success_at_1"] == 1, "normalized_failure_type"] = "success"
        frame.loc[frame["normalized_failure_type"] == "none", "normalized_failure_type"] = "success"
    else:
        frame["normalized_failure_type"] = frame["failure_type"].fillna("unknown")

    active_sweep_field = sweep_field(experiment)
    output_rows = []
    for keys, group in frame.groupby(
        ["registry_scheme", "registry_topology_id", active_sweep_field], sort=False
    ):
        scheme, topology_id, sweep_value = keys
        run_ids = sorted(group["run_id"].unique().tolist())
        budget = int(sweep_value) if active_sweep_field == "budget" else int(group["budget"].max())
        manifest_size = int(sweep_value) if active_sweep_field == "manifest_size" else int(group["manifest_size"].max())
        counts = group["normalized_failure_type"].value_counts()
        total = len(group)
        for failure_type in FAILURE_ORDER:
            count = int(counts.get(failure_type, 0))
            output_rows.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "scheme": scheme,
                    "topology_id": topology_id,
                    "budget": budget,
                    "manifest_size": manifest_size,
                    "query_count": int(total),
                    "failure_type": failure_type,
                    "count": count,
                    "rate": round(float(count) / float(total), 6),
                    "source_run_ids": "|".join(run_ids),
                }
            )

    aggregate_path = aggregate_output_path(experiment, "failure_breakdown.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
