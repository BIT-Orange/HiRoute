"""Build Figure 5 manifest-sweep summary from canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import (
    aggregate_output_path,
    bootstrap_mean_ci,
    load_experiment,
    log_frame,
    require_rows,
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
    "final_end_to_end_success_rate",
    "ci_success_at_1",
    "first_fetch_relevant_rate",
    "first_manifest_top1_correct_rate",
    "ci_first_fetch_relevant_rate",
    "manifest_rescue_rate",
    "ci_manifest_rescue_rate",
    "within_reply_manifest_rescue_rate",
    "ci_within_reply_manifest_rescue_rate",
    "cross_probe_manifest_rescue_rate",
    "ci_cross_probe_manifest_rescue_rate",
    "mean_manifest_fetch_index_success_only",
    "mean_manifest_rescue_rank_success_only",
    "mean_cumulative_manifest_fetches_success_only",
    "first_probe_relevant_domain_hit_rate",
    "mean_first_probe_domain_rank",
    "domain_selection_failure_rate",
    "local_resolution_failure_rate",
    "fetch_failure_rate",
    "mean_num_relevant_domains",
    "mean_num_confuser_domains",
    "mean_num_confuser_objects",
    "wrong_object_rate",
    "ci_wrong_object_rate",
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
    if frame.empty:
        print("ERROR: no canonical query logs found")
        return 1

    bootstrap_replicates = int(experiment.get("statistics", {}).get("bootstrap_replicates", 1000))

    frame = frame.copy()
    frame["success_at_1"] = frame["success_at_1"].astype(float)
    frame["first_fetch_relevant"] = frame.get("first_fetch_relevant", 0)
    frame["first_fetch_relevant"] = frame["first_fetch_relevant"].replace("", 0).astype(float)
    frame["manifest_fetch_index"] = frame.get("manifest_fetch_index", 0)
    frame["manifest_fetch_index"] = frame["manifest_fetch_index"].replace("", 0).astype(float)
    frame["first_probe_relevant_domain_hit"] = frame.get("first_probe_relevant_domain_hit", 0)
    frame["first_probe_relevant_domain_hit"] = (
        frame["first_probe_relevant_domain_hit"].replace("", 0).astype(float)
    )
    frame["first_probe_domain_rank"] = frame.get("first_probe_domain_rank", 0)
    frame["first_probe_domain_rank"] = frame["first_probe_domain_rank"].replace("", 0).astype(float)
    frame["num_relevant_domains"] = frame.get("num_relevant_domains", 0)
    frame["num_relevant_domains"] = frame["num_relevant_domains"].replace("", 0).astype(float)
    frame["num_confuser_domains"] = frame.get("num_confuser_domains", 0)
    frame["num_confuser_domains"] = frame["num_confuser_domains"].replace("", 0).astype(float)
    frame["num_confuser_objects"] = frame.get("num_confuser_objects", 0)
    frame["num_confuser_objects"] = frame["num_confuser_objects"].replace("", 0).astype(float)
    frame["cumulative_manifest_fetches"] = frame.get("cumulative_manifest_fetches", 0)
    frame["cumulative_manifest_fetches"] = (
        frame["cumulative_manifest_fetches"].replace("", 0).astype(float)
    )
    frame["wrong_object_indicator"] = (frame["failure_type"] == "wrong_object").astype(float)
    failure_stage = frame.get("failure_stage", "")
    if isinstance(failure_stage, str):
        failure_stage = frame["failure_type"].astype(str).map(lambda _value: "")
    frame["domain_selection_failure"] = (failure_stage == "domain_selection").astype(float)
    frame["local_resolution_failure"] = (failure_stage == "local_resolution").astype(float)
    frame["fetch_failure"] = (failure_stage == "fetch").astype(float)
    # Phase 2 rescue split (see docs/metrics/metric_semantics.md). Legacy manifest_rescue
    # kept in outputs for one release cycle; equals within_reply_manifest_rescue by design.
    frame["within_reply_manifest_rescue"] = (
        (frame["success_at_1"] == 1) & (frame["manifest_fetch_index"] > 0)
    ).astype(float)
    frame["cross_probe_manifest_rescue"] = (
        (frame["success_at_1"] == 1)
        & (frame["cumulative_manifest_fetches"] > 0)
        & (frame["manifest_fetch_index"] == 0)
    ).astype(float)
    frame["manifest_rescue"] = frame["within_reply_manifest_rescue"]

    output_rows = []
    for keys, group in frame.groupby(
        ["registry_scheme", "registry_topology_id", "manifest_size"], sort=False
    ):
        scheme, topology_id, manifest_size = keys
        run_ids = sorted(group["run_id"].unique().tolist())
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "budget": int(group["budget"].max()),
                "manifest_size": int(manifest_size),
                "run_count": len(run_ids),
                "query_count": int(len(group)),
                "mean_success_at_1": round(group["success_at_1"].mean(), 6),
                "final_end_to_end_success_rate": round(group["success_at_1"].mean(), 6),
                "ci_success_at_1": round(
                    bootstrap_mean_ci(group["success_at_1"], bootstrap_replicates, seed=10), 6
                ),
                "first_fetch_relevant_rate": round(group["first_fetch_relevant"].mean(), 6),
                "first_manifest_top1_correct_rate": round(group["first_fetch_relevant"].mean(), 6),
                "ci_first_fetch_relevant_rate": round(
                    bootstrap_mean_ci(group["first_fetch_relevant"], bootstrap_replicates, seed=13), 6
                ),
                "manifest_rescue_rate": round(group["manifest_rescue"].mean(), 6),
                "ci_manifest_rescue_rate": round(
                    bootstrap_mean_ci(group["manifest_rescue"], bootstrap_replicates, seed=14), 6
                ),
                "within_reply_manifest_rescue_rate": round(
                    group["within_reply_manifest_rescue"].mean(), 6
                ),
                "ci_within_reply_manifest_rescue_rate": round(
                    bootstrap_mean_ci(
                        group["within_reply_manifest_rescue"], bootstrap_replicates, seed=24
                    ),
                    6,
                ),
                "cross_probe_manifest_rescue_rate": round(
                    group["cross_probe_manifest_rescue"].mean(), 6
                ),
                "ci_cross_probe_manifest_rescue_rate": round(
                    bootstrap_mean_ci(
                        group["cross_probe_manifest_rescue"], bootstrap_replicates, seed=25
                    ),
                    6,
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
                "domain_selection_failure_rate": round(
                    group["domain_selection_failure"].mean(), 6
                ),
                "local_resolution_failure_rate": round(
                    group["local_resolution_failure"].mean(), 6
                ),
                "fetch_failure_rate": round(group["fetch_failure"].mean(), 6),
                "mean_num_relevant_domains": round(group["num_relevant_domains"].mean(), 6),
                "mean_num_confuser_domains": round(group["num_confuser_domains"].mean(), 6),
                "mean_num_confuser_objects": round(group["num_confuser_objects"].mean(), 6),
                "wrong_object_rate": round(group["wrong_object_indicator"].mean(), 6),
                "ci_wrong_object_rate": round(
                    bootstrap_mean_ci(group["wrong_object_indicator"], bootstrap_replicates, seed=11), 6
                ),
                "source_run_ids": "|".join(run_ids),
            }
        )

    aggregate_path = aggregate_output_path(experiment, "object_main_manifest_sweep.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
