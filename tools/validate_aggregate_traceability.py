"""Validate aggregate rows against promoted runs and emit per-aggregate trace sidecars."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import load_experiment, read_run_ids_file, registry_rows
from tools.workflow_support import isoformat_z, read_csv, repo_root


TRACE_KEY_FIELDS = [
    "scheme",
    "topology_id",
    "budget",
    "manifest_size",
    "stage",
    "deadline_ms",
    "failure_type",
    "scaling_axis",
    "scaling_value",
    "scenario_variant",
    "time_bin_s",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    parser.add_argument("--run-ids-file", type=Path)
    parser.add_argument("--aggregate-root", type=Path)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _aggregate_paths(experiment: dict, aggregate_root: Path | None) -> list[Path]:
    if aggregate_root is not None:
        root = _resolve(aggregate_root)
        return sorted(path for path in root.glob("*.csv"))
    candidates: list[Path] = []
    for output in experiment.get("outputs", []):
        output_path = _resolve(Path(str(output)))
        if output_path.suffix == ".csv" and "results/aggregate/" in str(output_path):
            candidates.append(output_path)
    return candidates


def _query_count_for_run(run_dir: Path, cache: dict[str, int]) -> int:
    cache_key = str(run_dir)
    if cache_key in cache:
        return cache[cache_key]
    query_log_path = run_dir / "query_log.csv"
    if not query_log_path.exists():
        cache[cache_key] = 0
        return 0
    cache[cache_key] = len(read_csv(query_log_path))
    return cache[cache_key]


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    run_ids = read_run_ids_file(args.run_ids_file)
    aggregate_paths = _aggregate_paths(experiment, args.aggregate_root)
    if not aggregate_paths:
        print("ERROR: experiment does not declare aggregate CSV outputs")
        return 1

    scoped_rows = registry_rows(experiment, args.registry_source, run_ids=run_ids)
    if not scoped_rows:
        print(f"ERROR: no {args.registry_source} rows found for experiment")
        return 1

    run_index = {
        row["run_id"]: row
        for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv")
    }
    promoted_run_ids = {row["run_id"] for row in scoped_rows}
    query_count_cache: dict[str, int] = {}
    errors: list[str] = []

    for aggregate_path in aggregate_paths:
        aggregate_errors: list[str] = []
        if not aggregate_path.exists():
            errors.append(f"{aggregate_path.relative_to(repo_root())}: aggregate is missing")
            continue
        rows = read_csv(aggregate_path)
        if not rows:
            errors.append(f"{aggregate_path.relative_to(repo_root())}: aggregate is empty")
            continue
        if "source_run_ids" not in rows[0]:
            errors.append(f"{aggregate_path.relative_to(repo_root())}: source_run_ids column is missing")
            continue

        trace_rows = []
        for index, row in enumerate(rows):
            source_run_ids = [value for value in str(row.get("source_run_ids", "")).split("|") if value]
            if not source_run_ids:
                aggregate_errors.append(f"{aggregate_path.relative_to(repo_root())}: row {index} has no source_run_ids")
                continue
            if not set(source_run_ids).issubset(promoted_run_ids):
                missing = sorted(set(source_run_ids) - promoted_run_ids)
                aggregate_errors.append(
                    f"{aggregate_path.relative_to(repo_root())}: row {index} references non-promoted runs {missing}"
                )
                continue

            source_run_dirs: list[str] = []
            total_source_query_count = 0
            for run_id in source_run_ids:
                run_row = run_index.get(run_id)
                if run_row is None or not run_row.get("run_dir"):
                    aggregate_errors.append(f"{aggregate_path.relative_to(repo_root())}: missing run_dir for {run_id}")
                    continue
                current_run_dir = repo_root() / run_row["run_dir"]
                if not (current_run_dir / "query_log.csv").exists():
                    aggregate_errors.append(f"{aggregate_path.relative_to(repo_root())}: query_log missing for {run_id}")
                    continue
                source_run_dirs.append(str(Path(run_row["run_dir"])))
                total_source_query_count += _query_count_for_run(current_run_dir, query_count_cache)
                if row.get("scheme") and run_row.get("scheme") != row.get("scheme"):
                    aggregate_errors.append(
                        f"{aggregate_path.relative_to(repo_root())}: row {index} scheme={row.get('scheme')} mismatches {run_id}"
                    )
                if row.get("topology_id") and run_row.get("topology_id") != row.get("topology_id"):
                    aggregate_errors.append(
                        f"{aggregate_path.relative_to(repo_root())}: row {index} topology_id={row.get('topology_id')} mismatches {run_id}"
                    )

            if row.get("run_count"):
                try:
                    declared_run_count = int(float(row["run_count"]))
                    if declared_run_count != len(source_run_ids):
                        aggregate_errors.append(
                            f"{aggregate_path.relative_to(repo_root())}: row {index} run_count={declared_run_count} "
                            f"does not match source_run_ids={len(source_run_ids)}"
                        )
                except ValueError:
                    aggregate_errors.append(f"{aggregate_path.relative_to(repo_root())}: row {index} run_count is not numeric")

            if row.get("query_count"):
                try:
                    declared_query_count = int(float(row["query_count"]))
                    if declared_query_count <= 0:
                        aggregate_errors.append(
                            f"{aggregate_path.relative_to(repo_root())}: row {index} query_count must be positive"
                        )
                    if total_source_query_count and declared_query_count > total_source_query_count:
                        aggregate_errors.append(
                            f"{aggregate_path.relative_to(repo_root())}: row {index} query_count={declared_query_count} "
                            f"exceeds source total={total_source_query_count}"
                        )
                except ValueError:
                    aggregate_errors.append(f"{aggregate_path.relative_to(repo_root())}: row {index} query_count is not numeric")

            trace_rows.append(
                {
                    "row_index": index,
                    "locator": {field: row.get(field, "") for field in TRACE_KEY_FIELDS if field in row},
                    "source_run_ids": source_run_ids,
                    "source_run_dirs": source_run_dirs,
                    "source_query_count_total": total_source_query_count,
                    "row_query_count": row.get("query_count", ""),
                }
            )

        if aggregate_errors:
            errors.extend(aggregate_errors)
            continue

        trace_path = aggregate_path.with_suffix(".trace.json")
        trace_path.write_text(
            json.dumps(
                {
                    "experiment_id": experiment["experiment_id"],
                    "aggregate_csv": str(aggregate_path.relative_to(repo_root())),
                    "generated_at": isoformat_z(),
                    "row_count": len(trace_rows),
                    "rows": trace_rows,
                },
                indent=2,
                sort_keys=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(str(trace_path.relative_to(repo_root())))

    if errors:
        for line in errors:
            print(f"ERROR: {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
