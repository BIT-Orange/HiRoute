"""Shared helpers for HiRoute evaluation scripts."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root


def load_experiment(path: Path) -> dict[str, Any]:
    experiment_path = path if path.is_absolute() else repo_root() / path
    return load_json_yaml(experiment_path)


def _runs_index() -> dict[str, dict[str, str]]:
    runs_path = repo_root() / "runs" / "registry" / "runs.csv"
    if not runs_path.exists():
        return {}
    return {row["run_id"]: row for row in read_csv(runs_path)}


def registry_rows(experiment_id: str, source: str = "promoted") -> list[dict[str, str]]:
    filename = "promoted_runs.csv" if source == "promoted" else "runs.csv"
    registry_path = repo_root() / "runs" / "registry" / filename
    if not registry_path.exists():
        return []

    run_index = _runs_index()
    rows = []
    for row in read_csv(registry_path):
        if row["experiment_id"] != experiment_id:
            continue
        enriched = dict(row)
        if "run_dir" not in enriched or not enriched["run_dir"]:
            enriched["run_dir"] = run_index.get(row["run_id"], {}).get("run_dir", "")
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
        frame["seed"] = int(row["seed"])
        manifest = read_manifest(row)
        frame["scenario"] = manifest.get("scenario", "")
        frame["scenario_variant"] = manifest.get("scenario_variant", "")
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def require_rows(experiment_id: str, source: str) -> list[dict[str, str]]:
    rows = registry_rows(experiment_id, source)
    if not rows:
        raise RuntimeError(f"no registry rows available for experiment '{experiment_id}' from source '{source}'")
    return rows

