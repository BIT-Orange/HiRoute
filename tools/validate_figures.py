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
    expected_budgets = {int(value) for value in experiment.get("budgets", [])}
    expected_manifest_sizes = {int(value) for value in experiment.get("manifest_sizes", [])}
    if not expected_budgets:
        expected_budgets = {int(experiment.get("default_budget") or 0)}
    if not expected_manifest_sizes:
        default_manifest_size = int(experiment.get("default_manifest_size") or 0)
        expected_manifest_sizes = {default_manifest_size} if default_manifest_size else set()
    frontier_schemes = {str(value) for value in experiment.get("frontier_schemes", [])}
    reference_schemes = {str(value) for value in experiment.get("reference_schemes", [])}
    default_budget = int(experiment.get("default_budget") or 0)
    default_manifest_size = int(experiment.get("default_manifest_size") or 0)
    experiment_id = str(experiment.get("experiment_id", ""))
    is_v3 = str(experiment.get("dataset_id", "")).endswith("_v3") or experiment_id.endswith("_v3") or experiment_id.endswith("_v3_compact")
    is_compact = experiment_id.endswith("_v3_compact")

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
        row_budget = int(row.get("budget") or 0)
        row_manifest_size = int(row.get("manifest_size") or 0)
        if frontier_schemes or reference_schemes:
            if row["scheme"] in reference_schemes and row_budget != default_budget:
                continue
            if row["scheme"] in frontier_schemes and row_budget not in expected_budgets:
                continue
        elif expected_manifest_sizes:
            if row_manifest_size not in expected_manifest_sizes:
                continue
        elif expected_budgets and row_budget not in expected_budgets:
            continue
        promoted_rows.append(row)
    if not promoted_rows:
        print("ERROR: no promoted runs found for experiment")
        return 1

    min_test_queries = int(
        experiment.get("promotion_rule", {}).get("min_test_queries_per_scheme_budget_tier", 0) or 0
    )
    if min_test_queries > 0:
        run_index_path = repo_root() / "runs" / "registry" / "runs.csv"
        run_dir_by_id = {
            row["run_id"]: row.get("run_dir", "")
            for row in read_csv_rows(run_index_path)
        } if run_index_path.exists() else {}
        query_counts = Counter()
        for row in promoted_rows:
            run_dir = row.get("run_dir") or run_dir_by_id.get(row["run_id"], "")
            if not run_dir:
                continue
            query_log_path = repo_root() / run_dir / "query_log.csv"
            if not query_log_path.exists():
                continue
            query_count = len(read_csv_rows(query_log_path))
            sweep_value = int(row.get("manifest_size") or 0) if expected_manifest_sizes else int(row.get("budget") or 0)
            query_counts[(row["scheme"], row["topology_id"], sweep_value)] += query_count

        missing = []
        target_topologies = expected_topologies or {row["topology_id"] for row in promoted_rows}
        for topology_id in target_topologies:
            for scheme in experiment.get("schemes", []):
                if expected_manifest_sizes:
                    required_values = (
                        {default_manifest_size}
                        if scheme in reference_schemes and default_manifest_size
                        else sorted(expected_manifest_sizes)
                    )
                    label = "manifest"
                else:
                    required_values = (
                        {default_budget}
                        if scheme in reference_schemes and default_budget
                        else sorted(expected_budgets)
                    )
                    label = "budget"
                for value in sorted(required_values):
                    if query_counts.get((scheme, topology_id, value), 0) < min_test_queries:
                        missing.append(f"{scheme}@{topology_id}@{label}{value}")
        if missing:
            print("ERROR: promoted runs do not satisfy minimum test query counts: " + ", ".join(missing))
            return 1
    else:
        min_runs = int(experiment.get("promotion_rule", {}).get("min_runs_per_scheme", 1))
        if experiment.get("comparison_topologies"):
            schemes = Counter(
                (
                    row["scheme"],
                    row["topology_id"],
                    int(row.get("manifest_size") or 0) if expected_manifest_sizes else int(row.get("budget") or 0),
                )
                for row in promoted_rows
            )
            missing = [
                f"{scheme}@{topology_id}@{'manifest' if expected_manifest_sizes else 'budget'}{budget}"
                for topology_id in expected_topologies
                for scheme in experiment.get("schemes", [])
                for budget in (
                    [default_manifest_size]
                    if expected_manifest_sizes and scheme in reference_schemes and default_manifest_size
                    else [default_budget]
                    if (not expected_manifest_sizes and scheme in reference_schemes and default_budget)
                    else sorted(expected_manifest_sizes if expected_manifest_sizes else expected_budgets)
                )
                if schemes.get((scheme, topology_id, budget), 0) < min_runs
            ]
        else:
            schemes = Counter(
                (
                    row["scheme"],
                    int(row.get("manifest_size") or 0) if expected_manifest_sizes else int(row.get("budget") or 0),
                )
                for row in promoted_rows
            )
            missing = [
                f"{scheme}@{'manifest' if expected_manifest_sizes else 'budget'}{budget}"
                for scheme in experiment.get("schemes", [])
                for budget in (
                    [default_manifest_size]
                    if expected_manifest_sizes and scheme in reference_schemes and default_manifest_size
                    else [default_budget]
                    if (not expected_manifest_sizes and scheme in reference_schemes and default_budget)
                    else sorted(expected_manifest_sizes if expected_manifest_sizes else expected_budgets)
                )
                if schemes.get((scheme, budget), 0) < min_runs
            ]
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
        aggregate_path_text = str(args.aggregate)
        if is_v3 and "/v3/" not in aggregate_path_text:
            print("ERROR: smartcity_v3 main figures must use v3 aggregate paths")
            return 1
        if is_compact and "/v3/compact/" not in aggregate_path_text:
            print("ERROR: compact v3 figures must use v3/compact aggregate paths")
            return 1
        if is_compact and ("/v3/local/" in aggregate_path_text or "/v3/local_lite/" in aggregate_path_text):
            print("ERROR: compact v3 figures must not read local/local_lite aggregates")
            return 1
        if not is_v3 and "/v3/" in aggregate_path_text:
            print("ERROR: non-v3 experiments must not read v3 aggregates")
            return 1
        aggregate_rows = read_csv_rows(args.aggregate)
        aggregate_schemes = {row.get("scheme", "") for row in aggregate_rows}
        if args.aggregate.name in {
            "main_success_overhead.csv",
            "failure_breakdown.csv",
            "candidate_shrinkage.csv",
            "deadline_summary.csv",
            "ablation_summary.csv",
        } and "exact" in aggregate_schemes:
            print("ERROR: appendix exact baseline must not appear in main-paper aggregates")
            return 1
        if is_v3 and "sanity_appendix_v3" in {row.get("workload_tier", "") for row in aggregate_rows}:
            print("ERROR: smartcity_v3 main figures must not include sanity_appendix_v3 data")
            return 1

        workload_tiers = set(experiment.get("query_filters", {}).get("workload_tiers", []))
        if args.aggregate.name in {"main_success_overhead.csv", "candidate_shrinkage.csv", "deadline_summary.csv"}:
            expected_tier = {"routing_hard_v3"} if is_v3 else {"routing_hard"}
            if workload_tiers != expected_tier:
                print("ERROR: routing aggregates must come from routing_hard workload")
                return 1
        if args.aggregate.name in {"failure_breakdown.csv", "ablation_summary.csv"}:
            expected_tier = {"object_hard_v3"} if is_v3 else {"object_hard"}
            if workload_tiers != expected_tier:
                print("ERROR: failure and ablation aggregates must come from object_hard workload")
                return 1

        if args.aggregate.name == "main_success_overhead.csv":
            sweep_key = "manifest_size" if expected_manifest_sizes else "budget"
            budgets_by_scheme: dict[str, set[int]] = {}
            for row in aggregate_rows:
                budgets_by_scheme.setdefault(row.get("scheme", ""), set()).add(int(row.get(sweep_key) or 0))
            expected_points = expected_manifest_sizes if expected_manifest_sizes else expected_budgets
            for scheme in {"flat_iroute", "hiroute", "inf_tag_forwarding"} & set(experiment.get("schemes", [])):
                if len(budgets_by_scheme.get(scheme, set())) < len(expected_points):
                    print(f"ERROR: routing frontier is missing budget points for {scheme}")
                    return 1
            if {"flat_iroute", "flood"}.issubset(aggregate_schemes):
                flat_rows = {
                    int(row.get(sweep_key) or 0): row
                    for row in aggregate_rows
                    if row.get("scheme") == "flat_iroute"
                }
                flood_rows = {
                    int(row.get(sweep_key) or 0): row
                    for row in aggregate_rows
                    if row.get("scheme") == "flood"
                }
                common = sorted(set(flat_rows) & set(flood_rows))
                if common:
                    identical = True
                    for budget in common:
                        left = flat_rows[budget]
                        right = flood_rows[budget]
                        for field in [
                            "mean_success_at_1",
                            "mean_num_remote_probes",
                            "mean_discovery_bytes",
                            "mean_latency_ms",
                        ]:
                            if left.get(field) != right.get(field):
                                identical = False
                                break
                        if not identical:
                            break
                    if identical:
                        print("ERROR: flat_iroute and flood remain degenerate on all routing headline metrics")
                        return 1

        if experiment["experiment_id"] in {"exp_main_v1", "exp_routing_main_v3", "exp_routing_main_v3_compact"} and args.aggregate.name == "candidate_shrinkage.csv":
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
        if experiment["experiment_id"] in {"exp_scaling_v1", "exp_scaling_v3", "exp_scaling_v3_compact"} and args.aggregate.name == "state_scaling_summary.csv":
            axes = {row.get("scaling_axis", "") for row in aggregate_rows}
            if axes != {"objects_per_domain", "domain_count"}:
                print("ERROR: state scaling aggregate must contain both object and domain sweeps")
                return 1
            aggregate_topologies = {row.get("topology_id", "") for row in aggregate_rows}
            if expected_topologies and aggregate_topologies != expected_topologies:
                print("ERROR: state scaling aggregate does not cover every comparison topology")
                return 1
        if experiment["experiment_id"] in {"exp_robustness_v3_compact"} and args.aggregate.name == "robustness_timeseries.csv":
            required_fields = {
                "experiment_id",
                "scenario_variant",
                "scheme",
                "topology_id",
                "time_bin_s",
                "query_count",
                "success_at_1_rate",
                "mean_remote_probes",
                "mean_discovery_bytes",
            }
            if not aggregate_rows:
                print("ERROR: robustness timeseries aggregate is empty")
                return 1
            missing_fields = required_fields - set(aggregate_rows[0].keys())
            if missing_fields:
                print("ERROR: robustness timeseries aggregate misses fields: " + ", ".join(sorted(missing_fields)))
                return 1
        if is_compact and experiment["experiment_id"] in {
            "exp_routing_main_v3_compact",
            "exp_object_main_v3_compact",
            "exp_ablation_v3_compact",
        }:
            query_filters = experiment.get("query_filters", {}) or {}
            for field in ["max_ingress_nodes", "max_queries_per_ingress", "max_total_queries"]:
                if int(query_filters.get(field, 0) or 0) != 0:
                    print(f"ERROR: compact experiment must not slice queries via {field}")
                    return 1
            params = experiment.get("runner", {}).get("params", {})
            if int(params.get("queryLimitPerIngress", 0) or 0) != 0:
                print("ERROR: compact routing/object/ablation must use queryLimitPerIngress=0")
                return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
