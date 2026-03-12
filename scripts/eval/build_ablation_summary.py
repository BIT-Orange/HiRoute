"""Build Figure 10 ablation-style summary from canonical query logs."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval.eval_support import load_experiment, log_frame, require_rows
from tools.workflow_support import repo_root, write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "topology_id",
    "mean_success_at_1",
    "success_before_200ms_rate",
    "mean_latency_ms",
    "mean_discovery_bytes",
    "mean_manifest_hit_at_5",
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

    frame["discovery_bytes_total"] = frame["discovery_tx_bytes"] + frame["discovery_rx_bytes"]
    output_rows = []
    for (scheme, topology_id), group in frame.groupby(["registry_scheme", "registry_topology_id"], sort=False):
        deadline_hits = ((group["success_at_1"] == 1) & (group["latency_ms"] <= 200)).mean()
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "topology_id": topology_id,
                "mean_success_at_1": round(group["success_at_1"].mean(), 6),
                "success_before_200ms_rate": round(float(deadline_hits), 6),
                "mean_latency_ms": round(group["latency_ms"].mean(), 6),
                "mean_discovery_bytes": round(group["discovery_bytes_total"].mean(), 6),
                "mean_manifest_hit_at_5": round(group["manifest_hit_at_5"].mean(), 6),
            }
        )

    aggregate_path = repo_root() / "results" / "aggregate" / "ablation_summary.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
