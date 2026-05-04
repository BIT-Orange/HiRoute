"""Build Figure 4 aggregate from canonical query logs."""

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
    bootstrap_mean_ci,
    load_experiment,
    log_frame,
    qrels_maps_by_topology,
    require_rows,
    sweep_field,
    table_output_path,
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
    "mean_success_at_1",
    "terminal_strong_success_rate",
    "terminal_loose_success_rate",
    "final_end_to_end_success_rate",
    "ci_success_at_1",
    "first_fetch_relevant_rate",
    "first_fetch_strong_relevant_rate",
    "first_fetch_loose_relevant_rate",
    "first_manifest_top1_correct_rate",
    "ci_first_fetch_relevant_rate",
    "mean_manifest_fetch_index_success_only",
    "mean_manifest_rescue_rank_success_only",
    "mean_manifest_hit_at_5",
    "mean_ndcg_at_5",
    "mean_num_remote_probes",
    "ci_num_remote_probes",
    "mean_discovery_bytes",
    "ci_discovery_bytes",
    "mean_latency_ms",
    "ci_latency_ms",
    "relevant_domain_reached_at_1",
    "ci_relevant_domain_reached_at_1",
    "relevant_domain_reached_at_k",
    "ci_relevant_domain_reached_at_k",
    "best_object_chosen_given_relevant_domain",
    "manifest_rescue_rate",
    "within_reply_manifest_rescue_rate",
    "cross_probe_manifest_rescue_rate",
    "mean_cumulative_manifest_fetches_success_only",
    "first_probe_relevant_domain_hit_rate",
    "mean_first_probe_domain_rank",
    "failure_stage_domain_selection_rate",
    "failure_stage_local_resolution_rate",
    "failure_stage_fetch_rate",
    "mean_num_relevant_domains",
    "mean_num_confuser_domains",
    "mean_num_confuser_objects",
    "effective_exported_summaries_total",
    "effective_exported_summaries_per_domain_mean",
    "source_run_ids",
]

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    rows = require_rows(experiment, args.registry_source)
    frame = log_frame(rows, "query_log.csv")
    probe_frame = log_frame(rows, "probe_log.csv")
    state_frame = log_frame(rows, "state_log.csv")
    if frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    bootstrap_replicates = int(experiment.get("statistics", {}).get("bootstrap_replicates", 1000))
    active_sweep_field = sweep_field(experiment)
    qrels_maps = qrels_maps_by_topology(experiment)
    frame = frame.copy()
    frame["success_at_1"] = pd.to_numeric(frame["success_at_1"], errors="coerce").fillna(0.0)
    frame["terminal_strong_success"] = frame["success_at_1"]
    frame["terminal_loose_success"] = pd.to_numeric(
        frame.get("terminal_loose_success", frame["success_at_1"]), errors="coerce"
    ).fillna(0.0)
    frame["manifest_hit_at_5"] = pd.to_numeric(frame["manifest_hit_at_5"], errors="coerce").fillna(0.0)
    frame["ndcg_at_5"] = pd.to_numeric(frame["ndcg_at_5"], errors="coerce").fillna(0.0)
    frame["num_remote_probes"] = pd.to_numeric(frame["num_remote_probes"], errors="coerce").fillna(0.0)
    frame["latency_ms"] = pd.to_numeric(frame["latency_ms"], errors="coerce").fillna(0.0)
    frame["discovery_tx_bytes"] = pd.to_numeric(frame["discovery_tx_bytes"], errors="coerce").fillna(0.0)
    frame["discovery_rx_bytes"] = pd.to_numeric(frame["discovery_rx_bytes"], errors="coerce").fillna(0.0)
    frame["first_fetch_relevant"] = pd.to_numeric(frame.get("first_fetch_relevant", 0), errors="coerce").fillna(0.0)
    frame["first_fetch_strong_relevant"] = frame["first_fetch_relevant"]
    frame["first_fetch_loose_relevant"] = pd.to_numeric(
        frame.get("first_fetch_loose_relevant", frame["first_fetch_relevant"]),
        errors="coerce",
    ).fillna(0.0)
    frame["manifest_fetch_index"] = pd.to_numeric(frame.get("manifest_fetch_index", 0), errors="coerce").fillna(0.0)
    frame["first_probe_relevant_domain_hit"] = pd.to_numeric(
        frame.get("first_probe_relevant_domain_hit", 0), errors="coerce"
    ).fillna(0.0)
    frame["first_probe_domain_rank"] = pd.to_numeric(
        frame.get("first_probe_domain_rank", 0), errors="coerce"
    ).fillna(0.0)
    frame["num_relevant_domains"] = pd.to_numeric(
        frame.get("num_relevant_domains", 0), errors="coerce"
    ).fillna(0.0)
    frame["num_confuser_domains"] = pd.to_numeric(
        frame.get("num_confuser_domains", 0), errors="coerce"
    ).fillna(0.0)
    frame["num_confuser_objects"] = pd.to_numeric(
        frame.get("num_confuser_objects", 0), errors="coerce"
    ).fillna(0.0)
    frame["cumulative_manifest_fetches"] = pd.to_numeric(
        frame.get("cumulative_manifest_fetches", 0), errors="coerce"
    ).fillna(0.0)
    frame["failure_stage_domain_selection"] = (
        frame.get("failure_stage", pd.Series(index=frame.index, dtype=str)) == "domain_selection"
    ).astype(float)
    frame["failure_stage_local_resolution"] = (
        frame.get("failure_stage", pd.Series(index=frame.index, dtype=str)) == "local_resolution"
    ).astype(float)
    frame["failure_stage_fetch"] = (
        frame.get("failure_stage", pd.Series(index=frame.index, dtype=str)) == "fetch"
    ).astype(float)
    frame["discovery_bytes_total"] = frame["discovery_tx_bytes"] + frame["discovery_rx_bytes"]
    # Phase 2 rescue split (see docs/metrics/metric_semantics.md).
    frame["within_reply_manifest_rescue"] = (
        (frame["success_at_1"] == 1) & (frame["manifest_fetch_index"] > 0)
    ).astype(float)
    frame["cross_probe_manifest_rescue"] = (
        (frame["success_at_1"] == 1)
        & (frame["cumulative_manifest_fetches"] > 0)
        & (frame["manifest_fetch_index"] == 0)
    ).astype(float)
    frame["manifest_rescue"] = frame["within_reply_manifest_rescue"]

    if not probe_frame.empty:
        probe_frame = probe_frame.copy()
        probe_frame["probe_index"] = probe_frame["probe_index"].astype(int)
        probe_summary = []
        for (run_id, query_id, topology_id), group in probe_frame.groupby(
            ["run_id", "query_id", "registry_topology_id"], sort=False
        ):
            relevant_domains = qrels_maps.get(topology_id, {}).get("strong_domains", {}).get(query_id, set())
            ordered = group.sort_values("probe_index")
            first_domain = str(ordered.iloc[0]["target_domain_id"]) if not ordered.empty else ""
            probed_domains = set(str(value) for value in ordered["target_domain_id"].tolist())
            probe_summary.append(
                {
                    "run_id": run_id,
                    "query_id": query_id,
                    "registry_topology_id": topology_id,
                    "relevant_domain_reached_at_1": 1.0 if first_domain in relevant_domains else 0.0,
                    "relevant_domain_reached_at_k": 1.0 if relevant_domains & probed_domains else 0.0,
                }
            )
        if probe_summary:
            frame = frame.merge(pd.DataFrame(probe_summary), on=["run_id", "query_id", "registry_topology_id"], how="left")
    if "relevant_domain_reached_at_1" not in frame.columns:
        frame["relevant_domain_reached_at_1"] = frame["first_probe_relevant_domain_hit"]
    if "relevant_domain_reached_at_k" not in frame.columns:
        frame["relevant_domain_reached_at_k"] = 0.0

    def _best_object_given_domain(row: pd.Series) -> float:
        relevant_domains = qrels_maps.get(str(row["registry_topology_id"]), {}).get("strong_domains", {}).get(str(row["query_id"]), set())
        return float(row["success_at_1"]) if str(row["final_domain_id"]) in relevant_domains else float("nan")

    frame["best_object_chosen_given_relevant_domain"] = frame.apply(_best_object_given_domain, axis=1)

    state_summary_by_run = {}
    if not state_frame.empty:
        grouped = state_frame.groupby("run_id", sort=False)
        for run_id, group in grouped:
            ordered = group.copy()
            ordered["timestamp_ms"] = ordered["timestamp_ms"].astype(float)
            latest_timestamp = ordered["timestamp_ms"].max()
            latest = ordered[ordered["timestamp_ms"] == latest_timestamp]
            total = float(latest["num_exported_summaries"].astype(float).sum())
            per_domain_mean = float(latest["num_exported_summaries"].astype(float).mean()) if not latest.empty else 0.0
            state_summary_by_run[run_id] = {
                "effective_exported_summaries_total": total,
                "effective_exported_summaries_per_domain_mean": per_domain_mean,
            }

    output_rows = []
    group_columns = ["registry_scheme", "registry_topology_id", active_sweep_field]
    for keys, group in frame.groupby(group_columns, sort=False):
        scheme, topology_id, sweep_value = keys
        run_ids = sorted(group["run_id"].unique().tolist())
        state_totals = [
            state_summary_by_run[run_id]["effective_exported_summaries_total"]
            for run_id in run_ids
            if run_id in state_summary_by_run
        ]
        state_per_domain = [
            state_summary_by_run[run_id]["effective_exported_summaries_per_domain_mean"]
            for run_id in run_ids
            if run_id in state_summary_by_run
        ]
        budget = int(sweep_value) if active_sweep_field == "budget" else int(group["budget"].max())
        manifest_size = int(sweep_value) if active_sweep_field == "manifest_size" else int(group["manifest_size"].max())
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "budget": budget,
                "manifest_size": manifest_size,
                "run_count": len(run_ids),
                "query_count": int(len(group)),
                "mean_success_at_1": round(group["success_at_1"].mean(), 6),
                "terminal_strong_success_rate": round(
                    group["terminal_strong_success"].mean(), 6
                ),
                "terminal_loose_success_rate": round(
                    group["terminal_loose_success"].mean(), 6
                ),
                "final_end_to_end_success_rate": round(group["success_at_1"].mean(), 6),
                "ci_success_at_1": round(
                    bootstrap_mean_ci(group["success_at_1"], bootstrap_replicates), 6
                ),
                "first_fetch_relevant_rate": round(group["first_fetch_relevant"].mean(), 6),
                "first_fetch_strong_relevant_rate": round(
                    group["first_fetch_strong_relevant"].mean(), 6
                ),
                "first_fetch_loose_relevant_rate": round(
                    group["first_fetch_loose_relevant"].mean(), 6
                ),
                "first_manifest_top1_correct_rate": round(group["first_fetch_relevant"].mean(), 6),
                "ci_first_fetch_relevant_rate": round(
                    bootstrap_mean_ci(group["first_fetch_relevant"], bootstrap_replicates, seed=6), 6
                ),
                "mean_manifest_fetch_index_success_only": round(
                    group.loc[group["success_at_1"] == 1, "manifest_fetch_index"].mean()
                    if (group["success_at_1"] == 1).any()
                    else 0.0,
                    6,
                ),
                "mean_manifest_rescue_rank_success_only": round(
                    group.loc[group["success_at_1"] == 1, "manifest_fetch_index"].mean()
                    if (group["success_at_1"] == 1).any()
                    else 0.0,
                    6,
                ),
                "mean_manifest_hit_at_5": round(group["manifest_hit_at_5"].mean(), 6),
                "mean_ndcg_at_5": round(group["ndcg_at_5"].mean(), 6),
                "mean_num_remote_probes": round(group["num_remote_probes"].mean(), 6),
                "ci_num_remote_probes": round(
                    bootstrap_mean_ci(group["num_remote_probes"], bootstrap_replicates, seed=1), 6
                ),
                "mean_discovery_bytes": round(group["discovery_bytes_total"].mean(), 6),
                "ci_discovery_bytes": round(
                    bootstrap_mean_ci(group["discovery_bytes_total"], bootstrap_replicates, seed=2), 6
                ),
                "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                "ci_latency_ms": round(
                    bootstrap_mean_ci(group["latency_ms"], bootstrap_replicates, seed=3), 6
                ),
                "relevant_domain_reached_at_1": round(group["relevant_domain_reached_at_1"].mean(), 6),
                "ci_relevant_domain_reached_at_1": round(
                    bootstrap_mean_ci(group["relevant_domain_reached_at_1"], bootstrap_replicates, seed=4), 6
                ),
                "relevant_domain_reached_at_k": round(group["relevant_domain_reached_at_k"].mean(), 6),
                "ci_relevant_domain_reached_at_k": round(
                    bootstrap_mean_ci(group["relevant_domain_reached_at_k"], bootstrap_replicates, seed=5), 6
                ),
                "best_object_chosen_given_relevant_domain": round(
                    group["best_object_chosen_given_relevant_domain"].dropna().mean() if group["best_object_chosen_given_relevant_domain"].notna().any() else 0.0,
                    6,
                ),
                "manifest_rescue_rate": round(group["manifest_rescue"].mean(), 6),
                "within_reply_manifest_rescue_rate": round(
                    group["within_reply_manifest_rescue"].mean(), 6
                ),
                "cross_probe_manifest_rescue_rate": round(
                    group["cross_probe_manifest_rescue"].mean(), 6
                ),
                "mean_cumulative_manifest_fetches_success_only": round(
                    group.loc[group["success_at_1"] == 1, "cumulative_manifest_fetches"].mean()
                    if (group["success_at_1"] == 1).any()
                    else 0.0,
                    6,
                ),
                "first_probe_relevant_domain_hit_rate": round(
                    group["first_probe_relevant_domain_hit"].mean(), 6
                ),
                "mean_first_probe_domain_rank": round(
                    group.loc[group["first_probe_domain_rank"] > 0, "first_probe_domain_rank"].mean()
                    if (group["first_probe_domain_rank"] > 0).any()
                    else 0.0,
                    6,
                ),
                "failure_stage_domain_selection_rate": round(
                    group["failure_stage_domain_selection"].mean(), 6
                ),
                "failure_stage_local_resolution_rate": round(
                    group["failure_stage_local_resolution"].mean(), 6
                ),
                "failure_stage_fetch_rate": round(group["failure_stage_fetch"].mean(), 6),
                "mean_num_relevant_domains": round(group["num_relevant_domains"].mean(), 6),
                "mean_num_confuser_domains": round(group["num_confuser_domains"].mean(), 6),
                "mean_num_confuser_objects": round(group["num_confuser_objects"].mean(), 6),
                "effective_exported_summaries_total": round(sum(state_totals) / len(state_totals), 6) if state_totals else 0.0,
                "effective_exported_summaries_per_domain_mean": round(sum(state_per_domain) / len(state_per_domain), 6) if state_per_domain else 0.0,
                "source_run_ids": "|".join(run_ids),
            }
        )

    if experiment["experiment_id"] in {"exp_sanity_appendix_v2", "exp_sanity_appendix_v3", "sanity_appendix"}:
        aggregate_path = table_output_path(experiment, "appendix_sanity_success_overhead.csv")
        table_path = aggregate_path
    elif experiment["experiment_id"] == "routing_main":
        aggregate_path = aggregate_output_path(experiment, "routing_support.csv")
        table_path = table_output_path(experiment, "routing_support_table.csv")
    else:
        aggregate_path = aggregate_output_path(experiment, "main_success_overhead.csv")
        table_path = table_output_path(experiment, "main_success_overhead_table.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    if table_path != aggregate_path:
        write_csv(table_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
