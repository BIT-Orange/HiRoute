"""Validate figure inputs against promoted run policy."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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

    expected_dataset_id = str(experiment.get("dataset_id", ""))
    expected_topologies = set(experiment.get("comparison_topologies", []))
    if not expected_topologies and experiment.get("topology_id"):
        expected_topologies = {str(experiment["topology_id"])}
    expected_seeds = {str(seed) for seed in experiment.get("seeds", [])}

    promoted_rows = []
    for row in read_csv_rows(promoted_path):
        if row["experiment_id"] != experiment["experiment_id"]:
            continue
        if expected_dataset_id and row["dataset_id"] != expected_dataset_id:
            continue
        if expected_topologies and row["topology_id"] not in expected_topologies:
            continue
        if expected_seeds and row["seed"] not in expected_seeds:
            continue
        promoted_rows.append(row)
    if not promoted_rows:
        print("ERROR: no promoted runs found for experiment")
        return 1

    min_runs = int(experiment.get("promotion_rule", {}).get("min_runs_per_scheme", 1))
    if experiment.get("comparison_topologies"):
        schemes = Counter((row["scheme"], row["topology_id"]) for row in promoted_rows)
        missing = [
            f"{scheme}@{topology_id}"
            for topology_id in expected_topologies
            for scheme in experiment.get("schemes", [])
            if schemes.get((scheme, topology_id), 0) < min_runs
        ]
    else:
        schemes = Counter(row["scheme"] for row in promoted_rows)
        missing = [scheme for scheme in experiment.get("schemes", []) if schemes.get(scheme, 0) < min_runs]
    if missing:
        print(f"ERROR: promoted runs do not satisfy minimum counts for schemes: {', '.join(missing)}")
        return 1

    dataset_ids = {row["dataset_id"] for row in promoted_rows}
    topology_ids = {row["topology_id"] for row in promoted_rows}
    if dataset_ids != {expected_dataset_id}:
        print("ERROR: promoted runs mix dataset versions")
        return 1
    if expected_topologies:
        if topology_ids != expected_topologies:
            print("ERROR: promoted runs do not cover every comparison topology")
            return 1
    elif len(topology_ids) != 1:
        print("ERROR: promoted runs mix topology versions")
        return 1

    if args.aggregate and not args.aggregate.exists():
        print(f"ERROR: aggregate CSV is missing: {args.aggregate}")
        return 1
    if args.figure_note and not args.figure_note.exists():
        print(f"ERROR: figure note is missing: {args.figure_note}")
        return 1

    if args.aggregate and args.aggregate.exists():
        aggregate_rows = read_csv_rows(args.aggregate)
        if experiment["experiment_id"] == "exp_main_v1" and args.aggregate.name == "candidate_shrinkage.csv":
            required_stages = {
                "all_domains",
                "predicate_filtered_domains",
                "level0_cells",
                "level1_cells",
                "refined_cells",
                "probed_cells",
            }
            seen_stages = {row.get("stage", "") for row in aggregate_rows}
            missing_stages = sorted(required_stages - seen_stages)
            if missing_stages:
                print("ERROR: candidate shrinkage aggregate misses required stages: " +
                      ", ".join(missing_stages))
                return 1
        if experiment["experiment_id"] == "exp_scaling_v1" and args.aggregate.name == "state_scaling_summary.csv":
            axes = {row.get("scaling_axis", "") for row in aggregate_rows}
            if axes != {"objects_per_domain", "domain_count"}:
                print("ERROR: state scaling aggregate must contain both object and domain sweeps")
                return 1
            aggregate_topologies = {row.get("topology_id", "") for row in aggregate_rows}
            if expected_topologies and aggregate_topologies != expected_topologies:
                print("ERROR: state scaling aggregate does not cover every comparison topology")
                return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
