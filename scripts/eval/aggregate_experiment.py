"""Aggregate query metrics for a HiRoute experiment."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from statistics import fmean
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


OUTPUT_FIELDS = [
    "experiment_id",
    "scheme",
    "run_count",
    "mean_success_at_1",
    "mean_manifest_hit_at_5",
    "mean_ndcg_at_5",
    "mean_num_remote_probes",
    "mean_discovery_bytes",
    "mean_latency_ms",
    "source_run_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def _read_registry(experiment_id: str, source: str) -> list[dict[str, str]]:
    filename = "promoted_runs.csv" if source == "promoted" else "runs.csv"
    path = repo_root() / "runs" / "registry" / filename
    return [row for row in read_csv(path) if row["experiment_id"] == experiment_id]


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(ROOT / args.experiment)
    run_rows = _read_registry(experiment["experiment_id"], args.registry_source)
    if not run_rows:
        print("ERROR: no registry rows available for aggregation")
        return 1

    grouped_logs: dict[str, list[dict[str, str]]] = defaultdict(list)
    grouped_run_ids: dict[str, list[str]] = defaultdict(list)
    for row in run_rows:
        query_log_path = repo_root() / row["run_dir"] / "query_log.csv"
        logs = read_csv(query_log_path)
        grouped_logs[row["scheme"]].extend(logs)
        grouped_run_ids[row["scheme"]].append(row["run_id"])

    output_rows = []
    for scheme in experiment["schemes"]:
        logs = grouped_logs.get(scheme, [])
        if not logs:
            continue
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                "scheme": scheme,
                "run_count": len(grouped_run_ids[scheme]),
                "mean_success_at_1": round(fmean(float(row["success_at_1"]) for row in logs), 6),
                "mean_manifest_hit_at_5": round(fmean(float(row["manifest_hit_at_5"]) for row in logs), 6),
                "mean_ndcg_at_5": round(fmean(float(row["ndcg_at_5"]) for row in logs), 6),
                "mean_num_remote_probes": round(fmean(float(row["num_remote_probes"]) for row in logs), 6),
                "mean_discovery_bytes": round(
                    fmean(float(row["discovery_tx_bytes"]) + float(row["discovery_rx_bytes"]) for row in logs), 6
                ),
                "mean_latency_ms": round(fmean(float(row["latency_ms"]) for row in logs), 6),
                "source_run_ids": "|".join(sorted(grouped_run_ids[scheme])),
            }
        )

    aggregate_path = repo_root() / "results" / "aggregate" / "main_success_overhead.csv"
    table_path = repo_root() / "results" / "tables" / "main_success_overhead_table.csv"
    write_csv(aggregate_path, OUTPUT_FIELDS, output_rows)
    write_csv(table_path, OUTPUT_FIELDS, output_rows)
    print(str(aggregate_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
