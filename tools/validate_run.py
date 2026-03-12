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


def validate_context(experiment_path: Path, scheme: str, seed: int, mode: str) -> tuple[dict[str, Any], list[str]]:
    experiment = load_json_yaml(experiment_path)
    errors: list[str] = []

    if scheme not in experiment.get("schemes", []):
        errors.append(f"scheme '{scheme}' is not listed in experiment schemes")
    if seed not in experiment.get("seeds", []):
        errors.append(f"seed '{seed}' is not listed in experiment seeds")

    configs = experiment.get("configs", {})
    inputs = experiment.get("inputs", {})
    baseline_map = configs.get("baselines", {})

    for label in ["dataset", "hierarchy"]:
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
    for field in required_inputs:
        input_path = inputs.get(field)
        if not input_path:
            errors.append(f"missing inputs.{field}")
            continue
        if not _resolve(input_path).exists():
            errors.append(f"missing input file: {input_path}")

    if mode == "official" and git_dirty(GENERATED_TRACKED_PREFIXES):
        errors.append("official runs require a clean git worktree")

    return experiment, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--mode", choices=["dry", "official"], default="official")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    _, errors = validate_context(args.experiment, args.scheme, args.seed, args.mode)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
