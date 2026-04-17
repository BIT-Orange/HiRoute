"""Build Figure 5 manifest-sweep summary from canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import (
    aggregate_output_path,
    bootstrap_mean_ci,
    load_experiment,
    log_frame,
    require_rows,
)
from tools.workflow_support import write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "budget",
    "manifest_size",
    "run_count",
    "query_count",
    "mean_success_at_1",
    "ci_success_at_1",
    "first_fetch_relevant_rate",
    "ci_first_fetch_relevant_rate",
    "manifest_rescue_rate",
    "ci_manifest_rescue_rate",
    "mean_manifest_fetch_index_success_only",
    "wrong_object_rate",
    "ci_wrong_object_rate",
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
    frame = log_frame(rows, "query_log.csv")
    if frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    bootstrap_replicates = int(experiment.get("statistics", {}).get("bootstrap_replicates", 1000))

    frame = frame.copy()
    frame["success_at_1"] = frame["success_at_1"].astype(float)
    frame["first_fetch_relevant"] = frame.get("first_fetch_relevant", 0)
    frame["first_fetch_relevant"] = frame["first_fetch_relevant"].replace("", 0).astype(float)
    frame["manifest_fetch_index"] = frame.get("manifest_fetch_index", 0)
    frame["manifest_fetch_index"] = frame["manifest_fetch_index"].replace("", 0).astype(float)
    frame["wrong_object_indicator"] = (frame["failure_type"] == "wrong_object").astype(float)
    frame["manifest_rescue"] = ((frame["success_at_1"] == 1) & (frame["manifest_fetch_index"] > 0)).astype(float)

    output_rows = []
    for keys, group in frame.groupby(
        ["registry_scheme", "registry_topology_id", "manifest_size"], sort=False
    ):
        scheme, topology_id, manifest_size = keys
        run_ids = sorted(group["run_id"].unique().tolist())
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "budget": int(group["budget"].max()),
                "manifest_size": int(manifest_size),
                "run_count": len(run_ids),
                "query_count": int(len(group)),
                "mean_success_at_1": round(group["success_at_1"].mean(), 6),
                "ci_success_at_1": round(
                    bootstrap_mean_ci(group["success_at_1"], bootstrap_replicates, seed=10), 6
                ),
                "first_fetch_relevant_rate": round(group["first_fetch_relevant"].mean(), 6),
                "ci_first_fetch_relevant_rate": round(
                    bootstrap_mean_ci(group["first_fetch_relevant"], bootstrap_replicates, seed=13), 6
                ),
                "manifest_rescue_rate": round(group["manifest_rescue"].mean(), 6),
                "ci_manifest_rescue_rate": round(
                    bootstrap_mean_ci(group["manifest_rescue"], bootstrap_replicates, seed=14), 6
                ),
                "mean_manifest_fetch_index_success_only": round(
                    group.loc[group["success_at_1"] == 1, "manifest_fetch_index"].mean()
                    if (group["success_at_1"] == 1).any()
                    else 0.0,
                    6,
                ),
                "wrong_object_rate": round(group["wrong_object_indicator"].mean(), 6),
                "ci_wrong_object_rate": round(
                    bootstrap_mean_ci(group["wrong_object_indicator"], bootstrap_replicates, seed=11), 6
                ),
                "source_run_ids": "|".join(run_ids),
            }
        )

    aggregate_path = aggregate_output_path(experiment, "object_main_manifest_sweep.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
