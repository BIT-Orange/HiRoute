"""Validate manifest-size monotonicity and probe-stability expectations across completed runs."""

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


RELAXED_PROBE_STABILITY_EXPERIMENTS = {"object_main", "ablation"}


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
    parser.add_argument(
        "--allow-probe-order-change",
        action="store_true",
        help="Do not fail when per-query probe sequence differs across manifest sizes.",
    )
    parser.add_argument(
        "--allow-selected-object-change",
        action="store_true",
        help="Do not fail when selected object differs for the same probe slot.",
    )
    parser.add_argument(
        "--strict-probe-stability",
        action="store_true",
        help="Force strict probe-sequence/object stability even for experiments with relaxed defaults.",
    )
    parser.add_argument(
        "--allow-success-regression-with-aggregate-gain",
        action="store_true",
        help=(
            "Demote per-query success_at_1 regressions to warnings WHEN the aggregate "
            "success_at_1 across manifest sizes is monotonically non-decreasing. "
            "Use this only for workloads (object_main, ablation) where predicate-miss "
            "dominates failure mass and the manifest's role is bounded fallback rather "
            "than per-query top-1 stability. The aggregate gain check is still strict: "
            "if the higher manifest's mean success_at_1 drops, this remains an error."
        ),
    )
    return parser.parse_args()


def _probe_stability_relaxed(args: argparse.Namespace) -> bool:
    if args.strict_probe_stability:
        return False
    if args.allow_probe_order_change or args.allow_selected_object_change:
        return True
    experiment_id = str(args.experiment_id or "")
    return experiment_id in RELAXED_PROBE_STABILITY_EXPERIMENTS


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

    relaxed_probe_stability = _probe_stability_relaxed(args)
    warnings: list[str] = []

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

            # Compute aggregate-mean monotonicity over common queries before
            # deciding whether per-query regressions can be demoted to warnings.
            ref_mean = sum(reference_success[q] for q in common_queries) / len(common_queries)
            cand_mean = sum(candidate_success[q] for q in common_queries) / len(common_queries)
            aggregate_monotonic = cand_mean + 1e-9 >= ref_mean
            allow_per_query_regression = (
                args.allow_success_regression_with_aggregate_gain and aggregate_monotonic
            )

            per_query_regressions: list[tuple[str, int, int]] = []
            for query_id in common_queries:
                if candidate_success[query_id] < reference_success[query_id]:
                    per_query_regressions.append(
                        (query_id, reference_size, candidate_size)
                    )

            if per_query_regressions and not allow_per_query_regression:
                for query_id, ref_size, cand_size in per_query_regressions:
                    errors.append(
                        f"{group_key}: success_at_1 regressed for {query_id} at manifest {ref_size}->{cand_size}"
                    )
            elif per_query_regressions:
                # Aggregate is monotonic but per-query is not; surface as a
                # warning with an aggregate-delta annotation so reviewers can
                # see what the workload actually does.
                summary = (
                    f"{group_key}: {len(per_query_regressions)} per-query success_at_1 "
                    f"regressions at manifest {reference_size}->{candidate_size} are tolerated "
                    f"because aggregate mean rises {ref_mean:.3f}->{cand_mean:.3f} "
                    f"(+{(cand_mean - ref_mean) * 100:.1f}pp)"
                )
                warnings.append(summary)
                preview = per_query_regressions[:5]
                for query_id, ref_size, cand_size in preview:
                    warnings.append(
                        f"{group_key}: per-query regression for {query_id} at manifest {ref_size}->{cand_size}"
                    )
                if len(per_query_regressions) > len(preview):
                    warnings.append(
                        f"{group_key}: ... {len(per_query_regressions) - len(preview)} additional per-query regressions omitted"
                    )

            if not aggregate_monotonic:
                errors.append(
                    f"{group_key}: aggregate mean success_at_1 regressed at manifest "
                    f"{reference_size}->{candidate_size} ({ref_mean:.3f}->{cand_mean:.3f})"
                )

            common_probe_queries = sorted(set(reference_probes) & set(candidate_probes))
            for query_id in common_probe_queries:
                left_sequence = [_probe_identity(row) for row in reference_probes[query_id]]
                right_sequence = [_probe_identity(row) for row in candidate_probes[query_id]]
                if left_sequence != right_sequence:
                    message = (
                        f"{group_key}: probe order changed for {query_id} at manifest "
                        f"{reference_size}->{candidate_size}"
                    )
                    if relaxed_probe_stability:
                        warnings.append(message)
                    else:
                        errors.append(message)
                    continue

                for left_row, right_row in zip(reference_probes[query_id], candidate_probes[query_id]):
                    left_object = _selected_object(left_row)
                    right_object = _selected_object(right_row)
                    if left_object and right_object and left_object != right_object:
                        message = (
                            f"{group_key}: top manifest candidate changed for {query_id} "
                            f"probe {left_row.get('probe_index', '')} at manifest {reference_size}->{candidate_size}"
                        )
                        if relaxed_probe_stability:
                            warnings.append(message)
                        else:
                            errors.append(message)

    if checked_groups == 0:
        print("ERROR: no scheme/topology/seed groups contain multiple manifest sizes")
        return 1

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if warnings:
        print(
            "WARN: probe stability checks relaxed; "
            f"ignored {len(warnings)} probe-order/candidate differences"
        )
        preview = warnings[:10]
        for message in preview:
            print(f"WARN: {message}")
        if len(warnings) > len(preview):
            print(f"WARN: ... {len(warnings) - len(preview)} additional differences omitted")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
