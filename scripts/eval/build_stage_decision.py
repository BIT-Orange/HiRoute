"""Build full-stage decisions for mainline experiments without touching paper-facing figures."""

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

from tools.workflow_support import load_json_yaml, read_csv, repo_root


SUCCESS_TOLERANCE = 0.02
FAILURE_TOLERANCE = 0.02
BYTES_ADVANTAGE_THRESHOLD = 0.10
PROBE_ADVANTAGE_THRESHOLD = 0.5
ABLATION_MAIN_MANIFEST_SIZE = 1
ABLATION_HEADLINE_SUCCESS_GAP = 0.10
EPSILON = 1e-9


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--run-ids-file", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--wiring-report", type=Path)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    resolved = _resolve(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def _load_run_rows(run_ids_file: Path) -> list[dict[str, str]]:
    requested = [line.strip() for line in _resolve(run_ids_file).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not requested:
        raise RuntimeError("run ids file is empty")
    requested_set = set(requested)
    rows = [row for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv") if row["run_id"] in requested_set]
    missing = sorted(requested_set - {row["run_id"] for row in rows})
    if missing:
        raise RuntimeError(f"run ids file references runs missing from runs.csv: {missing}")
    return rows


def _split_source_run_ids(raw_value: str) -> set[str]:
    return {value for value in str(raw_value).split("|") if value}


def _as_int(raw_value: Any) -> int:
    try:
        return int(float(raw_value))
    except (TypeError, ValueError):
        return 0


def _as_float(raw_value: Any) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return 0.0


def _discovery_matrix_path(experiment: dict[str, Any]) -> Path:
    matrix_filenames = {
        "discovery_reply_stage_matrix.csv",
        f"{experiment.get('experiment_id', '')}_discovery_reply_stage_matrix.csv",
    }
    for output in experiment.get("outputs", []):
        output_path = _resolve(Path(str(output)))
        if output_path.name in matrix_filenames:
            return output_path
    return repo_root() / "results" / "aggregate" / "mainline" / f"{experiment['experiment_id']}_discovery_reply_stage_matrix.csv"


def _discovery_reply_stage_digest(
    experiment: dict[str, Any],
    source_run_ids: list[str],
) -> dict[str, Any]:
    matrix_path = _discovery_matrix_path(experiment)
    try:
        matrix_relpath = str(matrix_path.relative_to(repo_root()))
    except ValueError:
        matrix_relpath = str(matrix_path)

    digest: dict[str, Any] = {
        "matrix_csv": matrix_relpath,
        "matrix_exists": matrix_path.exists(),
        "scoped_row_count": 0,
        "legacy_inferred_row_count": 0,
        "legacy_inferred_count_sum": 0,
        "legacy_inferred_rate_sum": 0.0,
        "top_reason_rows": [],
    }
    if not matrix_path.exists():
        return digest

    stage_run_ids = set(source_run_ids)
    scoped_rows: list[dict[str, str]] = []
    for row in read_csv(matrix_path):
        row_run_ids = _split_source_run_ids(row.get("source_run_ids", ""))
        if row_run_ids and row_run_ids.issubset(stage_run_ids):
            scoped_rows.append(row)

    digest["scoped_row_count"] = len(scoped_rows)
    if not scoped_rows:
        return digest

    legacy_rows = [
        row
        for row in scoped_rows
        if str(row.get("reply_reason_code", "")).strip().lower() == "legacy_inferred"
    ]
    digest["legacy_inferred_row_count"] = len(legacy_rows)
    digest["legacy_inferred_count_sum"] = sum(_as_int(row.get("count", 0)) for row in legacy_rows)
    digest["legacy_inferred_rate_sum"] = round(
        sum(_as_float(row.get("rate", 0.0)) for row in legacy_rows),
        6,
    )

    ranked = sorted(
        scoped_rows,
        key=lambda row: _as_int(row.get("count", 0)),
        reverse=True,
    )[:6]
    digest["top_reason_rows"] = [
        {
            "failure_stage": row.get("failure_stage", ""),
            "reply_status": row.get("reply_status", ""),
            "reply_reason_code": row.get("reply_reason_code", ""),
            "count": _as_int(row.get("count", 0)),
            "rate": round(_as_float(row.get("rate", 0.0)), 6),
        }
        for row in ranked
    ]
    return digest


def _collect_query_rows(run_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    query_rows: list[dict[str, Any]] = []
    for run_row in run_rows:
        run_dir = repo_root() / run_row["run_dir"]
        for row in read_csv(run_dir / "query_log.csv"):
            query_rows.append(
                {
                    "run_id": run_row["run_id"],
                    "scheme": run_row["scheme"],
                    "manifest_size": int(run_row.get("manifest_size") or 0),
                    "success_at_1": float(row.get("success_at_1") or 0),
                    "terminal_loose_success": float(
                        row.get("terminal_loose_success") or row.get("success_at_1") or 0
                    ),
                    "first_fetch_relevant": float(row.get("first_fetch_relevant") or 0),
                    "first_fetch_loose_relevant": float(
                        row.get("first_fetch_loose_relevant") or row.get("first_fetch_relevant") or 0
                    ),
                    "manifest_fetch_index": float(row.get("manifest_fetch_index") or 0),
                    "cumulative_manifest_fetches": float(
                        row.get("cumulative_manifest_fetches") or 0
                    ),
                    "failure_type": row.get("failure_type", ""),
                    "discovery_bytes_total": float(row.get("discovery_tx_bytes") or 0)
                    + float(row.get("discovery_rx_bytes") or 0),
                    "probe_count": float(row.get("num_remote_probes") or 0),
                }
            )
    return query_rows


def _group_rows(query_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in query_rows:
        grouped[(str(row["scheme"]), int(row["manifest_size"]))].append(row)

    summary_rows: list[dict[str, Any]] = []
    for (scheme, manifest_size), rows in sorted(grouped.items()):
        run_ids = sorted({row["run_id"] for row in rows})
        query_count = len(rows)
        summary_rows.append(
            {
                "scheme": scheme,
                "manifest_size": manifest_size,
                "run_count": len(run_ids),
                "query_count": query_count,
                "mean_success_at_1": round(sum(row["success_at_1"] for row in rows) / query_count, 6),
                "terminal_strong_success_rate": round(
                    sum(row["success_at_1"] for row in rows) / query_count,
                    6,
                ),
                "terminal_loose_success_rate": round(
                    sum(row["terminal_loose_success"] for row in rows) / query_count,
                    6,
                ),
                "first_fetch_relevant_rate": round(
                    sum(row["first_fetch_relevant"] for row in rows) / query_count,
                    6,
                ),
                "first_fetch_strong_relevant_rate": round(
                    sum(row["first_fetch_relevant"] for row in rows) / query_count,
                    6,
                ),
                "first_fetch_loose_relevant_rate": round(
                    sum(row["first_fetch_loose_relevant"] for row in rows) / query_count,
                    6,
                ),
                "manifest_rescue_rate": round(
                    sum(1 for row in rows if row["success_at_1"] == 1 and row["manifest_fetch_index"] > 0)
                    / query_count,
                    6,
                ),
                "within_reply_manifest_rescue_rate": round(
                    sum(1 for row in rows if row["success_at_1"] == 1 and row["manifest_fetch_index"] > 0)
                    / query_count,
                    6,
                ),
                "cross_probe_manifest_rescue_rate": round(
                    sum(
                        1
                        for row in rows
                        if row["success_at_1"] == 1
                        and row["cumulative_manifest_fetches"] > 0
                        and row["manifest_fetch_index"] == 0
                    )
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
                    sum(1 for row in rows if row["failure_type"] == "wrong_domain") / query_count,
                    6,
                ),
                "failure_rate_wrong_object": round(
                    sum(1 for row in rows if row["failure_type"] == "wrong_object") / query_count,
                    6,
                ),
                "failure_rate_predicate_miss": round(
                    sum(1 for row in rows if row["failure_type"] == "predicate_miss") / query_count,
                    6,
                ),
                "mean_discovery_bytes": round(sum(row["discovery_bytes_total"] for row in rows) / query_count, 6),
                "mean_probe_count": round(sum(row["probe_count"] for row in rows) / query_count, 6),
                "source_run_ids": "|".join(run_ids),
            }
        )
    return summary_rows


def _row_index(rows: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    return {(str(row["scheme"]), int(row["manifest_size"])): row for row in rows}


def _total_failure_rate(row: dict[str, Any]) -> float:
    return (
        float(row["failure_rate_wrong_domain"])
        + float(row["failure_rate_wrong_object"])
        + float(row["failure_rate_predicate_miss"])
    )


def _terminal_strong_success(row: dict[str, Any]) -> float:
    return _as_float(row.get("terminal_strong_success_rate", row.get("mean_success_at_1", 0.0)))


def _first_fetch_strong_success(row: dict[str, Any]) -> float:
    return _as_float(
        row.get("first_fetch_strong_relevant_rate", row.get("first_fetch_relevant_rate", 0.0))
    )


def _matches_reference(candidate: dict[str, Any], reference: dict[str, Any]) -> bool:
    success_gap = abs(_terminal_strong_success(candidate) - _terminal_strong_success(reference))
    failure_gap = abs(_total_failure_rate(candidate) - _total_failure_rate(reference))
    return success_gap <= SUCCESS_TOLERANCE and failure_gap <= FAILURE_TOLERANCE


def _bytes_advantage(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    candidate_bytes = float(candidate["mean_discovery_bytes"])
    reference_bytes = float(reference["mean_discovery_bytes"])
    if candidate_bytes <= 0:
        return 0.0
    return (candidate_bytes - reference_bytes) / candidate_bytes


def _probe_advantage(reference: dict[str, Any], candidate: dict[str, Any]) -> float:
    return float(candidate["mean_probe_count"]) - float(reference["mean_probe_count"])


def _first_run_id(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    return next((run_id for run_id in str(row.get("source_run_ids", "")).split("|") if run_id), "")


def _failure_delta(better: dict[str, Any], worse: dict[str, Any]) -> float:
    return _total_failure_rate(worse) - _total_failure_rate(better)


def _success_delta(better: dict[str, Any], worse: dict[str, Any]) -> float:
    return _terminal_strong_success(better) - _terminal_strong_success(worse)


def _materially_better(better: dict[str, Any], worse: dict[str, Any]) -> bool:
    return _success_delta(better, worse) >= SUCCESS_TOLERANCE or _failure_delta(better, worse) >= FAILURE_TOLERANCE


def _metric_gap(a: float, b: float) -> float:
    return abs(a - b)


def _saturated_group(rows: list[dict[str, Any]]) -> bool:
    success_values = [_terminal_strong_success(row) for row in rows]
    failure_values = [_total_failure_rate(row) for row in rows]
    bytes_values = [float(row["mean_discovery_bytes"]) for row in rows]
    probe_values = [float(row["mean_probe_count"]) for row in rows]
    return (
        max(success_values) - min(success_values) <= SUCCESS_TOLERANCE
        and max(failure_values) - min(failure_values) <= FAILURE_TOLERANCE
        and (
            max(bytes_values) <= EPSILON
            or (max(bytes_values) - min(bytes_values)) / max(bytes_values) < BYTES_ADVANTAGE_THRESHOLD
        )
        and max(probe_values) - min(probe_values) < PROBE_ADVANTAGE_THRESHOLD
    )


def _strictly_non_decreasing(values: list[float]) -> bool:
    return all(values[i] <= values[i + 1] + EPSILON for i in range(len(values) - 1))


def _strictly_non_increasing(values: list[float]) -> bool:
    return all(values[i] >= values[i + 1] - EPSILON for i in range(len(values) - 1))


def _first_choice_gap(row: dict[str, Any]) -> float:
    return _terminal_strong_success(row) - _first_fetch_strong_success(row)


def _object_main_decision(
    rows: list[dict[str, Any]],
    wiring_report: dict[str, Any],
    discovery_digest: dict[str, Any],
) -> dict[str, Any]:
    index = _row_index(rows)
    required = [
        ("hiroute", 1),
        ("hiroute", 2),
        ("hiroute", 3),
        ("inf_tag_forwarding", 1),
        ("inf_tag_forwarding", 2),
        ("inf_tag_forwarding", 3),
        ("central_directory", 1),
        ("central_directory", 2),
        ("central_directory", 3),
    ]
    missing = [f"{scheme}@manifest{manifest}" for scheme, manifest in required if (scheme, manifest) not in index]
    if missing:
        return {
            "decision": "proceed_ablation_quick",
            "figure_guidance": [],
            "detail": {
                "reason": "missing_rows",
                "missing": missing,
                "hiroute_reaches_ceiling_at_manifest1": False,
                "oracle_lower_byte_upper_bound": False,
                "wiring_report_status": str(wiring_report.get("overall_status", "unknown")),
                "discovery_reply_stage_matrix_digest": discovery_digest,
                "baseline_details": {
                    "inf_tag_forwarding": {
                        "catch_up_manifest": 0,
                        "accuracy_gap_persists": True,
                        "residual_cost_gap": False,
                        "bytes_advantage_vs_hiroute_manifest1": 0.0,
                        "probe_advantage_vs_hiroute_manifest1": 0.0,
                    },
                },
            },
            "representative_runs": [],
            "recommend_next_stage": "ablation_quick",
            "figure_title_guidance": "needs ablation",
            "key_metrics_digest": rows,
        }

    hiroute_ref = index[("hiroute", 1)]
    inf_rows = [index[("inf_tag_forwarding", manifest)] for manifest in (1, 2, 3)]
    central_row = index[("central_directory", 1)]

    hiroute_ceiling = max(
        abs(_terminal_strong_success(row) - _terminal_strong_success(hiroute_ref))
        for row in (index[("hiroute", 2)], index[("hiroute", 3)])
    ) <= EPSILON

    baseline_details: dict[str, dict[str, Any]] = {}
    any_accuracy_gap_persists = False
    all_catch_up = True
    any_catch_up_requires_larger_manifest = False
    any_residual_cost_gap = False
    no_residual_cost_gap = True
    for scheme, scheme_rows in (("inf_tag_forwarding", inf_rows),):
        catch_up_manifest = 0
        matched_row: dict[str, Any] | None = None
        for row in scheme_rows:
            if _matches_reference(row, hiroute_ref):
                catch_up_manifest = int(row["manifest_size"])
                matched_row = row
                break
        accuracy_gap_persists = catch_up_manifest == 0
        if accuracy_gap_persists:
            any_accuracy_gap_persists = True
            all_catch_up = False
            bytes_advantage = _bytes_advantage(hiroute_ref, scheme_rows[-1])
            probe_advantage = _probe_advantage(hiroute_ref, scheme_rows[-1])
            residual_cost_gap = bytes_advantage >= BYTES_ADVANTAGE_THRESHOLD or probe_advantage >= PROBE_ADVANTAGE_THRESHOLD
            any_residual_cost_gap = any_residual_cost_gap or residual_cost_gap
            no_residual_cost_gap = False
        else:
            if catch_up_manifest > 1:
                any_catch_up_requires_larger_manifest = True
            assert matched_row is not None
            bytes_advantage = _bytes_advantage(hiroute_ref, matched_row)
            probe_advantage = _probe_advantage(hiroute_ref, matched_row)
            residual_cost_gap = bytes_advantage >= BYTES_ADVANTAGE_THRESHOLD or probe_advantage >= PROBE_ADVANTAGE_THRESHOLD
            any_residual_cost_gap = any_residual_cost_gap or residual_cost_gap
            no_residual_cost_gap = no_residual_cost_gap and (not residual_cost_gap)
        baseline_details[scheme] = {
            "catch_up_manifest": catch_up_manifest,
            "accuracy_gap_persists": accuracy_gap_persists,
            "residual_cost_gap": residual_cost_gap,
            "bytes_advantage_vs_hiroute_manifest1": round(bytes_advantage, 6),
            "probe_advantage_vs_hiroute_manifest1": round(probe_advantage, 6),
            "first_fetch_gap_vs_hiroute_manifest1": round(
                _first_fetch_strong_success(hiroute_ref) - _first_fetch_strong_success(scheme_rows[0]),
                6,
            ),
            "rescue_gap_vs_hiroute_manifest1": round(
                float(hiroute_ref["manifest_rescue_rate"]) - float(scheme_rows[0]["manifest_rescue_rate"]),
                6,
            ),
        }

    oracle_lower_byte_upper_bound = (
        _terminal_strong_success(central_row) >= 0.99
        and float(central_row["mean_discovery_bytes"]) <= float(hiroute_ref["mean_discovery_bytes"]) + EPSILON
        and float(central_row["mean_probe_count"]) <= float(hiroute_ref["mean_probe_count"]) + EPSILON
    )
    first_fetch_advantage = any(
        _first_fetch_strong_success(hiroute_ref) - _first_fetch_strong_success(row) >= SUCCESS_TOLERANCE
        for row in inf_rows
    )
    hiroute_support_gap = any(_first_choice_gap(index[("hiroute", manifest)]) >= SUCCESS_TOLERANCE for manifest in (1, 2, 3))
    # Phase 2: accept either within-reply or cross-probe rescue as a hiroute manifest signal.
    hiroute_manifest_rescue_signal = any(
        max(
            float(index[("hiroute", manifest)].get("within_reply_manifest_rescue_rate", 0.0)),
            float(index[("hiroute", manifest)].get("cross_probe_manifest_rescue_rate", 0.0)),
            float(index[("hiroute", manifest)]["manifest_rescue_rate"]),
        )
        >= SUCCESS_TOLERANCE
        for manifest in (1, 2, 3)
    )

    figure_guidance: list[str] = []
    if hiroute_ceiling:
        figure_guidance.append("hiroute_reaches_ceiling_at_manifest1")
    if any_catch_up_requires_larger_manifest:
        figure_guidance.append("flat_inf_catch_up_only_with_larger_manifest")
    if any_accuracy_gap_persists:
        figure_guidance.append("accuracy_gap_persists_at_manifest3")
    if any_residual_cost_gap:
        figure_guidance.append("residual_cost_gap_persists")
    if all_catch_up and no_residual_cost_gap:
        figure_guidance.append("distributed_methods_saturated")
    if oracle_lower_byte_upper_bound:
        figure_guidance.append("oracle_remains_lower_byte_upper_bound")
    if first_fetch_advantage:
        figure_guidance.append("first_fetch_advantage_persists")
    if hiroute_support_gap:
        figure_guidance.append("terminal_vs_first_fetch_gap_visible")
    if hiroute_manifest_rescue_signal:
        figure_guidance.append("manifest_rescue_signal_visible")

    if hiroute_manifest_rescue_signal and first_fetch_advantage and any_accuracy_gap_persists:
        decision = "ready_for_main_figure"
        figure_title_guidance = "manifest-backed object ranking"
    elif any_accuracy_gap_persists or first_fetch_advantage or hiroute_support_gap or hiroute_manifest_rescue_signal:
        decision = "support_only_figure"
        figure_title_guidance = "terminal vs first-fetch cautionary support"
    elif all_catch_up and any_catch_up_requires_larger_manifest and any_residual_cost_gap:
        decision = "cost_only_figure"
        figure_title_guidance = "manifest efficiency / cost separation"
    elif all_catch_up and no_residual_cost_gap:
        decision = "saturated_revisit_workload"
        figure_title_guidance = "revisit workload"
    else:
        decision = "proceed_ablation_quick"
        figure_title_guidance = "needs ablation"

    wiring_status = str(wiring_report.get("overall_status", "unknown"))
    if wiring_status == "wiring_suspect" and decision == "ready_for_main_figure":
        decision = "proceed_ablation_quick"
        figure_title_guidance = "needs ablation"

    representative_runs = []
    for key in (("hiroute", 1), ("inf_tag_forwarding", 3), ("central_directory", 1)):
        run_id = _first_run_id(index.get(key))
        if run_id and run_id not in representative_runs:
            representative_runs.append(run_id)

    return {
        "decision": decision,
        "figure_guidance": figure_guidance,
        "detail": {
            "hiroute_reaches_ceiling_at_manifest1": hiroute_ceiling,
            "oracle_lower_byte_upper_bound": oracle_lower_byte_upper_bound,
            "first_fetch_advantage": first_fetch_advantage,
            "hiroute_terminal_vs_first_fetch_gap": hiroute_support_gap,
            "hiroute_manifest_rescue_signal": hiroute_manifest_rescue_signal,
            "wiring_report_status": wiring_status,
            "discovery_reply_stage_matrix_digest": discovery_digest,
            "baseline_details": baseline_details,
        },
        "representative_runs": representative_runs,
        "recommend_next_stage": "stop" if decision == "saturated_revisit_workload" else "ablation_quick",
        "figure_title_guidance": figure_title_guidance,
        "key_metrics_digest": rows,
    }


def _cost_order_flags(rows: list[dict[str, Any]]) -> tuple[bool, bool]:
    bytes_values = [float(row["mean_discovery_bytes"]) for row in rows]
    probe_values = [float(row["mean_probe_count"]) for row in rows]
    return _strictly_non_decreasing(bytes_values), _strictly_non_decreasing(probe_values)


def _ablation_decision(rows: list[dict[str, Any]], wiring_report: dict[str, Any]) -> dict[str, Any]:
    index = _row_index(rows)
    manifests = (1, 2, 3)
    required = [
        ("predicates_only", manifest)
        for manifest in manifests
    ] + [
        ("flat_semantic_only", manifest)
        for manifest in manifests
    ] + [
        ("predicates_plus_flat", manifest)
        for manifest in manifests
    ] + [
        ("full_hiroute", manifest)
        for manifest in manifests
    ]
    missing = [f"{scheme}@manifest{manifest}" for scheme, manifest in required if (scheme, manifest) not in index]
    if missing:
        return {
            "decision": "rerun_needed",
            "figure_guidance": [],
            "detail": {
                "reason": "missing_rows",
                "missing": missing,
                "wiring_report_status": str(wiring_report.get("overall_status", "unknown")),
            },
            "representative_runs": [],
            "recommend_next_stage": "stop",
            "figure_title_guidance": "rerun needed",
            "key_metrics_digest": rows,
        }

    manifest_details: dict[str, Any] = {}
    mechanism_ordering_clean = True
    hierarchy_signal_restored = True
    predicate_filtering_contributes = True
    flat_semantics_insufficient = True
    bytes_order_clean = True
    probe_order_clean = True
    full_hiroute_cost_best = True
    first_fetch_order_matches_success = True

    for manifest_size in manifests:
        full_row = index[("full_hiroute", manifest_size)]
        plus_flat_row = index[("predicates_plus_flat", manifest_size)]
        predicate_only_row = index[("predicates_only", manifest_size)]
        flat_row = index[("flat_semantic_only", manifest_size)]

        best_baseline_success = max(
            _terminal_strong_success(plus_flat_row),
            _terminal_strong_success(predicate_only_row),
            _terminal_strong_success(flat_row),
        )
        success_order_clean = (
            _terminal_strong_success(full_row) - best_baseline_success >= SUCCESS_TOLERANCE
        )
        hierarchy_ok = _materially_better(full_row, plus_flat_row) and _materially_better(full_row, flat_row)
        predicate_ok = _materially_better(plus_flat_row, flat_row)
        flat_only_bad = _materially_better(predicate_only_row, flat_row) and _materially_better(full_row, flat_row)
        bytes_ok, probes_ok = _cost_order_flags([full_row, plus_flat_row, predicate_only_row, flat_row])
        min_discovery_bytes = min(
            float(row["mean_discovery_bytes"]) for row in (full_row, plus_flat_row, predicate_only_row, flat_row)
        )
        full_hiroute_cost_best = full_hiroute_cost_best and (
            float(full_row["mean_discovery_bytes"]) <= min_discovery_bytes + EPSILON
        )
        first_fetch_values = [
            _first_fetch_strong_success(full_row),
            _first_fetch_strong_success(plus_flat_row),
            _first_fetch_strong_success(predicate_only_row),
            _first_fetch_strong_success(flat_row),
        ]
        first_fetch_order_matches_success = first_fetch_order_matches_success and _strictly_non_increasing(
            first_fetch_values
        )

        mechanism_ordering_clean = mechanism_ordering_clean and success_order_clean
        hierarchy_signal_restored = hierarchy_signal_restored and hierarchy_ok
        predicate_filtering_contributes = predicate_filtering_contributes and predicate_ok
        flat_semantics_insufficient = flat_semantics_insufficient and flat_only_bad
        bytes_order_clean = bytes_order_clean and bytes_ok
        probe_order_clean = probe_order_clean and probes_ok

        manifest_details[str(manifest_size)] = {
            "success_order_clean": success_order_clean,
            "hierarchy_signal_restored": hierarchy_ok,
            "predicate_filtering_contributes": predicate_ok,
            "flat_semantics_insufficient": flat_only_bad,
            "bytes_order_clean": bytes_ok,
            "probe_order_clean": probes_ok,
            "full_vs_next_best_terminal_strong_gap": round(
                _terminal_strong_success(full_row) - best_baseline_success,
                6,
            ),
            "rows": {
                "full_hiroute": full_row,
                "predicates_plus_flat": plus_flat_row,
                "predicates_only": predicate_only_row,
                "flat_semantic_only": flat_row,
            },
        }

    scheme_rows = {
        scheme: [index[(scheme, manifest)] for manifest in manifests]
        for scheme in ("full_hiroute", "predicates_plus_flat", "predicates_only", "flat_semantic_only")
    }
    main_manifest = ABLATION_MAIN_MANIFEST_SIZE
    main_rows = {
        scheme: index[(scheme, main_manifest)]
        for scheme in ("full_hiroute", "predicates_plus_flat", "predicates_only", "flat_semantic_only")
    }
    main_next_best_success = max(
        _terminal_strong_success(row)
        for scheme, row in main_rows.items()
        if scheme != "full_hiroute"
    )
    main_full_success_gap = (
        _terminal_strong_success(main_rows["full_hiroute"]) - main_next_best_success
    )
    main_headline_success_gap_ok = main_full_success_gap >= ABLATION_HEADLINE_SUCCESS_GAP
    main_hierarchy_signal = main_full_success_gap >= SUCCESS_TOLERANCE
    distributed_saturated = all(
        _saturated_group(
            [
                index[("full_hiroute", manifest_size)],
                index[("predicates_plus_flat", manifest_size)],
                index[("predicates_only", manifest_size)],
                index[("flat_semantic_only", manifest_size)],
            ]
        )
        for manifest_size in manifests
    )
    cost_order_matches_accuracy_order = bytes_order_clean and probe_order_clean
    wiring_status = str(wiring_report.get("overall_status", "unknown"))

    figure_guidance: list[str] = []
    if hierarchy_signal_restored:
        figure_guidance.append("hierarchy_signal_restored")
    if predicate_filtering_contributes:
        figure_guidance.append("predicate_filtering_contributes")
    if flat_semantics_insufficient:
        figure_guidance.append("flat_semantics_insufficient")
    if cost_order_matches_accuracy_order:
        figure_guidance.append("cost_order_matches_accuracy_order")
    if full_hiroute_cost_best:
        figure_guidance.append("full_hiroute_cost_best")
    if mechanism_ordering_clean:
        figure_guidance.append("mechanism_ordering_clean")
    if not first_fetch_order_matches_success:
        figure_guidance.append("terminal_vs_first_fetch_not_aligned")
    if main_headline_success_gap_ok:
        figure_guidance.append("manifest1_terminal_strong_gap_ok")

    if wiring_status == "wiring_suspect":
        decision = "rerun_needed"
        figure_title_guidance = "rerun needed"
    elif distributed_saturated:
        decision = "saturated_revisit_workload"
        figure_title_guidance = "revisit workload"
    elif main_headline_success_gap_ok and main_hierarchy_signal:
        decision = "ready_for_main_figure"
        figure_title_guidance = "manifest1 terminal strong mechanism figure"
    elif main_hierarchy_signal:
        decision = "ready_for_support_figure"
        figure_title_guidance = "manifest1 support figure"
    else:
        decision = "rerun_needed"
        figure_title_guidance = "rerun needed"

    representative_runs = []
    for key in (
        ("full_hiroute", 1),
        ("predicates_plus_flat", 3),
        ("predicates_only", 3),
        ("flat_semantic_only", 3),
    ):
        run_id = _first_run_id(index.get(key))
        if run_id and run_id not in representative_runs:
            representative_runs.append(run_id)

    return {
        "decision": decision,
        "figure_guidance": figure_guidance,
        "detail": {
            "wiring_report_status": wiring_status,
            "manifest_details": manifest_details,
            "hierarchy_signal_restored": hierarchy_signal_restored,
            "predicate_filtering_contributes": predicate_filtering_contributes,
            "flat_semantics_insufficient": flat_semantics_insufficient,
            "cost_order_matches_accuracy_order": cost_order_matches_accuracy_order,
            "full_hiroute_cost_best": full_hiroute_cost_best,
            "first_fetch_order_matches_success": first_fetch_order_matches_success,
            "mechanism_ordering_clean": mechanism_ordering_clean,
            "distributed_saturated": distributed_saturated,
            "main_manifest_size": main_manifest,
            "main_full_vs_next_best_terminal_strong_gap": round(main_full_success_gap, 6),
            "main_headline_success_gap_ok": main_headline_success_gap_ok,
            "headline_success_gap_threshold": ABLATION_HEADLINE_SUCCESS_GAP,
        },
        "representative_runs": representative_runs,
        "recommend_next_stage": "routing_main_quick" if decision in {"ready_for_main_figure", "ready_for_support_figure"} else "stop",
        "figure_title_guidance": figure_title_guidance,
        "key_metrics_digest": rows,
    }


def _stdout_lines_for_object_main(payload: dict[str, Any]) -> list[str]:
    baseline_details = payload["detail"]["baseline_details"]
    discovery_digest = payload.get("detail", {}).get("discovery_reply_stage_matrix_digest", {})
    legacy_rows = int(discovery_digest.get("legacy_inferred_row_count", 0) or 0)
    legacy_counts = int(discovery_digest.get("legacy_inferred_count_sum", 0) or 0)
    matrix_csv = str(discovery_digest.get("matrix_csv", ""))
    return [
        f"decision: {payload['decision']}",
        f"figure_guidance: {', '.join(payload['figure_guidance']) if payload['figure_guidance'] else '(none)'}",
        (
            "Q1. INF 在 manifest=2/3 是否追平 HiRoute: "
            f"inf={baseline_details['inf_tag_forwarding']['catch_up_manifest'] or 'no'}"
        ),
        (
            "Q2. 即使追平，bytes/probes 是否仍显著更高: "
            f"inf={'yes' if baseline_details['inf_tag_forwarding']['residual_cost_gap'] else 'no'}"
        ),
        (
            "Q3. central_directory 是否继续保持 lower-byte oracle upper bound: "
            f"{'yes' if payload['detail']['oracle_lower_byte_upper_bound'] else 'no'}"
        ),
        f"Q4. Figure 5 更适合的标题: {payload['figure_title_guidance']}",
        (
            "Q5. discovery matrix 是否仍依赖 legacy_inferred: "
            f"{'yes' if legacy_rows > 0 or legacy_counts > 0 else 'no'}"
        ),
        f"Q6. discovery matrix 引用路径: {matrix_csv}",
    ]


def _stdout_lines_for_ablation(payload: dict[str, Any]) -> list[str]:
    detail = payload["detail"]
    main_or_support = "main figure" if payload["decision"] == "ready_for_main_figure" else "support figure"
    return [
        f"decision: {payload['decision']}",
        f"figure_guidance: {', '.join(payload['figure_guidance']) if payload['figure_guidance'] else '(none)'}",
        f"Q1. hierarchy signal 是否恢复: {'yes' if detail.get('hierarchy_signal_restored') else 'no'}",
        f"Q2. predicates 是否有独立贡献: {'yes' if detail.get('predicate_filtering_contributes') else 'no'}",
        f"Q3. flat semantics 是否不足: {'yes' if detail.get('flat_semantics_insufficient') else 'no'}",
        f"Q4. Figure 3 更适合作为: {main_or_support if payload['decision'] in {'ready_for_main_figure', 'ready_for_support_figure'} else payload['figure_title_guidance']}",
    ]


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(_resolve(args.experiment))

    run_rows = _load_run_rows(args.run_ids_file)
    query_rows = _collect_query_rows(run_rows)
    if not query_rows:
        print("ERROR: no query rows available for stage decision")
        return 1

    summary_rows = _group_rows(query_rows)
    source_run_ids = sorted({row["run_id"] for row in run_rows})
    wiring_report = _load_json(args.wiring_report)

    if args.stage == "object_main" and experiment.get("experiment_id") == "object_main":
        discovery_digest = _discovery_reply_stage_digest(experiment, source_run_ids)
        decision_payload = _object_main_decision(summary_rows, wiring_report, discovery_digest)
        stdout_lines = _stdout_lines_for_object_main
    elif args.stage == "ablation" and experiment.get("experiment_id") == "ablation":
        decision_payload = _ablation_decision(summary_rows, wiring_report)
        stdout_lines = _stdout_lines_for_ablation
    else:
        print(f"ERROR: build_stage_decision.py does not support stage={args.stage} experiment={experiment.get('experiment_id')}")
        return 1

    payload = {
        "stage": args.stage,
        "experiment_id": experiment["experiment_id"],
        **decision_payload,
        "query_count": len(query_rows),
        "run_count": len(source_run_ids),
        "source_run_ids": source_run_ids,
    }

    output_path = _resolve(args.output_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print("\n".join(stdout_lines(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
