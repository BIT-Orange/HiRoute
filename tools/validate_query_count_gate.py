"""Validate completed query-log counts against an experiment promotion threshold."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import (
    expected_sweep_values,
    expected_topology_ids,
    load_experiment,
    read_run_ids_file,
    registry_rows,
    run_dir,
)
from tools.workflow_support import load_json_yaml, read_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="runs")
    parser.add_argument("--run-ids-file", type=Path)
    parser.add_argument(
        "--no-require-variants",
        action="store_true",
        help="do not require each configured scenario variant to satisfy the count gate independently",
    )
    return parser.parse_args()


def _scenario_variant(row: dict[str, str]) -> str:
    manifest_path = run_dir(row) / "manifest.yaml"
    if not manifest_path.exists():
        return ""
    try:
        manifest = load_json_yaml(manifest_path)
    except Exception:
        return ""
    return str(manifest.get("scenario_variant", "") or "")


def _query_count(row: dict[str, str]) -> int:
    query_log_path = run_dir(row) / "query_log.csv"
    if not query_log_path.exists():
        return 0
    return len(read_csv(query_log_path))


def _required_values(experiment: dict, scheme: str, sweep_values: list[int]) -> list[int]:
    reference_schemes = {str(value) for value in experiment.get("reference_schemes", [])}
    if scheme not in reference_schemes:
        return sweep_values
    if experiment.get("manifest_sizes"):
        default_manifest = int(experiment.get("default_manifest_size") or 0)
        return [default_manifest] if default_manifest else sweep_values
    default_budget = int(experiment.get("default_budget") or 0)
    return [default_budget] if default_budget else sweep_values


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    run_ids = read_run_ids_file(args.run_ids_file)
    rows = registry_rows(experiment, args.registry_source, run_ids=run_ids)
    if not rows:
        print("ERROR: no matching registry rows found")
        return 1

    threshold = int(
        experiment.get("promotion_rule", {}).get("min_test_queries_per_scheme_budget_tier", 0) or 0
    )
    if threshold <= 0:
        print("OK query_count_gate=disabled")
        return 0

    uses_manifest_sweep = bool(experiment.get("manifest_sizes"))
    sweep_values = expected_sweep_values(experiment)
    topologies = expected_topology_ids(experiment) or {row["topology_id"] for row in rows}
    schemes = [str(value) for value in experiment.get("schemes", [])]
    variants = sorted((experiment.get("runner", {}) or {}).get("scenario_variants", {}).keys())
    if args.no_require_variants or not variants:
        variants = [""]

    counts: Counter[tuple[str, str, int, str]] = Counter()
    missing_logs: list[str] = []
    for row in rows:
        count = _query_count(row)
        if count <= 0:
            missing_logs.append(row["run_id"])
        sweep_value = int(row.get("manifest_size") or 0) if uses_manifest_sweep else int(row.get("budget") or 0)
        variant = _scenario_variant(row) if variants != [""] else ""
        counts[(row["scheme"], row["topology_id"], sweep_value, variant)] += count

    errors: list[str] = []
    for topology_id in sorted(topologies):
        for scheme in schemes:
            for sweep_value in _required_values(experiment, scheme, sweep_values):
                for variant in variants:
                    count = counts.get((scheme, topology_id, int(sweep_value), variant), 0)
                    if count < threshold:
                        label = "manifest" if uses_manifest_sweep else "budget"
                        variant_suffix = f"@{variant}" if variant else ""
                        errors.append(
                            f"{scheme}@{topology_id}@{label}{sweep_value}{variant_suffix}={count} < {threshold}"
                        )

    if missing_logs:
        errors.append("missing query_log.csv for " + ", ".join(sorted(missing_logs)))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        "OK "
        + f"experiment={experiment['experiment_id']} "
        + f"registry_source={args.registry_source} "
        + f"run_id_scope={'scoped' if run_ids else 'full'} "
        + f"threshold={threshold}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
