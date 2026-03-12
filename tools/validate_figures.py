"""Validate figure inputs against promoted run policy."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from tools.workflow_support import load_json_yaml, repo_root


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--aggregate", type=Path)
    parser.add_argument("--figure-note", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(args.experiment)
    promoted_path = repo_root() / "runs" / "registry" / "promoted_runs.csv"
    if not promoted_path.exists():
        print("ERROR: promoted_runs.csv is missing")
        return 1

    promoted_rows = [
        row for row in read_csv_rows(promoted_path) if row["experiment_id"] == experiment["experiment_id"]
    ]
    if not promoted_rows:
        print("ERROR: no promoted runs found for experiment")
        return 1

    schemes = Counter(row["scheme"] for row in promoted_rows)
    min_runs = int(experiment.get("promotion_rule", {}).get("min_runs_per_scheme", 1))
    missing = [scheme for scheme in experiment.get("schemes", []) if schemes.get(scheme, 0) < min_runs]
    if missing:
        print(f"ERROR: promoted runs do not satisfy minimum counts for schemes: {', '.join(missing)}")
        return 1

    dataset_ids = {row["dataset_id"] for row in promoted_rows}
    topology_ids = {row["topology_id"] for row in promoted_rows}
    if len(dataset_ids) != 1:
        print("ERROR: promoted runs mix dataset versions")
        return 1
    if len(topology_ids) != 1:
        print("ERROR: promoted runs mix topology versions")
        return 1

    if args.aggregate and not args.aggregate.exists():
        print(f"ERROR: aggregate CSV is missing: {args.aggregate}")
        return 1
    if args.figure_note and not args.figure_note.exists():
        print(f"ERROR: figure note is missing: {args.figure_note}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
