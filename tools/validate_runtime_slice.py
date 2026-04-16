"""Validate runtime query/qrels/log consistency for a mainline experiment slice."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import load_experiment, read_run_ids_file, registry_rows, run_dir
from tools.workflow_support import load_json_yaml, read_csv, repo_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="runs")
    parser.add_argument("--run-ids-file", type=Path)
    return parser.parse_args()


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else repo_root() / path


def _runtime_input(manifest: dict, key: str, fallback: str, current_run_dir: Path) -> Path:
    inputs = manifest.get("inputs", {}) if isinstance(manifest, dict) else {}
    runtime_key = f"{key}_runtime"
    runtime_path = inputs.get(runtime_key)
    if runtime_path:
        return _resolve(str(runtime_path))
    return current_run_dir / fallback


def _domain_support(qrels_rows: list[dict[str, str]]) -> dict[str, set[str]]:
    support: dict[str, set[str]] = defaultdict(set)
    for row in qrels_rows:
        if row.get("is_relevant_domain", "1") == "1":
            support[row["query_id"]].add(row["domain_id"])
    return support


def _weak_object_counts(qrels_rows: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in qrels_rows:
        if int(row.get("relevance") or 0) == 1:
            counts[row["query_id"]] += 1
    return counts


def _workload_tiers(query_rows: list[dict[str, str]], experiment: dict) -> set[str]:
    tiers = {row.get("workload_tier", "") for row in query_rows if row.get("workload_tier", "")}
    if tiers:
        return tiers
    return {str(value) for value in (experiment.get("query_filters", {}) or {}).get("workload_tiers", [])}


def _active_domains(manifest: dict) -> set[str]:
    inputs = manifest.get("inputs", {}) if isinstance(manifest, dict) else {}
    topology_mapping = inputs.get("topology_mapping_csv")
    if not topology_mapping:
        return set()
    rows = read_csv(_resolve(str(topology_mapping)))
    return {row["domain_id"] for row in rows if row.get("domain_id")}


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    run_ids = read_run_ids_file(args.run_ids_file)
    rows = registry_rows(experiment, args.registry_source, run_ids=run_ids)
    if not rows:
        print("ERROR: no matching registry rows found")
        return 1

    errors: list[str] = []
    summaries: list[str] = []
    combined_routing_support: set[int] = set()
    combined_object_support: set[int] = set()
    combined_object_confusers: set[int] = set()

    for row in rows:
        current_run_dir = run_dir(row)
        manifest = load_json_yaml(current_run_dir / "manifest.yaml")
        query_rows = read_csv(_runtime_input(manifest, "queries_csv", "queries_master_runtime.csv", current_run_dir))
        qrels_domain_rows = read_csv(
            _runtime_input(manifest, "qrels_domain_csv", "qrels_domain_runtime.csv", current_run_dir)
        )
        qrels_object_rows = read_csv(
            _runtime_input(manifest, "qrels_object_csv", "qrels_object_runtime.csv", current_run_dir)
        )
        query_log_rows = read_csv(current_run_dir / "query_log.csv")
        probe_log_path = current_run_dir / "probe_log.csv"
        probe_log_rows = read_csv(probe_log_path) if probe_log_path.exists() else []
        search_trace_path = current_run_dir / "search_trace.csv"
        search_trace_rows = read_csv(search_trace_path) if search_trace_path.exists() else []

        runtime_query_ids = {entry["query_id"] for entry in query_rows}
        query_log_ids = {entry["query_id"] for entry in query_log_rows}
        probe_query_ids = {entry["query_id"] for entry in probe_log_rows}
        trace_query_ids = {entry["query_id"] for entry in search_trace_rows}
        active_domains = _active_domains(manifest)
        tiers = _workload_tiers(query_rows, experiment)
        strong_domains = _domain_support(qrels_domain_rows)
        relevant_support = {len(domains) for domains in strong_domains.values()}
        weak_object_counts = _weak_object_counts(qrels_object_rows)
        weak_object_support = {int(value) for value in weak_object_counts.values()}
        zone_constraint_coverage = (
            sum(1 for entry in query_rows if entry.get("zone_constraint", "")) / float(len(query_rows))
            if query_rows
            else 0.0
        )

        if not query_rows:
            errors.append(f"{row['run_id']}: runtime queries are missing")
            continue
        if runtime_query_ids != query_log_ids:
            errors.append(
                f"{row['run_id']}: query_log query ids do not match runtime queries "
                f"({len(query_log_ids)} vs {len(runtime_query_ids)})"
            )
        if set(strong_domains) != runtime_query_ids:
            errors.append(f"{row['run_id']}: qrels_domain_runtime does not cover the full runtime query slice")
        if {entry['query_id'] for entry in qrels_object_rows} != runtime_query_ids:
            errors.append(f"{row['run_id']}: qrels_object_runtime does not cover the full runtime query slice")
        if not probe_query_ids.issubset(runtime_query_ids):
            errors.append(f"{row['run_id']}: probe_log references queries outside runtime slice")
        if not trace_query_ids.issubset(runtime_query_ids):
            errors.append(f"{row['run_id']}: search_trace references queries outside runtime slice")
        if any(not domains for domains in strong_domains.values()):
            errors.append(f"{row['run_id']}: qrels_domain_runtime contains queries without strong domains")
        if active_domains:
            for query_id, domains in strong_domains.items():
                if not domains.issubset(active_domains):
                    errors.append(f"{row['run_id']}: {query_id} references inactive domains {sorted(domains - active_domains)}")

        if "routing_main" in tiers:
            combined_routing_support.update(relevant_support)
            if zone_constraint_coverage < 1.0:
                errors.append(f"{row['run_id']}: routing slice zone_constraint coverage={zone_constraint_coverage:.3f}")
            if relevant_support != {2, 3, 4}:
                errors.append(f"{row['run_id']}: routing relevant-domain support={sorted(relevant_support)}")

        if "object_main" in tiers:
            combined_object_support.update(relevant_support)
            combined_object_confusers.update(weak_object_support)
            if zone_constraint_coverage < 1.0:
                errors.append(f"{row['run_id']}: object slice zone_constraint coverage={zone_constraint_coverage:.3f}")
            if relevant_support != {1, 2}:
                errors.append(f"{row['run_id']}: object relevant-domain support={sorted(relevant_support)}")
            if len(weak_object_support) <= 1:
                errors.append(f"{row['run_id']}: object confuser-object support collapsed={sorted(weak_object_support)}")

        summaries.append(
            "RUN "
            + f"run_id={row['run_id']} "
            + f"queries={len(query_rows)} "
            + f"tiers={','.join(sorted(tiers)) or 'unknown'} "
            + f"zone_constraint_coverage={zone_constraint_coverage:.3f} "
            + f"relevant_domain_support={','.join(str(value) for value in sorted(relevant_support)) or 'none'} "
            + f"confuser_object_support={','.join(str(value) for value in sorted(weak_object_support)) or 'none'}"
        )

    if errors:
        for line in errors:
            print(f"ERROR: {line}")
        return 1

    print(
        "OK "
        + f"experiment={experiment['experiment_id']} "
        + f"registry_source={args.registry_source} "
        + f"run_id_scope={'scoped' if run_ids else 'full'} "
        + f"runs={len(rows)}"
    )
    if combined_routing_support:
        print(
            "SUMMARY "
            + "routing_relevant_domain_support="
            + ",".join(str(value) for value in sorted(combined_routing_support))
        )
    if combined_object_support:
        print(
            "SUMMARY "
            + "object_relevant_domain_support="
            + ",".join(str(value) for value in sorted(combined_object_support))
        )
    if combined_object_confusers:
        print(
            "SUMMARY "
            + "object_confuser_object_support="
            + ",".join(str(value) for value in sorted(combined_object_confusers))
        )
    for line in summaries:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
