"""Build discovery-reply status x failure-stage matrix from canonical logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import (
    aggregate_output_path,
    declared_output_filenames,
    load_experiment,
    log_frame,
    require_rows,
    sweep_field,
)
from tools.workflow_support import write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "budget",
    "manifest_size",
    "run_count",
    "query_count",
    "failure_stage",
    "reply_status",
    "reply_reason_code",
    "count",
    "rate",
    "source_run_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def _normalize_failure_stage(frame: pd.DataFrame) -> pd.Series:
    failure_stage = frame.get("failure_stage", pd.Series(index=frame.index, dtype=str)).fillna("")
    success_series = frame.get("success_at_1", pd.Series(index=frame.index, dtype=float))
    success = pd.to_numeric(success_series, errors="coerce").fillna(0.0)
    failure_type = frame.get("failure_type", pd.Series(index=frame.index, dtype=str)).fillna("")

    normalized = failure_stage.astype(str)
    normalized = normalized.where(normalized != "", "unknown")
    normalized = normalized.where(success != 1, "success")
    normalized = normalized.where(~((normalized == "unknown") & (failure_type == "predicate_miss")), "domain_selection")
    normalized = normalized.where(~((normalized == "unknown") & (failure_type == "wrong_object")), "local_resolution")
    normalized = normalized.where(~((normalized == "unknown") & (failure_type == "fetch_timeout")), "fetch")
    normalized = normalized.where(~((normalized == "unknown") & (failure_type == "no_reply")), "fetch")
    normalized = normalized.where(~((normalized == "unknown") & (failure_type == "wrong_domain")), "domain_selection")
    return normalized


def _infer_reply_status(probe_frame: pd.DataFrame) -> pd.Series:
    explicit = probe_frame.get("reply_status", pd.Series(index=probe_frame.index, dtype=str)).fillna("")
    explicit = explicit.astype(str).str.strip().str.lower()
    success_series = probe_frame.get("success", pd.Series(index=probe_frame.index, dtype=float))
    success = pd.to_numeric(success_series, errors="coerce").fillna(0.0)
    accepted_series = probe_frame.get("accepted", pd.Series(index=probe_frame.index, dtype=float))
    accepted = pd.to_numeric(accepted_series, errors="coerce").fillna(0.0)
    entries_series = probe_frame.get("reply_entries", pd.Series(index=probe_frame.index, dtype=float))
    reply_entries = pd.to_numeric(entries_series, errors="coerce").fillna(0.0)
    inferred = pd.Series("empty_manifest", index=probe_frame.index, dtype=str)
    inferred = inferred.where(~((success == 1) | (accepted == 1) | (reply_entries > 0)), "ok")
    return explicit.where(explicit != "", inferred)


def _latest_probe_status(probe_frame: pd.DataFrame) -> pd.DataFrame:
    if probe_frame.empty:
        return pd.DataFrame(columns=["run_id", "query_id", "reply_status", "reply_reason_code"])

    working = probe_frame.copy()
    working["probe_index"] = pd.to_numeric(working.get("probe_index", 0), errors="coerce").fillna(0.0)
    working["reply_status"] = _infer_reply_status(working)
    reason = working.get("reply_reason_code", pd.Series(index=working.index, dtype=str)).fillna("")
    reason = reason.astype(str).str.strip().str.lower()
    reason = reason.where(reason != "", "legacy_inferred")
    reason = reason.where(working["reply_status"] != "ok", "ok")
    working["reply_reason_code"] = reason

    latest = (
        working.sort_values(["run_id", "query_id", "probe_index"], kind="stable")
        .groupby(["run_id", "query_id"], as_index=False)
        .tail(1)
    )
    return latest[["run_id", "query_id", "reply_status", "reply_reason_code"]]


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    rows = require_rows(experiment, args.registry_source)
    query_frame = log_frame(rows, "query_log.csv")
    # Prefer raw probe logs because canonical normalization drops reply status/reason fields.
    probe_frame = log_frame(rows, "probe_log.csv", raw=True)

    if query_frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    active_sweep_field = sweep_field(experiment)
    query_frame = query_frame.copy()
    query_frame["failure_stage"] = _normalize_failure_stage(query_frame)

    latest_probe = _latest_probe_status(probe_frame)
    merged = query_frame.merge(latest_probe, on=["run_id", "query_id"], how="left")
    merged["reply_status"] = merged["reply_status"].fillna("missing_probe").astype(str)
    merged["reply_reason_code"] = merged["reply_reason_code"].fillna("missing_probe").astype(str)

    base_group = ["registry_scheme", "registry_topology_id", active_sweep_field]
    totals = (
        merged.groupby(base_group, sort=False)
        .size()
        .rename("query_count")
        .reset_index()
    )
    run_ids_by_group = (
        merged.groupby(base_group, sort=False)["run_id"]
        .apply(lambda series: "|".join(sorted(series.unique().tolist())))
        .rename("source_run_ids")
        .reset_index()
    )
    sweep_meta_columns = [column for column in ["budget", "manifest_size"] if column not in base_group]
    if sweep_meta_columns:
        sweep_meta = merged.groupby(base_group, sort=False)[sweep_meta_columns].max().reset_index()
    else:
        sweep_meta = merged[base_group].drop_duplicates().copy()
    run_count_by_group = (
        merged.groupby(base_group, sort=False)["run_id"]
        .nunique()
        .rename("run_count")
        .reset_index()
    )

    grouped = (
        merged.groupby(base_group + ["failure_stage", "reply_status", "reply_reason_code"], sort=False)
        .size()
        .rename("count")
        .reset_index()
    )
    grouped = grouped.merge(totals, on=base_group, how="left")
    grouped = grouped.merge(sweep_meta, on=base_group, how="left")
    grouped = grouped.merge(run_count_by_group, on=base_group, how="left")
    grouped = grouped.merge(run_ids_by_group, on=base_group, how="left")

    output_rows = []
    for row in grouped.itertuples(index=False):
        sweep_value = int(getattr(row, active_sweep_field))
        budget = sweep_value if active_sweep_field == "budget" else int(getattr(row, "budget"))
        manifest_size = sweep_value if active_sweep_field == "manifest_size" else int(getattr(row, "manifest_size"))
        query_count = int(getattr(row, "query_count"))
        count = int(getattr(row, "count"))
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": getattr(row, "registry_scheme"),
                "topology_id": getattr(row, "registry_topology_id"),
                "budget": budget,
                "manifest_size": manifest_size,
                "run_count": int(getattr(row, "run_count")),
                "query_count": query_count,
                "failure_stage": getattr(row, "failure_stage"),
                "reply_status": getattr(row, "reply_status"),
                "reply_reason_code": getattr(row, "reply_reason_code"),
                "count": count,
                "rate": round(float(count) / float(query_count), 6) if query_count > 0 else 0.0,
                "source_run_ids": getattr(row, "source_run_ids"),
            }
        )

    output_filename = "discovery_reply_stage_matrix.csv"
    if output_filename not in declared_output_filenames(experiment):
        output_filename = f"{experiment['experiment_id']}_discovery_reply_stage_matrix.csv"
    aggregate_path = aggregate_output_path(experiment, output_filename)
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
