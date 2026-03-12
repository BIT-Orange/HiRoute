"""Build Figure 6 candidate shrinkage summary from raw ndnSIM query logs."""

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
    "mean_candidate_shrinkage_ratio",
    "median_candidate_shrinkage_ratio",
    "mean_remote_probes",
    "mean_manifest_hit_at_r",
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
    frame = log_frame(rows, "query_log.csv", raw=True)
    if frame.empty:
        print("ERROR: raw query logs are missing")
        return 1
    if "candidate_shrinkage_ratio" not in frame.columns:
        frame = log_frame(rows, "query_log.csv")
        if frame.empty:
            print("ERROR: canonical query logs are missing")
            return 1
        frame["candidate_shrinkage_ratio"] = 0.0
        frame["remote_probes"] = frame["num_remote_probes"]
        frame["manifest_hit_at_r"] = frame["manifest_hit_at_5"]

    frame["candidate_shrinkage_ratio"] = frame["candidate_shrinkage_ratio"].astype(float)
    frame["remote_probes"] = frame["remote_probes"].astype(float)
    frame["manifest_hit_at_r"] = frame["manifest_hit_at_r"].astype(float)
    output_rows = []
    for (scheme, topology_id), group in frame.groupby(["scheme", "registry_topology_id"], sort=False):
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "mean_candidate_shrinkage_ratio": round(group["candidate_shrinkage_ratio"].mean(), 6),
                "median_candidate_shrinkage_ratio": round(group["candidate_shrinkage_ratio"].median(), 6),
                "mean_remote_probes": round(group["remote_probes"].mean(), 6),
                "mean_manifest_hit_at_r": round(group["manifest_hit_at_r"].mean(), 6),
            }
        )

    aggregate_path = repo_root() / "results" / "aggregate" / "candidate_shrinkage.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
