"""Validate a HiRoute experiment before execution."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import GENERATED_TRACKED_PREFIXES, git_dirty, load_json_yaml, repo_root

DIAGNOSTIC_EXPERIMENT_IDS = {"routing_debug", "object_debug"}
MAINLINE_EXPERIMENT_IDS = {"routing_main", "object_main", "ablation", "state_scaling", "robustness"}


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return repo_root() / path


def _resolve_input_path(experiment: dict[str, Any], field: str) -> Path | None:
    inputs = experiment.get("inputs", {})
    input_path = inputs.get(field)
    if input_path:
        return _resolve(str(input_path))
    dataset_config = experiment.get("configs", {}).get("dataset")
    if not dataset_config:
        return None
    dataset_manifest = load_json_yaml(_resolve(str(dataset_config)))
    output_path = (dataset_manifest.get("outputs", {}) or {}).get(field)
    if not output_path:
        return None
    return _resolve(str(output_path))


def _allow_dirty_worktree_override() -> bool:
    return os.environ.get("HIROUTE_ALLOW_DIRTY_WORKTREE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


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


def _resolve_manifest_size(experiment: dict[str, Any], manifest_size: int | None, errors: list[str]) -> None:
    configured = [int(value) for value in experiment.get("manifest_sizes", [])]
    selected = manifest_size
    if selected is None:
        selected = int(experiment.get("default_manifest_size") or 0)
    if not selected:
        runner_params = experiment.get("runner", {}).get("params", {})
        selected = int(runner_params.get("manifestSize") or 0)
    if configured and selected and selected not in configured:
        errors.append(f"manifest size '{selected}' is not listed in experiment manifest_sizes")
    experiment["_selected_manifest_size"] = int(selected or 0)


def _query_explicit_domains(query_row: dict[str, str]) -> set[str]:
    domains = set()
    zone_constraint = query_row.get("zone_constraint", "")
    if zone_constraint and "-zone-" in zone_constraint:
        domains.add(zone_constraint.split("-zone-")[0])
    domains.update(re.findall(r"\b(domain-\d+)\b", query_row.get("query_text", "")))
    return domains


def _validate_query_slice(experiment: dict[str, Any], errors: list[str]) -> None:
    inputs = experiment.get("inputs", {})
    topology_rows = list(
        csv.DictReader(_resolve(inputs["topology_mapping_csv"]).open("r", newline="", encoding="utf-8"))
    )
    active_domains = {row["domain_id"] for row in topology_rows if row.get("domain_id")}
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
    allowed_query_ids = {str(value) for value in query_filters.get("query_ids", [])}
    min_intended_domain_count = int(query_filters.get("min_intended_domain_count", 0) or 0)
    max_ingress_nodes = int(query_filters.get("max_ingress_nodes", 0) or 0)
    max_queries_per_ingress = int(query_filters.get("max_queries_per_ingress", 0) or 0)
    max_total_queries = int(query_filters.get("max_total_queries", 0) or 0)

    allowed_ingress_nodes = None
    if max_ingress_nodes > 0:
        ingress_nodes = sorted(row["node_id"] for row in topology_rows if row.get("role") == "ingress")
        allowed_ingress_nodes = set(ingress_nodes[:max_ingress_nodes])

    surviving_rows: list[dict[str, str]] = []
    for row in query_rows:
        if allowed_splits and row.get("split", "") not in allowed_splits:
            continue
        if allowed_tiers and row.get("workload_tier", "") not in allowed_tiers:
            continue
        if allowed_ambiguity and row.get("ambiguity_level", "") not in allowed_ambiguity:
            continue
        if allowed_query_ids and row["query_id"] not in allowed_query_ids:
            continue
        if min_intended_domain_count and int(row.get("intended_domain_count") or 0) < min_intended_domain_count:
            continue
        relevant_domains = relevant_domains_by_query.get(row["query_id"], set())
        if not relevant_domains or not relevant_domains.issubset(active_domains):
            continue
        if not _query_explicit_domains(row).issubset(active_domains):
            continue
        if allowed_ingress_nodes and row.get("ingress_node_id", "") not in allowed_ingress_nodes:
            continue
        surviving_rows.append(row)

    if max_queries_per_ingress > 0 and surviving_rows:
        per_ingress_counts: dict[str, int] = {}
        trimmed_rows = []
        for row in surviving_rows:
            ingress_node = row.get("ingress_node_id", "")
            current = per_ingress_counts.get(ingress_node, 0)
            if current >= max_queries_per_ingress:
                continue
            per_ingress_counts[ingress_node] = current + 1
            trimmed_rows.append(row)
        surviving_rows = trimmed_rows

    if max_total_queries > 0 and surviving_rows:
        surviving_rows = surviving_rows[:max_total_queries]

    surviving = len(surviving_rows)

    experiment["_validation_query_count"] = surviving
    if surviving == 0:
        errors.append(f"no eligible queries remain after split/tier/topology filtering for {experiment['experiment_id']}")
        return

    min_test_queries = int(
        experiment.get("promotion_rule", {}).get("min_test_queries_per_scheme_budget_tier", 0) or 0
    )
    if min_test_queries > 0 and surviving < min_test_queries:
        errors.append(
            f"eligible query slice is too small for promotion threshold: {surviving} < {min_test_queries}"
        )


def _validate_ablation_contract(experiment: dict[str, Any], errors: list[str]) -> None:
    ablation_schemes = {
        "predicates_only",
        "flat_semantic_only",
        "predicates_plus_flat",
        "full_hiroute",
    }
    experiment_schemes = {str(scheme) for scheme in experiment.get("schemes", [])}
    if experiment_schemes != ablation_schemes:
        return

    runner = experiment.get("runner", {})
    params = runner.get("params", {}) if isinstance(runner, dict) else {}
    if runner.get("type") != "ndnsim":
        errors.append("ablation experiments must use the ndnsim runner")
    if int(experiment.get("default_budget") or 0) == 0:
        if int(experiment.get("default_manifest_size") or 0) == 0:
            errors.append("ablation experiments must set a single default budget or default_manifest_size")
    for required_flag in ["manifestSize", "probeBudget", "queryLimitPerIngress"]:
        if required_flag not in params:
            errors.append(f"ablation experiments must pin runner.params.{required_flag}")


def _validate_v3_contract(experiment: dict[str, Any], mode: str, errors: list[str]) -> None:
    dataset_id = str(experiment.get("dataset_id", ""))
    experiment_id = str(experiment.get("experiment_id", ""))
    if dataset_id not in {"smartcity_v3", "smartcity"}:
        return

    runner = experiment.get("runner", {})
    if runner.get("type") != "ndnsim":
        errors.append(f"{dataset_id} official experiments must use runner.type=ndnsim")

    query_filters = experiment.get("query_filters", {}) or {}
    workload_tiers = set(str(value) for value in query_filters.get("workload_tiers", []))
    if dataset_id == "smartcity":
        allowed_tiers = {"routing_main", "object_main", "sanity_appendix"}
        routing_experiments = {"routing_main", "state_scaling", "robustness"}
        object_experiments = {"object_main", "ablation"}
        mainline_experiments = MAINLINE_EXPERIMENT_IDS
        expected_output_fragment = "/mainline/"
        label = "mainline"
    else:
        allowed_tiers = {"routing_hard_v3", "object_hard_v3", "sanity_appendix_v3"}
        routing_experiments = {"exp_routing_main_v3", "exp_routing_main_v3_compact", "exp_scaling_v3_compact", "exp_robustness_v3_compact"}
        object_experiments = {"exp_object_main_v3", "exp_ablation_v3", "exp_object_main_v3_compact", "exp_ablation_v3_compact"}
        mainline_experiments = {
            "exp_routing_main_v3",
            "exp_object_main_v3",
            "exp_ablation_v3",
            "exp_routing_main_v3_compact",
            "exp_object_main_v3_compact",
            "exp_ablation_v3_compact",
        }
        expected_output_fragment = "/v3/compact/" if experiment_id.endswith("_v3_compact") else "/v3/"
        label = "v3"
    if workload_tiers and not workload_tiers.issubset(allowed_tiers):
        errors.append(f"{dataset_id} experiments must only reference {label} workload tiers")

    if mode == "official" and experiment_id in mainline_experiments:
        if set(query_filters.get("splits", [])) != {"test"}:
            errors.append(f"official {label} experiments must use split=test only")
    if experiment_id in mainline_experiments and query_filters.get("query_ids"):
        errors.append(f"{experiment_id} must not use query_filters.query_ids")

    routing_tier = "routing_main" if dataset_id == "smartcity" else "routing_hard_v3"
    object_tier = "object_main" if dataset_id == "smartcity" else "object_hard_v3"
    sanity_tier = "sanity_appendix" if dataset_id == "smartcity" else "sanity_appendix_v3"

    if experiment_id in routing_experiments and workload_tiers != {routing_tier}:
        errors.append(f"{experiment_id} must use {routing_tier} only")
    if experiment_id in object_experiments and workload_tiers != {object_tier}:
        errors.append(f"{experiment_id} must use {object_tier} only")
    if experiment_id in {"exp_sanity_appendix_v3", "sanity_appendix"} and workload_tiers != {sanity_tier}:
        errors.append(f"{experiment_id} must use {sanity_tier} only")
    if experiment_id == "routing_debug" and workload_tiers != {routing_tier}:
        errors.append(f"{experiment_id} must use {routing_tier} only")
    if experiment_id == "object_debug" and workload_tiers != {object_tier}:
        errors.append(f"{experiment_id} must use {object_tier} only")
    if experiment_id in DIAGNOSTIC_EXPERIMENT_IDS:
        selected_query_ids = [str(value) for value in query_filters.get("query_ids", [])]
        if not selected_query_ids:
            errors.append(f"{experiment_id} must set query_filters.query_ids")

    requires_compact_topology = (
        ((dataset_id == "smartcity" and experiment_id not in DIAGNOSTIC_EXPERIMENT_IDS) or experiment_id.endswith("_v3_compact"))
        and experiment_id != "state_scaling"
    )
    if requires_compact_topology:
        topology_path = experiment.get("configs", {}).get("topology", "")
        mapping_path = experiment.get("inputs", {}).get("topology_mapping_csv", "")
        if "compact" not in str(topology_path):
            errors.append(f"{label} experiments must use a compact topology config")
        if "compact" not in str(mapping_path):
            errors.append(f"{label} experiments must use a compact topology mapping")
        aggregate_outputs = [str(path) for path in experiment.get("outputs", [])]
        if not aggregate_outputs or any(expected_output_fragment not in path for path in aggregate_outputs):
            errors.append(f"{label} experiments must write outputs under results/*{expected_output_fragment}")

    if dataset_id == "smartcity" or experiment_id in {
        "exp_routing_main_v3_compact",
        "exp_object_main_v3_compact",
        "exp_ablation_v3_compact",
    }:
        for field in ["max_ingress_nodes", "max_queries_per_ingress", "max_total_queries"]:
            if int(query_filters.get(field, 0) or 0) != 0:
                errors.append(f"{experiment_id} must not use query_filters.{field}")
        params = runner.get("params", {}) if isinstance(runner, dict) else {}
        if int(params.get("queryLimitPerIngress", 0) or 0) != 0:
            errors.append(f"{experiment_id} must set runner.params.queryLimitPerIngress=0")

    if experiment_id in {"exp_routing_main_v3_compact", "routing_main"}:
        schemes = {str(value) for value in experiment.get("schemes", [])}
        required_schemes = {
            "predicates_only",
            "random_admissible",
            "inf_tag_forwarding",
            "hiroute",
            "central_directory",
        }
        missing_schemes = sorted(required_schemes - schemes)
        if missing_schemes:
            errors.append(
                f"{experiment_id} is missing required routing baselines: "
                + ", ".join(missing_schemes)
            )


def validate_context(
    experiment_path: Path,
    scheme: str,
    seed: int,
    mode: str,
    topology_id: str | None = None,
    variant: str | None = None,
    budget: int | None = None,
    manifest_size: int | None = None,
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
    _resolve_manifest_size(experiment, manifest_size, errors)

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
        if experiment.get("dataset_id") == "smartcity":
            required_inputs.extend(
                ["query_embeddings_csv", "object_embeddings_csv", "summary_embeddings_csv"]
            )
    for field in required_inputs:
        input_path = _resolve_input_path(experiment, field)
        if input_path is None:
            errors.append(f"missing inputs.{field}")
            continue
        if not input_path.exists():
            errors.append(f"missing input file: {input_path}")

    if configs.get("topology") and _resolve(configs["topology"]).exists():
        topology_config = load_json_yaml(_resolve(configs["topology"]))
        annotated_topology = topology_config.get("annotated_topology_path")
        if not annotated_topology:
            errors.append(f"missing annotated_topology_path in {configs['topology']}")
        elif not _resolve(annotated_topology).exists():
            errors.append(f"missing annotated topology file: {annotated_topology}")

    if mode == "official" and git_dirty(GENERATED_TRACKED_PREFIXES) and not _allow_dirty_worktree_override():
        errors.append("official runs require a clean git worktree")

    if not errors:
        _validate_query_slice(experiment, errors)
        _validate_ablation_contract(experiment, errors)
        _validate_v3_contract(experiment, mode, errors)

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
    parser.add_argument("--manifest-size", type=int)
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
        args.manifest_size,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
