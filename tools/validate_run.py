"""Validate a HiRoute experiment before execution."""

from __future__ import annotations

import argparse
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


def validate_context(
    experiment_path: Path,
    scheme: str,
    seed: int,
    mode: str,
    topology_id: str | None = None,
    variant: str | None = None,
) -> tuple[dict[str, Any], list[str]]:
    experiment = load_json_yaml(experiment_path)
    errors: list[str] = []

    if scheme not in experiment.get("schemes", []):
        errors.append(f"scheme '{scheme}' is not listed in experiment schemes")
    if seed not in experiment.get("seeds", []):
        errors.append(f"seed '{seed}' is not listed in experiment seeds")

    _resolve_topology(experiment, topology_id, errors)
    _resolve_variant(experiment, variant, errors)

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

    return experiment, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--mode", choices=["dry", "official"], default="official")
    parser.add_argument("--topology-id")
    parser.add_argument("--variant")
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
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
