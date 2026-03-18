"""Shared helpers for HiRoute evaluation scripts."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root


def load_experiment(path: Path) -> dict[str, Any]:
    experiment_path = path if path.is_absolute() else repo_root() / path
    return load_json_yaml(experiment_path)


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else repo_root() / path


def is_v3_experiment(experiment: dict[str, Any]) -> bool:
    return str(experiment.get("dataset_id", "")).endswith("_v3") or str(experiment.get("experiment_id", "")).endswith("_v3")


def _declared_output_path(experiment: dict[str, Any], filename: str) -> Path | None:
    for output in experiment.get("outputs", []):
        candidate = _resolve(str(output))
        if candidate.name == filename:
            return candidate
    return None


def declared_output_filenames(experiment: dict[str, Any]) -> set[str]:
    return {_resolve(str(output)).name for output in experiment.get("outputs", [])}


def sweep_field(experiment: dict[str, Any]) -> str:
    return "manifest_size" if experiment.get("manifest_sizes") else "budget"


def expected_sweep_values(experiment: dict[str, Any]) -> list[int]:
    if experiment.get("manifest_sizes"):
        return [int(value) for value in experiment.get("manifest_sizes", [])]
    if experiment.get("budgets"):
        return [int(value) for value in experiment.get("budgets", [])]
    default_manifest = int(experiment.get("default_manifest_size") or 0)
    if default_manifest:
        return [default_manifest]
    default_budget = int(experiment.get("default_budget") or 0)
    return [default_budget] if default_budget else []


def aggregate_output_path(experiment: dict[str, Any], filename: str) -> Path:
    declared = _declared_output_path(experiment, filename)
    if declared is not None:
        return declared
    base = repo_root() / "results" / "aggregate"
    if is_v3_experiment(experiment):
        base = base / "v3"
    return base / filename


def table_output_path(experiment: dict[str, Any], filename: str) -> Path:
    declared = _declared_output_path(experiment, filename)
    if declared is not None:
        return declared
    base = repo_root() / "results" / "tables"
    if is_v3_experiment(experiment):
        base = base / "v3"
    return base / filename


def figure_output_path(experiment: dict[str, Any], filename: str) -> Path:
    declared = _declared_output_path(experiment, filename)
    if declared is not None:
        return declared
    base = repo_root() / "results" / "figures"
    if is_v3_experiment(experiment):
        base = base / "v3"
    return base / filename


def _runs_index() -> dict[str, dict[str, str]]:
    runs_path = repo_root() / "runs" / "registry" / "runs.csv"
    if not runs_path.exists():
        return {}
    return {row["run_id"]: row for row in read_csv(runs_path)}


def expected_topology_ids(experiment: dict[str, Any]) -> set[str]:
    comparison_topologies = experiment.get("comparison_topologies", [])
    if comparison_topologies:
        return {str(topology_id) for topology_id in comparison_topologies}
    topology_id = experiment.get("topology_id")
    return {str(topology_id)} if topology_id else set()


def expected_scenarios(experiment: dict[str, Any]) -> set[str]:
    scenarios = set()
    scenario = experiment.get("scenario")
    if scenario:
        scenarios.add(str(scenario))
    runner = experiment.get("runner", {})
    for scenario_name in runner.get("scenario_variants", {}).values():
        scenarios.add(str(scenario_name))
    return scenarios


def registry_rows(experiment: dict[str, Any] | str, source: str = "promoted") -> list[dict[str, str]]:
    filename = "promoted_runs.csv" if source == "promoted" else "runs.csv"
    registry_path = repo_root() / "runs" / "registry" / filename
    if not registry_path.exists():
        return []

    if isinstance(experiment, dict):
        experiment_id = experiment["experiment_id"]
        expected_dataset_id = str(experiment.get("dataset_id", ""))
        expected_topologies = expected_topology_ids(experiment)
        expected_seeds = {str(seed) for seed in experiment.get("seeds", [])}
        expected_schemes = {str(scheme) for scheme in experiment.get("schemes", [])}
        allowed_scenarios = expected_scenarios(experiment)
        sweep_values = {int(value) for value in expected_sweep_values(experiment)}
        manifest_sizes = {int(value) for value in experiment.get("manifest_sizes", [])}
    else:
        experiment_id = experiment
        expected_dataset_id = ""
        expected_topologies = set()
        expected_seeds = set()
        expected_schemes = set()
        allowed_scenarios = set()
        sweep_values = set()
        manifest_sizes = set()

    run_index = _runs_index()
    rows = []
    for row in read_csv(registry_path):
        if row["experiment_id"] != experiment_id:
            continue
        if expected_dataset_id and row["dataset_id"] != expected_dataset_id:
            continue
        if expected_topologies and row["topology_id"] not in expected_topologies:
            continue
        if expected_seeds and row["seed"] not in expected_seeds:
            continue
        if expected_schemes and row["scheme"] not in expected_schemes:
            continue
        if manifest_sizes:
            if int(row.get("manifest_size") or 0) not in manifest_sizes:
                continue
        elif sweep_values and int(row.get("budget") or 0) not in sweep_values:
            continue
        enriched = dict(row)
        if "run_dir" not in enriched or not enriched["run_dir"]:
            enriched["run_dir"] = run_index.get(row["run_id"], {}).get("run_dir", "")
        if allowed_scenarios and enriched.get("run_dir"):
            manifest_path = run_dir(enriched) / "manifest.yaml"
            if manifest_path.exists():
                try:
                    manifest = load_json_yaml(manifest_path)
                except Exception:
                    continue
                if manifest.get("scenario", "") not in allowed_scenarios:
                    continue
        rows.append(enriched)
    return rows


def run_dir(row: dict[str, str]) -> Path:
    return repo_root() / row["run_dir"]


def read_manifest(row: dict[str, str]) -> dict[str, Any]:
    return load_json_yaml(run_dir(row) / "manifest.yaml")


def _log_path(row: dict[str, str], filename: str, raw: bool) -> Path:
    candidate = run_dir(row) / filename
    if raw:
        raw_candidate = candidate.with_suffix(candidate.suffix + ".raw")
        if raw_candidate.exists():
            return raw_candidate
    return candidate


def log_frame(rows: list[dict[str, str]], filename: str, raw: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for row in rows:
        path = _log_path(row, filename, raw)
        if not path.exists():
            continue
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        frame["run_id"] = row["run_id"]
        frame["experiment_id"] = row["experiment_id"]
        frame["registry_scheme"] = row["scheme"]
        frame["registry_topology_id"] = row["topology_id"]
        frame["budget"] = int(row.get("budget") or 0)
        frame["manifest_size"] = int(row.get("manifest_size") or 0)
        frame["seed"] = int(row["seed"])
        manifest = read_manifest(row)
        frame["scenario"] = manifest.get("scenario", "")
        frame["scenario_variant"] = manifest.get("scenario_variant", "")
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def require_rows(experiment: dict[str, Any] | str, source: str) -> list[dict[str, str]]:
    rows = registry_rows(experiment, source)
    if not rows:
        experiment_id = experiment["experiment_id"] if isinstance(experiment, dict) else experiment
        raise RuntimeError(f"no registry rows available for experiment '{experiment_id}' from source '{source}'")
    return rows


def bootstrap_mean_ci(series: pd.Series, replicates: int = 1000, seed: int = 0) -> float:
    values = series.dropna().to_numpy(dtype=float)
    if values.size <= 1:
        return 0.0
    if np.allclose(values, values[0]):
        return 0.0
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(replicates, values.size), replace=True)
    means = samples.mean(axis=1)
    lower, upper = np.quantile(means, [0.025, 0.975])
    return float((upper - lower) / 2.0)


def qrels_maps_by_topology(experiment: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inputs = experiment.get("inputs", {})
    topology_ids = expected_topology_ids(experiment) or {str(experiment.get("topology_id", ""))}
    payload: dict[str, dict[str, Any]] = {}
    for topology_id in topology_ids:
        qrels_domain_path = inputs.get("qrels_domain_csvs", {}).get(topology_id, inputs.get("qrels_domain_csv"))
        qrels_object_path = inputs.get("qrels_object_csvs", {}).get(topology_id, inputs.get("qrels_object_csv"))
        strong_domains: dict[str, set[str]] = {}
        weak_domains: dict[str, set[str]] = {}
        relevant_objects: dict[str, set[str]] = {}
        if qrels_domain_path:
            for row in read_csv(_resolve(qrels_domain_path)):
                if row.get("is_relevant_domain", "1") == "1":
                    strong_domains.setdefault(row["query_id"], set()).add(row["domain_id"])
                elif row.get("relevance_strength", "") == "weak":
                    weak_domains.setdefault(row["query_id"], set()).add(row["domain_id"])
        if qrels_object_path:
            for row in read_csv(_resolve(qrels_object_path)):
                if int(row.get("relevance") or 0) >= 2:
                    relevant_objects.setdefault(row["query_id"], set()).add(row["object_id"])
        payload[topology_id] = {
            "strong_domains": strong_domains,
            "weak_domains": weak_domains,
            "relevant_objects": relevant_objects,
        }
    return payload
