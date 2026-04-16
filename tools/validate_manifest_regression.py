"""Validate manifest-size monotonicity and probe-order stability across completed runs."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import read_run_ids_file
from tools.workflow_support import load_json_yaml, repo_root


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _discover_run_dirs(runs_root: Path) -> list[Path]:
    return sorted(path.parent for path in runs_root.glob("*/manifest.yaml"))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default="runs/completed", type=Path)
    parser.add_argument("--run-dir", action="append", default=[], type=Path)
    parser.add_argument("--run-ids-file", type=Path)
    parser.add_argument("--experiment-id")
    parser.add_argument("--scheme")
    parser.add_argument("--dataset-id")
    parser.add_argument("--topology-id")
    parser.add_argument("--seed", type=int)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _load_run_bundle(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.yaml"
    manifest = load_json_yaml(manifest_path)
    query_log = _read_csv_rows(run_dir / "query_log.csv")
    probe_log_path = run_dir / "probe_log.csv"
    raw_probe_log_path = probe_log_path.with_suffix(".csv.raw")
    if raw_probe_log_path.exists():
        probe_log = _read_csv_rows(raw_probe_log_path)
    else:
        probe_log = _read_csv_rows(probe_log_path)
    return {
        "run_dir": run_dir,
        "manifest": manifest,
        "query_log": query_log,
        "probe_log": probe_log,
    }


def _select_runs(args: argparse.Namespace) -> list[dict[str, Any]]:
    scoped_run_ids = read_run_ids_file(args.run_ids_file)
    if args.run_dir:
        run_dirs = [_resolve(path) for path in args.run_dir]
    elif scoped_run_ids:
        run_dirs = [repo_root() / "runs" / "completed" / run_id for run_id in sorted(scoped_run_ids)]
    else:
        run_dirs = _discover_run_dirs(_resolve(args.runs_root))
    selected: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        manifest_path = run_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue
        manifest = load_json_yaml(manifest_path)
        if args.experiment_id and str(manifest.get("experiment_id")) != args.experiment_id:
            continue
        if args.scheme and str(manifest.get("scheme")) != args.scheme:
            continue
        if args.dataset_id and str(manifest.get("dataset_id")) != args.dataset_id:
            continue
        if args.topology_id and str(manifest.get("topology_id")) != args.topology_id:
            continue
        if args.seed is not None and int(manifest.get("seed") or 0) != args.seed:
            continue
        selected.append(_load_run_bundle(run_dir))
    return selected


def _latest_per_manifest_size(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    for run in runs:
        manifest_size = int(run["manifest"].get("manifest_size") or 0)
        incumbent = chosen.get(manifest_size)
        if incumbent is None:
            chosen[manifest_size] = run
            continue
        incumbent_end = str(incumbent["manifest"].get("end_time") or "")
        candidate_end = str(run["manifest"].get("end_time") or "")
        if candidate_end >= incumbent_end:
            chosen[manifest_size] = run
    return [chosen[key] for key in sorted(chosen)]


def _query_success_by_id(rows: list[dict[str, str]]) -> dict[str, int]:
    return {row["query_id"]: int(row.get("success_at_1") or 0) for row in rows}


def _probe_sequence_by_query(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["query_id"]].append(row)
    for query_id, query_rows in grouped.items():
        grouped[query_id] = sorted(query_rows, key=lambda row: int(row.get("probe_index") or 0))
    return grouped


def _probe_identity(row: dict[str, str]) -> tuple[str, str]:
    controller = row.get("controller_prefix", "")
    if controller:
        return (str(row.get("probe_index", "")), controller)
    return (str(row.get("probe_index", "")), str(row.get("target_domain_id", "")))


def _selected_object(row: dict[str, str]) -> str:
    return str(row.get("selected_object_id", ""))


def _group_key(run: dict[str, Any]) -> tuple[str, str, str, int]:
    manifest = run["manifest"]
    return (
        str(manifest.get("experiment_id") or ""),
        str(manifest.get("scheme") or ""),
        str(manifest.get("topology_id") or ""),
        int(manifest.get("seed") or 0),
    )


def main() -> int:
    args = _parse_args()
    runs = _select_runs(args)
    if not runs:
        print("ERROR: no matching completed runs found")
        return 1

    grouped: dict[tuple[str, str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        grouped[_group_key(run)].append(run)

    errors: list[str] = []
    checked_groups = 0
    for group_key, group_runs in sorted(grouped.items()):
        manifest_runs = _latest_per_manifest_size(group_runs)
        if len(manifest_runs) < 2:
            continue
        checked_groups += 1
        reference = manifest_runs[0]
        reference_size = int(reference["manifest"].get("manifest_size") or 0)
        reference_success = _query_success_by_id(reference["query_log"])
        reference_probes = _probe_sequence_by_query(reference["probe_log"])

        for candidate in manifest_runs[1:]:
            candidate_size = int(candidate["manifest"].get("manifest_size") or 0)
            candidate_success = _query_success_by_id(candidate["query_log"])
            candidate_probes = _probe_sequence_by_query(candidate["probe_log"])
            common_queries = sorted(set(reference_success) & set(candidate_success))
            if not common_queries:
                errors.append(
                    f"{group_key}: manifest {reference_size}->{candidate_size} has no common query ids"
                )
                continue

            for query_id in common_queries:
                if candidate_success[query_id] < reference_success[query_id]:
                    errors.append(
                        f"{group_key}: success_at_1 regressed for {query_id} at manifest {reference_size}->{candidate_size}"
                    )

            common_probe_queries = sorted(set(reference_probes) & set(candidate_probes))
            for query_id in common_probe_queries:
                left_sequence = [_probe_identity(row) for row in reference_probes[query_id]]
                right_sequence = [_probe_identity(row) for row in candidate_probes[query_id]]
                if left_sequence != right_sequence:
                    errors.append(
                        f"{group_key}: probe order changed for {query_id} at manifest {reference_size}->{candidate_size}"
                    )
                    continue

                for left_row, right_row in zip(reference_probes[query_id], candidate_probes[query_id]):
                    left_object = _selected_object(left_row)
                    right_object = _selected_object(right_row)
                    if left_object and right_object and left_object != right_object:
                        errors.append(
                            f"{group_key}: top manifest candidate changed for {query_id} "
                            f"probe {left_row.get('probe_index', '')} at manifest {reference_size}->{candidate_size}"
                        )

    if checked_groups == 0:
        print("ERROR: no scheme/topology/seed groups contain multiple manifest sizes")
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
