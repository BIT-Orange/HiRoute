"""Build stage-local quick summaries and gating decisions for mainline rerun stages."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


OBJECT_MAIN_FIELDS = [
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
    "failure_rate_wrong_domain",
    "failure_rate_wrong_object",
    "failure_rate_predicate_miss",
    "mean_discovery_bytes",
    "mean_probe_count",
    "source_run_ids",
]

ABLATION_FIELDS = [
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
    "failure_rate_wrong_domain",
    "failure_rate_wrong_object",
    "failure_rate_predicate_miss",
    "mean_discovery_bytes",
    "mean_probe_count",
    "source_run_ids",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--run-ids-file", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--decision-json", required=True, type=Path)
    parser.add_argument("--stage", required=True)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _load_run_rows(run_ids_file: Path) -> list[dict[str, str]]:
    requested = [line.strip() for line in _resolve(run_ids_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not requested:
        raise RuntimeError("run ids file is empty")
    requested_set = set(requested)
    rows = []
    for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv"):
        if row["run_id"] in requested_set:
            rows.append(row)
    if {row["run_id"] for row in rows} != requested_set:
        missing = sorted(requested_set - {row["run_id"] for row in rows})
        raise RuntimeError(f"run ids file references runs missing from runs.csv: {missing}")
    return rows


def _collect_query_rows(run_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    query_rows: list[dict[str, Any]] = []
    for run_row in run_rows:
        run_dir = repo_root() / run_row["run_dir"]
        for row in read_csv(run_dir / "query_log.csv"):
            query_rows.append(
                {
                    "run_id": run_row["run_id"],
                    "scheme": run_row["scheme"],
                    "topology_id": run_row["topology_id"],
                    "budget": int(run_row.get("budget") or 0),
                    "manifest_size": int(run_row.get("manifest_size") or 0),
                    "success_at_1": float(row.get("success_at_1") or 0),
                    "first_fetch_relevant": float(row.get("first_fetch_relevant") or 0),
                    "manifest_fetch_index": float(row.get("manifest_fetch_index") or 0),
                    "failure_type": row.get("failure_type", ""),
                    "discovery_bytes_total": float(row.get("discovery_tx_bytes") or 0)
                    + float(row.get("discovery_rx_bytes") or 0),
                    "probe_count": float(row.get("num_remote_probes") or 0),
                }
            )
    return query_rows


def _group_rows(query_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in query_rows:
        grouped[(row["scheme"], row["topology_id"], row["manifest_size"])].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (scheme, topology_id, manifest_size), rows in sorted(grouped.items()):
        run_ids = sorted({row["run_id"] for row in rows})
        query_count = len(rows)
        summary_rows.append(
            {
                "scheme": scheme,
                "topology_id": topology_id,
                "budget": max(int(row["budget"]) for row in rows),
                "manifest_size": manifest_size,
                "run_count": len(run_ids),
                "query_count": query_count,
                "mean_success_at_1": round(sum(row["success_at_1"] for row in rows) / query_count, 6),
                "first_fetch_relevant_rate": round(
                    sum(row["first_fetch_relevant"] for row in rows) / query_count,
                    6,
                ),
                "manifest_rescue_rate": round(
                    sum(1 for row in rows if row["success_at_1"] == 1 and row["manifest_fetch_index"] > 0)
                    / query_count,
                    6,
                ),
                "mean_manifest_fetch_index_success_only": round(
                    (
                        sum(row["manifest_fetch_index"] for row in rows if row["success_at_1"] == 1)
                        / sum(1 for row in rows if row["success_at_1"] == 1)
                    )
                    if any(row["success_at_1"] == 1 for row in rows)
                    else 0.0,
                    6,
                ),
                "failure_rate_wrong_domain": round(
                    sum(1 for row in rows if row["failure_type"] == "wrong_domain") / query_count, 6
                ),
                "failure_rate_wrong_object": round(
                    sum(1 for row in rows if row["failure_type"] == "wrong_object") / query_count, 6
                ),
                "failure_rate_predicate_miss": round(
                    sum(1 for row in rows if row["failure_type"] == "predicate_miss") / query_count, 6
                ),
                "mean_discovery_bytes": round(
                    sum(row["discovery_bytes_total"] for row in rows) / query_count,
                    6,
                ),
                "mean_probe_count": round(sum(row["probe_count"] for row in rows) / query_count, 6),
                "source_run_ids": "|".join(run_ids),
            }
        )
    return summary_rows


def _row_index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    index = {}
    for row in rows:
        index[(str(row["scheme"]), int(row["manifest_size"]))] = row
    return index


def _total_key_failure_rate(row: dict[str, Any]) -> float:
    return (
        float(row["failure_rate_wrong_domain"])
        + float(row["failure_rate_wrong_object"])
        + float(row["failure_rate_predicate_miss"])
    )


def _has_useful_separation(reference: dict[str, Any], baseline: dict[str, Any]) -> bool:
    success_gap = float(reference["mean_success_at_1"]) - float(baseline["mean_success_at_1"])
    failure_gap = _total_key_failure_rate(baseline) - _total_key_failure_rate(reference)
    if success_gap >= 0.02 or failure_gap >= 0.02:
        return True

    if abs(success_gap) <= 0.02:
        ref_bytes = float(reference["mean_discovery_bytes"])
        base_bytes = float(baseline["mean_discovery_bytes"])
        bytes_gain = ((base_bytes - ref_bytes) / base_bytes) if base_bytes > 0 else 0.0
        probe_gap = float(baseline["mean_probe_count"]) - float(reference["mean_probe_count"])
        if bytes_gain >= 0.10 or probe_gap >= 0.5:
            return True
    return False


def _has_route_b_object_signal(reference: dict[str, Any], baseline: dict[str, Any]) -> bool:
    first_fetch_gap = float(reference["first_fetch_relevant_rate"]) - float(baseline["first_fetch_relevant_rate"])
    rescue_gap = float(reference["manifest_rescue_rate"]) - float(baseline["manifest_rescue_rate"])
    first_choice_gap = float(reference["mean_success_at_1"]) - float(reference["first_fetch_relevant_rate"])
    return first_fetch_gap >= 0.02 or rescue_gap >= 0.02 or first_choice_gap >= 0.02


def _object_main_decision(rows: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    index = _row_index(rows)
    required_keys = [
        ("hiroute", 1),
        ("hiroute", 2),
        ("hiroute", 3),
        ("inf_tag_forwarding", 1),
        ("central_directory", 1),
    ]
    missing = [f"{scheme}@manifest{manifest}" for scheme, manifest in required_keys if (scheme, manifest) not in index]
    if missing:
        return "stop_object_regressed", {"reason": "missing_rows", "missing": missing}

    hiroute_sweep = [index[("hiroute", manifest)] for manifest in (1, 2, 3)]
    monotonic = all(
        float(hiroute_sweep[i]["mean_success_at_1"]) <= float(hiroute_sweep[i + 1]["mean_success_at_1"]) + 1e-9
        for i in range(len(hiroute_sweep) - 1)
    )
    central_ok = float(index[("central_directory", 1)]["mean_success_at_1"]) >= 0.99
    hiroute_m1 = index[("hiroute", 1)]
    inf_m1 = index[("inf_tag_forwarding", 1)]

    if not monotonic:
        return "stop_object_regressed", {"reason": "hiroute_manifest_not_monotonic"}
    if not central_ok:
        return "stop_object_regressed", {"reason": "central_directory_failed_sanity"}
    if (
        float(hiroute_m1["mean_success_at_1"]) <= float(inf_m1["mean_success_at_1"]) - 0.05
    ):
        return "stop_object_regressed", {"reason": "hiroute_loses_to_distributed_baseline"}

    separated = {
        "inf_tag_forwarding": _has_useful_separation(hiroute_m1, inf_m1)
        or _has_route_b_object_signal(hiroute_m1, inf_m1),
    }
    distributed_rows = [hiroute_m1, inf_m1, index[("central_directory", 1)]]
    all_high_success = all(float(row["mean_success_at_1"]) >= 0.99 for row in distributed_rows)
    hiroute_support_signal = any(
        float(row["manifest_rescue_rate"]) >= 0.02
        or (float(row["mean_success_at_1"]) - float(row["first_fetch_relevant_rate"])) >= 0.02
        for row in hiroute_sweep
    )

    if any(separated.values()) or hiroute_support_signal:
        return "proceed_full_object_main", {
            "reason": "route_b_support_signal" if hiroute_support_signal and not any(separated.values()) else "useful_separation",
            "separation": separated,
            "hiroute_support_signal": hiroute_support_signal,
        }
    if all_high_success:
        return "stop_workload_saturated", {
            "reason": "all_manifest1_success_high",
            "separation": separated,
            "hiroute_support_signal": hiroute_support_signal,
        }
    return "stop_workload_saturated", {
        "reason": "no_useful_separation",
        "separation": separated,
        "hiroute_support_signal": hiroute_support_signal,
    }


def _ablation_decision(rows: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    index = _row_index(rows)
    required_keys = [
        ("predicates_only", 1),
        ("flat_semantic_only", 1),
        ("predicates_plus_flat", 1),
        ("full_hiroute", 1),
    ]
    missing = [f"{scheme}@manifest{manifest}" for scheme, manifest in required_keys if (scheme, manifest) not in index]
    if missing:
        return "stop_ablation_signal_collapsed", {"reason": "missing_rows", "missing": missing}

    full = index[("full_hiroute", 1)]
    predicate_plus_flat = index[("predicates_plus_flat", 1)]
    predicate_only = index[("predicates_only", 1)]
    flat_only = index[("flat_semantic_only", 1)]

    if float(full["mean_success_at_1"]) <= float(predicate_plus_flat["mean_success_at_1"]) - 0.05:
        return "stop_ablation_signal_collapsed", {"reason": "full_hiroute_underperforms_predicates_plus_flat"}

    separated = {
        "predicates_plus_flat": _has_useful_separation(full, predicate_plus_flat),
        "predicates_only": _has_useful_separation(full, predicate_only),
        "flat_semantic_only": _has_useful_separation(full, flat_only),
    }
    all_high_success = all(
        float(index[key]["mean_success_at_1"]) >= 0.99
        for key in required_keys
    )
    if separated["predicates_plus_flat"] or separated["predicates_only"] or separated["flat_semantic_only"]:
        return "proceed_full_ablation", {"reason": "useful_separation", "separation": separated}
    if all_high_success:
        return "stop_ablation_signal_collapsed", {"reason": "all_manifest1_success_high", "separation": separated}
    return "stop_ablation_signal_collapsed", {"reason": "no_useful_separation", "separation": separated}


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(_resolve(args.experiment))
    run_rows = _load_run_rows(args.run_ids_file)
    query_rows = _collect_query_rows(run_rows)
    if not query_rows:
        print("ERROR: no query rows available for quick summary")
        return 1

    summary_rows = _group_rows(query_rows)
    fields = OBJECT_MAIN_FIELDS if experiment["experiment_id"] == "object_main" else ABLATION_FIELDS
    output_rows = []
    for row in summary_rows:
        output_rows.append(
            {
                "experiment_id": experiment["experiment_id"],
                **row,
            }
        )
    write_csv(_resolve(args.output_csv), fields, output_rows)

    if args.stage == "object_main_quick":
        decision, detail = _object_main_decision(output_rows)
        representative_run = next(
            (
                row["source_run_ids"].split("|")[0]
                for row in output_rows
                if row["scheme"] == "hiroute" and int(row["manifest_size"]) == 1
            ),
            "",
        )
    elif args.stage == "ablation_quick":
        decision, detail = _ablation_decision(output_rows)
        representative_run = next(
            (
                row["source_run_ids"].split("|")[0]
                for row in output_rows
                if row["scheme"] == "full_hiroute" and int(row["manifest_size"]) == 1
            ),
            "",
        )
    elif args.stage == "object_main":
        decision, detail = _object_main_decision(output_rows)
        representative_run = next(
            (
                row["source_run_ids"].split("|")[0]
                for row in output_rows
                if row["scheme"] == "hiroute" and int(row["manifest_size"]) == 1
            ),
            "",
        )
    else:
        decision = "completed"
        detail = {"reason": "no_stage_specific_gate"}
        representative_run = ""

    payload = {
        "stage": args.stage,
        "experiment_id": experiment["experiment_id"],
        "decision": decision,
        "detail": detail,
        "representative_run": representative_run,
        "summary_csv": str(_resolve(args.output_csv).relative_to(repo_root())),
        "row_count": len(output_rows),
    }
    decision_path = _resolve(args.decision_json)
    decision_path.parent.mkdir(parents=True, exist_ok=True)
    decision_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
