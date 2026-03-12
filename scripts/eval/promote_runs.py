"""Promote experiment runs that satisfy the formal registry policy."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import ensure_csv, isoformat_z, load_json_yaml, read_csv, repo_root


FIELDS = [
    "run_id",
    "experiment_id",
    "scheme",
    "dataset_id",
    "topology_id",
    "seed",
    "git_commit",
    "promotion_reason",
    "promoted_at",
]

REQUIRED_ARTIFACTS = [
    "manifest.yaml",
    "stdout.log",
    "stderr.log",
    "query_log.csv",
    "probe_log.csv",
    "search_trace.csv",
    "state_log.csv",
    "failure_event_log.csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(ROOT / args.experiment)
    runs_path = repo_root() / "runs" / "registry" / "runs.csv"
    promoted_path = repo_root() / "runs" / "registry" / "promoted_runs.csv"
    ensure_csv(promoted_path, FIELDS)

    run_rows = [row for row in read_csv(runs_path) if row["experiment_id"] == experiment["experiment_id"]]
    if not run_rows:
        print("ERROR: no completed runs found for experiment")
        return 1

    scheme_counts = Counter(row["scheme"] for row in run_rows)
    min_runs = int(experiment["promotion_rule"]["min_runs_per_scheme"])
    missing = [scheme for scheme in experiment["schemes"] if scheme_counts.get(scheme, 0) < min_runs]
    if missing:
        print(f"ERROR: missing enough completed runs for schemes: {', '.join(missing)}")
        return 1

    dataset_ids = {row["dataset_id"] for row in run_rows}
    topology_ids = {row["topology_id"] for row in run_rows}
    if len(dataset_ids) != 1 or len(topology_ids) != 1:
        print("ERROR: completed runs mix dataset or topology versions")
        return 1

    promoted_rows = []
    for row in run_rows:
        run_dir = repo_root() / row["run_dir"]
        missing_artifacts = [artifact for artifact in REQUIRED_ARTIFACTS if not (run_dir / artifact).exists()]
        if missing_artifacts:
            print(f"ERROR: {row['run_id']} is missing artifacts: {', '.join(missing_artifacts)}")
            return 1
        promoted_rows.append(
            {
                "run_id": row["run_id"],
                "experiment_id": row["experiment_id"],
                "scheme": row["scheme"],
                "dataset_id": row["dataset_id"],
                "topology_id": row["topology_id"],
                "seed": row["seed"],
                "git_commit": row["git_commit"],
                "promotion_reason": "meets min run count and artifact completeness",
                "promoted_at": isoformat_z(),
            }
        )

    existing = [row for row in read_csv(promoted_path) if row["experiment_id"] != experiment["experiment_id"]]
    with promoted_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in existing + promoted_rows:
            writer.writerow(row)

    print(experiment["experiment_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
