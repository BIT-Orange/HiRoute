"""Build Figure 10 ablation-style summary from canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import aggregate_output_path, load_experiment, log_frame, require_rows, sweep_field
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
    "first_fetch_relevant_rate",
    "manifest_rescue_rate",
    "mean_manifest_fetch_index_success_only",
    "wrong_object_rate",
    "mean_discovery_bytes",
    "mean_manifest_hit_at_5",
    "mean_latency_ms",
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

    active_sweep_field = sweep_field(experiment)
    frame = frame.copy()
    frame["success_at_1"] = frame["success_at_1"].astype(float)
    frame["first_fetch_relevant"] = frame.get("first_fetch_relevant", 0)
    frame["first_fetch_relevant"] = frame["first_fetch_relevant"].replace("", 0).astype(float)
    frame["manifest_fetch_index"] = frame.get("manifest_fetch_index", 0)
    frame["manifest_fetch_index"] = frame["manifest_fetch_index"].replace("", 0).astype(float)
    frame["manifest_rescue"] = ((frame["success_at_1"] == 1) & (frame["manifest_fetch_index"] > 0)).astype(float)
    frame["discovery_bytes_total"] = frame["discovery_tx_bytes"] + frame["discovery_rx_bytes"]
    output_rows = []
    for keys, group in frame.groupby(
        ["registry_scheme", "registry_topology_id", active_sweep_field], sort=False
    ):
        scheme, topology_id, sweep_value = keys
        run_ids = sorted(group["run_id"].unique().tolist())
        budget = int(sweep_value) if active_sweep_field == "budget" else int(group["budget"].max())
        manifest_size = int(sweep_value) if active_sweep_field == "manifest_size" else int(group["manifest_size"].max())
        wrong_object_rate = (group["failure_type"] == "wrong_object").mean()
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
                "first_fetch_relevant_rate": round(group["first_fetch_relevant"].mean(), 6),
                "manifest_rescue_rate": round(group["manifest_rescue"].mean(), 6),
                "mean_manifest_fetch_index_success_only": round(
                    group.loc[group["success_at_1"] == 1, "manifest_fetch_index"].mean()
                    if (group["success_at_1"] == 1).any()
                    else 0.0,
                    6,
                ),
                "wrong_object_rate": round(float(wrong_object_rate), 6),
                "mean_discovery_bytes": round(group["discovery_bytes_total"].mean(), 6),
                "mean_manifest_hit_at_5": round(group["manifest_hit_at_5"].mean(), 6),
                "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                "source_run_ids": "|".join(run_ids),
            }
        )

    aggregate_path = aggregate_output_path(experiment, "ablation_summary.csv")
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(Path.cwd())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
