"""Build Figure 9 robustness aggregates from staleness/failure experiments."""

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
    load_experiment,
    log_frame,
    read_manifest,
    require_rows,
)
from tools.workflow_support import write_csv


SUMMARY_FIELDS = [
    "experiment_id",
    "scenario_variant",
    "scheme",
    "topology_id",
    "pre_event_success",
    "min_success_after_event",
    "t95_recovery_sec",
    "extra_probes_during_recovery",
    "area_under_degradation_curve",
]

TIMESERIES_FIELDS = [
    "experiment_id",
    "scenario_variant",
    "scheme",
    "topology_id",
    "time_bin_s",
    "query_count",
    "success_at_1_rate",
    "mean_remote_probes",
    "mean_discovery_bytes",
]

ROBUSTNESS_EXPERIMENTS = {
    "exp_staleness_v1": ["exp_staleness_v1", "exp_failures_v1"],
    "exp_failures_v1": ["exp_staleness_v1", "exp_failures_v1"],
    "exp_robustness_v3": ["exp_robustness_v3"],
    "exp_robustness_v3_compact": ["exp_robustness_v3_compact"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def _recovery_metrics(group: pd.DataFrame, pre_event_success: float, failure_time_s: float) -> tuple[float, float, float]:
    post = group[group["time_bin_s"] >= failure_time_s].copy()
    if post.empty:
        return pre_event_success, 0.0, 0.0
    min_success = float(post["success_at_1_rate"].min())
    if pre_event_success <= 0:
        return min_success, 0.0, 0.0

    target = pre_event_success * 0.95
    recovered = post[post["success_at_1_rate"] >= target].sort_values("time_bin_s")
    t95 = 0.0 if recovered.empty else float(recovered.iloc[0]["time_bin_s"] - failure_time_s)
    degradation = (pre_event_success - post["success_at_1_rate"]).clip(lower=0.0)
    area = float(degradation.sum())
    return min_success, t95, area


def main() -> int:
    args = parse_args()
    experiment = load_experiment(args.experiment)
    experiment_ids = ROBUSTNESS_EXPERIMENTS.get(experiment["experiment_id"], [experiment["experiment_id"]])

    rows = []
    for experiment_id in experiment_ids:
        companion_path = ROOT / "configs" / "experiments" / f"{experiment_id}.yaml"
        companion = load_experiment(companion_path)
        rows.extend(require_rows(companion, args.registry_source))

    query_frame = log_frame(rows, "query_log.csv")
    if query_frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    query_frame["discovery_bytes_total"] = (
        query_frame["discovery_tx_bytes"].astype(float) + query_frame["discovery_rx_bytes"].astype(float)
    )
    query_frame["time_s"] = (query_frame["end_time_ms"].astype(float) / 1000.0).fillna(0.0)
    query_frame["time_bin_s"] = query_frame["time_s"].floordiv(1.0).astype(int)
    query_frame["num_remote_probes"] = query_frame["num_remote_probes"].astype(float)
    query_frame["success_at_1"] = query_frame["success_at_1"].astype(float)

    manifest_by_run = {row["run_id"]: read_manifest(row) for row in rows}
    timeseries_rows = []
    summary_rows = []

    grouped = query_frame.groupby(["scenario_variant", "registry_scheme", "registry_topology_id"], sort=False)
    for (scenario_variant, scheme, topology_id), group in grouped:
        bins = (
            group.groupby(["run_id", "time_bin_s"], as_index=False)
            .agg(
                query_count=("query_id", "count"),
                success_at_1_rate=("success_at_1", "mean"),
                mean_remote_probes=("num_remote_probes", "mean"),
                mean_discovery_bytes=("discovery_bytes_total", "mean"),
            )
        )
        aggregated_bins = (
            bins.groupby("time_bin_s", as_index=False)
            .agg(
                query_count=("query_count", "sum"),
                success_at_1_rate=("success_at_1_rate", "mean"),
                mean_remote_probes=("mean_remote_probes", "mean"),
                mean_discovery_bytes=("mean_discovery_bytes", "mean"),
            )
            .sort_values("time_bin_s")
        )
        for _, row in aggregated_bins.iterrows():
            timeseries_rows.append(
                {
                    "experiment_id": experiment["experiment_id"],
                    "scenario_variant": scenario_variant,
                    "scheme": scheme,
                    "topology_id": topology_id,
                    "time_bin_s": int(row["time_bin_s"]),
                    "query_count": int(row["query_count"]),
                    "success_at_1_rate": round(float(row["success_at_1_rate"]), 6),
                    "mean_remote_probes": round(float(row["mean_remote_probes"]), 6),
                    "mean_discovery_bytes": round(float(row["mean_discovery_bytes"]), 6),
                }
            )

        failure_times = []
        recovery_times = []
        for run_id in group["run_id"].unique():
            manifest = manifest_by_run.get(run_id, {})
            runner_params = manifest.get("runner_params", {}) if isinstance(manifest, dict) else {}
            failure_times.append(float(runner_params.get("failureTime") or 0.0))
            recovery_times.append(float(runner_params.get("recoveryTime") or 0.0))
        failure_time_s = sum(failure_times) / len(failure_times) if failure_times else 0.0
        recovery_time_s = sum(recovery_times) / len(recovery_times) if recovery_times else failure_time_s

        pre = aggregated_bins[aggregated_bins["time_bin_s"] < failure_time_s]
        pre_event_success = float(pre["success_at_1_rate"].mean()) if not pre.empty else float(
            aggregated_bins["success_at_1_rate"].mean()
        )
        min_success_after_event, t95_recovery_sec, area_under_degradation_curve = _recovery_metrics(
            aggregated_bins,
            pre_event_success,
            failure_time_s,
        )
        recovery_window = aggregated_bins[
            (aggregated_bins["time_bin_s"] >= failure_time_s) &
            (aggregated_bins["time_bin_s"] <= max(recovery_time_s, failure_time_s + t95_recovery_sec))
        ]
        pre_probe_mean = float(pre["mean_remote_probes"].mean()) if not pre.empty else 0.0
        recovery_probe_mean = (
            float(recovery_window["mean_remote_probes"].mean()) if not recovery_window.empty else pre_probe_mean
        )
        extra_probes_during_recovery = recovery_probe_mean - pre_probe_mean

        summary_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scenario_variant": scenario_variant,
                "scheme": scheme,
                "topology_id": topology_id,
                "pre_event_success": round(pre_event_success, 6),
                "min_success_after_event": round(min_success_after_event, 6),
                "t95_recovery_sec": round(t95_recovery_sec, 6),
                "extra_probes_during_recovery": round(extra_probes_during_recovery, 6),
                "area_under_degradation_curve": round(area_under_degradation_curve, 6),
            }
        )

    summary_path = aggregate_output_path(experiment, "robustness_summary.csv")
    timeseries_path = aggregate_output_path(experiment, "robustness_timeseries.csv")
    write_csv(summary_path, SUMMARY_FIELDS, summary_rows)
    write_csv(timeseries_path, TIMESERIES_FIELDS, timeseries_rows)
    print(str(summary_path.relative_to(ROOT)))
    print(str(timeseries_path.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
