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


def expected_topology_ids(experiment: dict[str, object]) -> set[str]:
    comparison_topologies = experiment.get("comparison_topologies", [])
    if comparison_topologies:
        return {str(topology_id) for topology_id in comparison_topologies}
    topology_id = experiment.get("topology_id")
    return {str(topology_id)} if topology_id else set()


def expected_scenarios(experiment: dict[str, object]) -> set[str]:
    scenarios = set()
    scenario = experiment.get("scenario")
    if scenario:
        scenarios.add(str(scenario))
    runner = experiment.get("runner", {})
    if isinstance(runner, dict):
        for scenario_name in runner.get("scenario_variants", {}).values():
            scenarios.add(str(scenario_name))
    return scenarios


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

    expected_dataset_id = str(experiment.get("dataset_id", ""))
    expected_topologies = expected_topology_ids(experiment)
    expected_seeds = {str(seed) for seed in experiment.get("seeds", [])}
    allowed_scenarios = expected_scenarios(experiment)

    run_rows = []
    for row in read_csv(runs_path):
        if row["experiment_id"] != experiment["experiment_id"]:
            continue
        if expected_dataset_id and row["dataset_id"] != expected_dataset_id:
            continue
        if expected_topologies and row["topology_id"] not in expected_topologies:
            continue
        if expected_seeds and row["seed"] not in expected_seeds:
            continue
        manifest_path = repo_root() / row["run_dir"] / "manifest.yaml"
        if allowed_scenarios and manifest_path.exists():
            try:
                manifest = load_json_yaml(manifest_path)
            except Exception:
                continue
            if manifest.get("scenario", "") not in allowed_scenarios:
                continue
            row = dict(row)
            row["_scenario"] = manifest.get("scenario", "")
        elif manifest_path.exists():
            row = dict(row)
            try:
                row["_scenario"] = load_json_yaml(manifest_path).get("scenario", "")
            except Exception:
                continue
        else:
            row = dict(row)
            row["_scenario"] = ""
        run_rows.append(row)
    if not run_rows:
        print("ERROR: no completed runs found for experiment")
        return 1

    latest_by_key: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in run_rows:
        key = (row["scheme"], row["seed"], row["topology_id"], row.get("_scenario", ""))
        existing = latest_by_key.get(key)
        if existing is None or row["start_time"] > existing["start_time"]:
            latest_by_key[key] = row
    run_rows = list(latest_by_key.values())

    min_runs = int(experiment["promotion_rule"]["min_runs_per_scheme"])
    if experiment.get("comparison_topologies"):
        scheme_counts = Counter((row["scheme"], row["topology_id"]) for row in run_rows)
        missing = [
            f"{scheme}@{topology_id}"
            for topology_id in expected_topologies
            for scheme in experiment["schemes"]
            if scheme_counts.get((scheme, topology_id), 0) < min_runs
        ]
    else:
        scheme_counts = Counter(row["scheme"] for row in run_rows)
        missing = [scheme for scheme in experiment["schemes"] if scheme_counts.get(scheme, 0) < min_runs]
    if missing:
        print(f"ERROR: missing enough completed runs for schemes: {', '.join(missing)}")
        return 1

    dataset_ids = {row["dataset_id"] for row in run_rows}
    topology_ids = {row["topology_id"] for row in run_rows}
    if dataset_ids != {expected_dataset_id}:
        print("ERROR: completed runs mix dataset versions")
        return 1
    if expected_topologies and topology_ids != expected_topologies:
        print("ERROR: completed runs do not match configured topology set")
        return 1

    promoted_rows = []
    for row in run_rows:
        run_dir = repo_root() / row["run_dir"]
        missing_artifacts = [artifact for artifact in REQUIRED_ARTIFACTS if not (run_dir / artifact).exists()]
        if missing_artifacts:
            print(f"ERROR: {row['run_id']} is missing artifacts: {', '.join(missing_artifacts)}")
            return 1
        if experiment.get("promotion_rule", {}).get("require_clean_git"):
            manifest = load_json_yaml(run_dir / "manifest.yaml")
            if manifest.get("code", {}).get("git_dirty", True):
                print(f"ERROR: {row['run_id']} was produced from a dirty git tree")
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
