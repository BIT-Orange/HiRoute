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
    "ci_success_at_1",
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
    frame["discovery_bytes_total"] = frame["discovery_tx_bytes"] + frame["discovery_rx_bytes"]
    frame["manifest_rescue"] = ((frame["manifest_hit_at_5"] == 1) & (frame["success_at_1"] == 0)).astype(float)

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
        frame["relevant_domain_reached_at_1"] = 0.0
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
                "ci_success_at_1": round(
                    bootstrap_mean_ci(group["success_at_1"], bootstrap_replicates), 6
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
                "effective_exported_summaries_total": round(sum(state_totals) / len(state_totals), 6) if state_totals else 0.0,
                "effective_exported_summaries_per_domain_mean": round(sum(state_per_domain) / len(state_per_domain), 6) if state_per_domain else 0.0,
                "source_run_ids": "|".join(run_ids),
            }
        )

    if experiment["experiment_id"] in {"exp_sanity_appendix_v2", "exp_sanity_appendix_v3"}:
        aggregate_path = table_output_path(experiment, "appendix_sanity_success_overhead.csv")
        table_path = aggregate_path
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
