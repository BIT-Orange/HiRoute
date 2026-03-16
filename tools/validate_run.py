"""Validate a HiRoute experiment before execution."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import GENERATED_TRACKED_PREFIXES, git_dirty, load_json_yaml, repo_root


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return repo_root() / path


def _resolve_topology(experiment: dict[str, Any], topology_id: str | None, errors: list[str]) -> None:
    configs = experiment.setdefault("configs", {})
    inputs = experiment.setdefault("inputs", {})
    selected_topology = topology_id or experiment.get("topology_id")
    if not selected_topology:
        errors.append("missing experiment topology_id")
        return

    comparison_topologies = experiment.get("comparison_topologies", [])
    if topology_id and comparison_topologies and selected_topology not in comparison_topologies:
        errors.append(f"topology '{selected_topology}' is not listed in comparison_topologies")

    topology_config = configs.get("topology_overlays", {}).get(selected_topology, configs.get("topology"))
    topology_mapping = inputs.get("topology_mappings", {}).get(
        selected_topology, inputs.get("topology_mapping_csv")
    )
    if not topology_config:
        errors.append(f"missing topology config for topology '{selected_topology}'")
    if not topology_mapping:
        errors.append(f"missing topology mapping for topology '{selected_topology}'")

    experiment["topology_id"] = selected_topology
    if topology_config:
        configs["topology"] = topology_config
    if topology_mapping:
        inputs["topology_mapping_csv"] = topology_mapping

    bundle_mappings = [
        ("query_csvs", "queries_csv"),
        ("qrels_object_csvs", "qrels_object_csv"),
        ("qrels_domain_csvs", "qrels_domain_csv"),
        ("query_embedding_index_csvs", "query_embedding_index_csv"),
    ]
    for bundle_key, scalar_key in bundle_mappings:
        values = inputs.get(bundle_key, {})
        if not values:
            continue
        selected_value = values.get(selected_topology)
        if not selected_value:
            errors.append(f"missing inputs.{bundle_key}.{selected_topology}")
            continue
        inputs[scalar_key] = selected_value


def _resolve_variant(experiment: dict[str, Any], variant: str | None, errors: list[str]) -> None:
    runner = experiment.setdefault("runner", {})
    scenario_variants = runner.get("scenario_variants", {})
    selected_variant = variant or runner.get("default_variant")
    if variant and variant not in scenario_variants:
        errors.append(f"variant '{variant}' is not configured for this experiment")
        return
    if selected_variant:
        if selected_variant not in scenario_variants:
            errors.append(f"default variant '{selected_variant}' is not configured")
            return
        experiment["scenario"] = scenario_variants[selected_variant]
        experiment["_runner_variant"] = selected_variant


def _resolve_budget(experiment: dict[str, Any], budget: int | None, errors: list[str]) -> None:
    configured = [int(value) for value in experiment.get("budgets", [])]
    selected = budget
    if selected is None:
        selected = int(experiment.get("default_budget") or 0)
    if not selected:
        runner_params = experiment.get("runner", {}).get("params", {})
        selected = int(runner_params.get("exportBudget") or 0)
    if configured and selected and selected not in configured:
        errors.append(f"budget '{selected}' is not listed in experiment budgets")
    experiment["_selected_budget"] = int(selected or 0)


def _query_explicit_domains(query_row: dict[str, str]) -> set[str]:
    domains = set()
    zone_constraint = query_row.get("zone_constraint", "")
    if zone_constraint and "-zone-" in zone_constraint:
        domains.add(zone_constraint.split("-zone-")[0])
    domains.update(re.findall(r"\b(domain-\d+)\b", query_row.get("query_text", "")))
    return domains


def _validate_query_slice(experiment: dict[str, Any], errors: list[str]) -> None:
    inputs = experiment.get("inputs", {})
    active_domains = {
        row["domain_id"]
        for row in csv.DictReader(_resolve(inputs["topology_mapping_csv"]).open("r", newline="", encoding="utf-8"))
        if row.get("domain_id")
    }
    query_rows = list(csv.DictReader(_resolve(inputs["queries_csv"]).open("r", newline="", encoding="utf-8")))
    qrels_domain_rows = list(csv.DictReader(_resolve(inputs["qrels_domain_csv"]).open("r", newline="", encoding="utf-8")))

    relevant_domains_by_query: dict[str, set[str]] = {}
    for row in qrels_domain_rows:
        if row.get("is_relevant_domain", "1") != "1":
            continue
        relevant_domains_by_query.setdefault(row["query_id"], set()).add(row["domain_id"])

    query_filters = experiment.get("query_filters", {}) or {}
    allowed_splits = {str(value) for value in query_filters.get("splits", [])}
    allowed_tiers = {str(value) for value in query_filters.get("workload_tiers", [])}
    allowed_ambiguity = {str(value) for value in query_filters.get("ambiguity_levels", [])}
    min_intended_domain_count = int(query_filters.get("min_intended_domain_count", 0) or 0)

    surviving = 0
    for row in query_rows:
        if allowed_splits and row.get("split", "") not in allowed_splits:
            continue
        if allowed_tiers and row.get("workload_tier", "") not in allowed_tiers:
            continue
        if allowed_ambiguity and row.get("ambiguity_level", "") not in allowed_ambiguity:
            continue
        if min_intended_domain_count and int(row.get("intended_domain_count") or 0) < min_intended_domain_count:
            continue
        relevant_domains = relevant_domains_by_query.get(row["query_id"], set())
        if not relevant_domains or not relevant_domains.issubset(active_domains):
            continue
        if not _query_explicit_domains(row).issubset(active_domains):
            continue
        surviving += 1

    experiment["_validation_query_count"] = surviving
    if surviving == 0:
        errors.append(f"no eligible queries remain after split/tier/topology filtering for {experiment['experiment_id']}")


def validate_context(
    experiment_path: Path,
    scheme: str,
    seed: int,
    mode: str,
    topology_id: str | None = None,
    variant: str | None = None,
    budget: int | None = None,
) -> tuple[dict[str, Any], list[str]]:
    experiment = load_json_yaml(experiment_path)
    errors: list[str] = []

    if scheme not in experiment.get("schemes", []):
        errors.append(f"scheme '{scheme}' is not listed in experiment schemes")
    if seed not in experiment.get("seeds", []):
        errors.append(f"seed '{seed}' is not listed in experiment seeds")

    _resolve_topology(experiment, topology_id, errors)
    _resolve_variant(experiment, variant, errors)
    _resolve_budget(experiment, budget, errors)

    configs = experiment.get("configs", {})
    inputs = experiment.get("inputs", {})
    baseline_map = configs.get("baselines", {})

    for label in ["dataset", "hierarchy", "topology"]:
        config_path = configs.get(label)
        if not config_path:
            errors.append(f"missing configs.{label}")
            continue
        if not _resolve(config_path).exists():
            errors.append(f"missing config file: {config_path}")

    if scheme not in baseline_map:
        errors.append(f"missing baseline config for scheme '{scheme}'")
    elif not _resolve(baseline_map[scheme]).exists():
        errors.append(f"missing baseline config file: {baseline_map[scheme]}")

    required_inputs = [
        "objects_csv",
        "queries_csv",
        "qrels_object_csv",
        "qrels_domain_csv",
        "hslsa_csv",
        "topology_mapping_csv",
    ]
    if experiment.get("runner", {}).get("type") == "ndnsim":
        required_inputs.extend(["query_embedding_index_csv", "controller_local_index_csv"])
    for field in required_inputs:
        input_path = inputs.get(field)
        if not input_path:
            errors.append(f"missing inputs.{field}")
            continue
        if not _resolve(input_path).exists():
            errors.append(f"missing input file: {input_path}")

    if configs.get("topology") and _resolve(configs["topology"]).exists():
        topology_config = load_json_yaml(_resolve(configs["topology"]))
        annotated_topology = topology_config.get("annotated_topology_path")
        if not annotated_topology:
            errors.append(f"missing annotated_topology_path in {configs['topology']}")
        elif not _resolve(annotated_topology).exists():
            errors.append(f"missing annotated topology file: {annotated_topology}")

    if mode == "official" and git_dirty(GENERATED_TRACKED_PREFIXES):
        errors.append("official runs require a clean git worktree")

    if not errors:
        _validate_query_slice(experiment, errors)

    return experiment, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--mode", choices=["dry", "official"], default="official")
    parser.add_argument("--topology-id")
    parser.add_argument("--variant")
    parser.add_argument("--budget", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _, errors = validate_context(
        args.experiment,
        args.scheme,
        args.seed,
        args.mode,
        args.topology_id,
        args.variant,
        args.budget,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
