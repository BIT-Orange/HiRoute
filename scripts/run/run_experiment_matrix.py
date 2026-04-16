"""Run an experiment matrix with resume support and optional post-processing."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, repo_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--mode", default="official")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--scheme", action="append", dest="schemes")
    parser.add_argument("--topology-id", action="append", dest="topology_ids")
    parser.add_argument("--budget", action="append", type=int, dest="budgets")
    parser.add_argument("--manifest-size", action="append", type=int, dest="manifest_sizes")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--variant", action="append", dest="variants")
    parser.add_argument("--include-reference-sweep", action="store_true")
    parser.add_argument("--postprocess", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _load_experiment(path: Path) -> dict[str, Any]:
    experiment_path = _resolve(path)
    experiment = load_json_yaml(experiment_path)
    experiment["_experiment_path"] = experiment_path
    return experiment


def _expected_topologies(experiment: dict[str, Any], override: list[str] | None) -> list[str]:
    if override:
        return list(dict.fromkeys(override))
    comparison = [str(value) for value in experiment.get("comparison_topologies", [])]
    if comparison:
        return comparison
    topology_id = str(experiment.get("topology_id", ""))
    return [topology_id] if topology_id else []


def _expected_schemes(experiment: dict[str, Any], override: list[str] | None) -> list[str]:
    if override:
        return list(dict.fromkeys(override))
    return [str(value) for value in experiment.get("schemes", [])]


def _expected_seeds(experiment: dict[str, Any], override: list[int] | None) -> list[int]:
    if override:
        return list(dict.fromkeys(int(value) for value in override))
    return [int(value) for value in experiment.get("seeds", [1])]


def _expected_variants(experiment: dict[str, Any], override: list[str] | None) -> list[str | None]:
    if override:
        return list(dict.fromkeys(override))
    variants = list((experiment.get("runner", {}) or {}).get("scenario_variants", {}).keys())
    if variants:
        return variants
    return [None]


def _sweep_values(
    experiment: dict[str, Any],
    scheme: str,
    include_reference_sweep: bool,
    budget_override: list[int] | None,
    manifest_override: list[int] | None,
) -> tuple[str, list[int]]:
    reference_schemes = {str(value) for value in experiment.get("reference_schemes", [])}
    if experiment.get("manifest_sizes"):
        values = manifest_override or [int(value) for value in experiment.get("manifest_sizes", [])]
        if scheme in reference_schemes and not include_reference_sweep:
            default_manifest = int(experiment.get("default_manifest_size") or 0)
            values = [default_manifest] if default_manifest else values
        return "manifest_size", list(dict.fromkeys(int(value) for value in values))

    values = budget_override or [int(value) for value in experiment.get("budgets", [])]
    if scheme in reference_schemes and not include_reference_sweep:
        default_budget = int(experiment.get("default_budget") or 0)
        values = [default_budget] if default_budget else values
    return "budget", list(dict.fromkeys(int(value) for value in values))


def _completed_keys(experiment: dict[str, Any], sweep_field: str) -> set[tuple[str, str, int, int, str | None]]:
    runs_path = repo_root() / "runs" / "registry" / "runs.csv"
    if not runs_path.exists():
        return set()

    keys: set[tuple[str, str, int, int, str | None]] = set()
    with runs_path.open("r", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["experiment_id"] != experiment["experiment_id"] or row["status"] != "completed":
                continue
            run_dir = row.get("run_dir", "")
            scenario_variant = None
            if run_dir:
                manifest_path = repo_root() / run_dir / "manifest.yaml"
                if manifest_path.exists():
                    try:
                        manifest = load_json_yaml(manifest_path)
                        scenario_variant = manifest.get("scenario_variant") or None
                    except Exception:
                        scenario_variant = None
            keys.add(
                (
                    row["scheme"],
                    row["topology_id"],
                    int(row.get(sweep_field) or 0),
                    int(row["seed"]),
                    scenario_variant,
                )
            )
    return keys


def _command(
    experiment_path: Path,
    scheme: str,
    topology_id: str,
    seed: int,
    sweep_field: str,
    sweep_value: int,
    mode: str,
    variant: str | None,
) -> list[str]:
    cmd = [
        sys.executable,
        str(repo_root() / "scripts" / "run" / "run_experiment.py"),
        "--experiment",
        str(experiment_path),
        "--scheme",
        scheme,
        "--seed",
        str(seed),
        "--topology-id",
        topology_id,
        "--mode",
        mode,
    ]
    if sweep_field == "budget":
        cmd.extend(["--budget", str(sweep_value)])
    else:
        cmd.extend(["--manifest-size", str(sweep_value)])
    if variant:
        cmd.extend(["--variant", variant])
    return cmd


def _run_one(item: tuple[str, list[str]]) -> tuple[str, int, str, str]:
    label, cmd = item
    result = subprocess.run(
        cmd,
        cwd=repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    return label, result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def _postprocess(experiment_path: Path, validate: bool, experiment: dict[str, Any]) -> None:
    commands = [
        [sys.executable, str(repo_root() / "scripts" / "eval" / "promote_runs.py"), "--experiment", str(experiment_path)],
        [sys.executable, str(repo_root() / "scripts" / "eval" / "aggregate_experiment.py"), "--experiment", str(experiment_path)],
        [sys.executable, str(repo_root() / "scripts" / "plots" / "plot_experiment.py"), "--experiment", str(experiment_path)],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=repo_root(), check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "postprocess command failed")
        if result.stdout:
            print(result.stdout.strip())

    if not validate:
        return

    for output in experiment.get("outputs", []):
        if not str(output).endswith(".csv"):
            continue
        cmd = [
            sys.executable,
            str(repo_root() / "tools" / "validate_figures.py"),
            "--experiment",
            str(experiment_path),
            "--aggregate",
            str(_resolve(Path(str(output)))),
        ]
        result = subprocess.run(cmd, cwd=repo_root(), check=False, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "validate_figures failed")
        if result.stdout:
            print(result.stdout.strip())


def main() -> int:
    args = parse_args()
    experiment = _load_experiment(args.experiment)
    experiment_path = Path(experiment["_experiment_path"])

    schemes = _expected_schemes(experiment, args.schemes)
    topologies = _expected_topologies(experiment, args.topology_ids)
    seeds = _expected_seeds(experiment, args.seeds)
    variants = _expected_variants(experiment, args.variants)
    sweep_field = "manifest_size" if experiment.get("manifest_sizes") else "budget"
    completed = set() if args.force_rerun else _completed_keys(experiment, sweep_field)

    work_items: list[tuple[str, list[str]]] = []
    for topology_id in topologies:
        for scheme in schemes:
            _, sweep_values = _sweep_values(
                experiment,
                scheme,
                args.include_reference_sweep,
                args.budgets,
                args.manifest_sizes,
            )
            for sweep_value in sweep_values:
                for seed in seeds:
                    for variant in variants:
                        key = (scheme, topology_id, int(sweep_value), int(seed), variant)
                        if key in completed:
                            continue
                        label = f"{scheme}@{topology_id}@{sweep_field}{sweep_value}@seed{seed}"
                        if variant:
                            label = f"{label}@{variant}"
                        work_items.append(
                            (
                                label,
                                _command(
                                    experiment_path,
                                    scheme,
                                    topology_id,
                                    int(seed),
                                    sweep_field,
                                    int(sweep_value),
                                    args.mode,
                                    variant,
                                ),
                            )
                        )

    print(f"matrix_missing={len(work_items)}")
    if not work_items:
        if args.postprocess:
            _postprocess(experiment_path, args.validate, experiment)
        return 0

    failures: list[tuple[str, str, str]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(args.max_workers))) as executor:
        futures = [executor.submit(_run_one, item) for item in work_items]
        for future in as_completed(futures):
            label, returncode, stdout, stderr = future.result()
            print(f"{label} rc={returncode}")
            if returncode != 0:
                failures.append((label, stdout, stderr))
                if stdout:
                    print(stdout)
                if stderr:
                    print(stderr)

    if failures:
        print(f"matrix_failures={len(failures)}")
        return 1

    if args.postprocess:
        _postprocess(experiment_path, args.validate, experiment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
