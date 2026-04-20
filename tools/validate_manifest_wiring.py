"""Audit manifest-size parameter wiring for mainline object/ablation stages."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import isoformat_z, load_json_yaml, read_csv, repo_root


SUCCESS_TOLERANCE = 0.02
FAILURE_TOLERANCE = 0.02
RESCUE_TOLERANCE = 0.02
BYTES_ADVANTAGE_THRESHOLD = 0.10
PROBE_ADVANTAGE_THRESHOLD = 0.5

STAGE_TO_EXPERIMENT = {
    "object_main": "configs/experiments/object_main.yaml",
    "ablation": "configs/experiments/ablation.yaml",
}

NOT_CONSUMED_BY_DESIGN: set[str] = set()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=sorted(STAGE_TO_EXPERIMENT), required=True)
    parser.add_argument("--experiment", type=Path)
    parser.add_argument("--run-ids-file", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else repo_root() / path


def _load_stage_status(stage: str) -> dict[str, Any]:
    path = repo_root() / "review_artifacts" / stage / "stage_status.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _default_output_path(stage: str) -> Path:
    return repo_root() / "review_artifacts" / stage / "aggregate" / f"{stage}_manifest_wiring_report.json"


def _load_run_ids(args: argparse.Namespace) -> list[str]:
    if args.run_ids_file:
        path = _resolve(args.run_ids_file)
        if not path.exists():
            raise RuntimeError(f"run ids file does not exist: {path}")
        return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    stage_status = _load_stage_status(args.stage)
    run_ids = [str(run_id) for run_id in stage_status.get("completed_run_ids", []) if str(run_id).strip()]
    if not run_ids:
        default_run_ids = repo_root() / "review_artifacts" / args.stage / "run_ids.txt"
        if default_run_ids.exists():
            run_ids = [line.strip() for line in default_run_ids.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not run_ids:
        raise RuntimeError(f"stage {args.stage} has no completed_run_ids to audit")
    return run_ids


def _load_registry_rows(run_ids: list[str]) -> list[dict[str, str]]:
    requested = set(run_ids)
    rows = [row for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv") if row["run_id"] in requested]
    missing = sorted(requested - {row["run_id"] for row in rows})
    if missing:
        raise RuntimeError(f"missing run ids in runs.csv: {missing}")
    return rows


def _total_failure_rate(row: dict[str, float]) -> float:
    return float(row["failure_rate_wrong_domain"]) + float(row["failure_rate_wrong_object"]) + float(row["failure_rate_predicate_miss"])


def _relative_spread(values: list[float]) -> float:
    if not values:
        return 0.0
    maximum = max(values)
    minimum = min(values)
    if maximum <= 0.0:
        return 0.0
    return (maximum - minimum) / maximum


def _collect_run_report(row: dict[str, str]) -> tuple[dict[str, Any], dict[str, float]]:
    run_dir = repo_root() / row["run_dir"]
    manifest = load_json_yaml(run_dir / "manifest.yaml")
    query_log_path = run_dir / "query_log.csv"
    query_rows = read_csv(query_log_path)
    search_trace_path = run_dir / "search_trace.csv"
    probe_log_path = run_dir / "probe_log.csv"
    manifest_size = int(manifest.get("manifest_size") or 0)
    runner_manifest_size_raw = (manifest.get("runner_params", {}) or {}).get("manifestSize")
    runner_manifest_size = int(runner_manifest_size_raw) if runner_manifest_size_raw not in (None, "") else None
    scheme = str(manifest.get("scheme") or row["scheme"])
    runner_type = str(manifest.get("runner_type") or "")
    launcher_override_expected = runner_type == "ndnsim" and manifest_size > 0

    failure_rates = {
        "failure_rate_wrong_domain": round(
            sum(1 for entry in query_rows if entry.get("failure_type", "") == "wrong_domain") / len(query_rows),
            6,
        ) if query_rows else 0.0,
        "failure_rate_wrong_object": round(
            sum(1 for entry in query_rows if entry.get("failure_type", "") == "wrong_object") / len(query_rows),
            6,
        ) if query_rows else 0.0,
        "failure_rate_predicate_miss": round(
            sum(1 for entry in query_rows if entry.get("failure_type", "") == "predicate_miss") / len(query_rows),
            6,
        ) if query_rows else 0.0,
    }
    metrics = {
        "mean_success_at_1": round(sum(float(entry.get("success_at_1") or 0) for entry in query_rows) / len(query_rows), 6) if query_rows else 0.0,
        **failure_rates,
        "within_reply_manifest_rescue_rate": round(
            sum(
                1
                for entry in query_rows
                if float(entry.get("success_at_1") or 0) == 1.0
                and float(entry.get("manifest_fetch_index") or 0) > 0
            )
            / len(query_rows),
            6,
        ) if query_rows else 0.0,
        "cross_probe_manifest_rescue_rate": round(
            sum(
                1
                for entry in query_rows
                if float(entry.get("success_at_1") or 0) == 1.0
                and float(entry.get("cumulative_manifest_fetches") or 0) > 0
                and float(entry.get("manifest_fetch_index") or 0) == 0.0
            )
            / len(query_rows),
            6,
        ) if query_rows else 0.0,
        "mean_discovery_bytes": round(
            sum(float(entry.get("discovery_tx_bytes") or 0) + float(entry.get("discovery_rx_bytes") or 0) for entry in query_rows) / len(query_rows),
            6,
        ) if query_rows else 0.0,
        "mean_probe_count": round(sum(float(entry.get("num_remote_probes") or 0) for entry in query_rows) / len(query_rows), 6) if query_rows else 0.0,
        "query_count": len(query_rows),
    }

    if scheme in NOT_CONSUMED_BY_DESIGN:
        classification = "not_consumed_by_design"
        reason = "scheme explicitly ignores manifest_size"
    elif runner_manifest_size is None:
        if launcher_override_expected:
            classification = "runtime_config_recorded"
            reason = "manifest.yaml records selected manifest_size; ndnsim launcher applies it even when runner_params default is absent"
        else:
            classification = "wiring_suspect"
            reason = "manifest.yaml missing runner_params.manifestSize"
    elif runner_manifest_size != manifest_size:
        if launcher_override_expected:
            classification = "runtime_config_recorded"
            reason = "runner_params.manifestSize is a default snapshot; ndnsim launcher overrides it with the selected manifest_size"
        else:
            classification = "wiring_suspect"
            reason = "manifest.yaml manifest_size and runner_params.manifestSize disagree"
    else:
        classification = "runtime_config_recorded"
        reason = "manifest.yaml records matching manifest_size and runner_params.manifestSize"

    report = {
        "run_id": row["run_id"],
        "scheme": scheme,
        "manifest_size": manifest_size,
        "runner_manifest_size": runner_manifest_size,
        "classification": classification,
        "reason": reason,
        "runtime_evidence": {
            "manifest_yaml_present": True,
            "runner_manifest_size_matches": runner_manifest_size == manifest_size,
            "launcher_override_expected": launcher_override_expected,
            "query_log_present": query_log_path.exists(),
            "search_trace_present": search_trace_path.exists(),
            "probe_log_present": probe_log_path.exists(),
        },
        "metrics": metrics,
    }
    return report, metrics


def _scheme_report(
    scheme: str,
    run_reports: list[dict[str, Any]],
    expected_manifest_sizes: list[int],
) -> dict[str, Any]:
    manifest_sizes_seen = sorted({int(run["manifest_size"]) for run in run_reports})
    missing_manifest_sizes = [manifest_size for manifest_size in expected_manifest_sizes if manifest_size not in manifest_sizes_seen]
    per_manifest = {
        int(run["manifest_size"]): run["metrics"]
        for run in sorted(run_reports, key=lambda item: int(item["manifest_size"]))
    }
    success_values = [float(metrics["mean_success_at_1"]) for metrics in per_manifest.values()]
    failure_values = [_total_failure_rate(metrics) for metrics in per_manifest.values()]
    rescue_values = [
        float(metrics.get("within_reply_manifest_rescue_rate", 0.0))
        + float(metrics.get("cross_probe_manifest_rescue_rate", 0.0))
        for metrics in per_manifest.values()
    ]
    bytes_values = [float(metrics["mean_discovery_bytes"]) for metrics in per_manifest.values()]
    probe_values = [float(metrics["mean_probe_count"]) for metrics in per_manifest.values()]
    effect_visible = (
        (max(success_values) - min(success_values) >= SUCCESS_TOLERANCE)
        or (max(failure_values) - min(failure_values) >= FAILURE_TOLERANCE)
        or (max(rescue_values) - min(rescue_values) >= RESCUE_TOLERANCE)
        or (_relative_spread(bytes_values) >= BYTES_ADVANTAGE_THRESHOLD)
        or (max(probe_values) - min(probe_values) >= PROBE_ADVANTAGE_THRESHOLD)
    ) if per_manifest else False

    suspicious_runs = [run["run_id"] for run in run_reports if run["classification"] == "wiring_suspect"]
    if scheme in NOT_CONSUMED_BY_DESIGN:
        classification = "not_consumed_by_design"
        reason = "scheme explicitly ignores manifest_size"
    elif suspicious_runs or missing_manifest_sizes:
        classification = "wiring_suspect"
        reason = "runtime config evidence incomplete" if suspicious_runs else f"missing manifest sizes: {missing_manifest_sizes}"
    elif effect_visible:
        classification = "wiring_ok_and_effect_visible"
        reason = "manifest_size is recorded and observable terminal, rescue, or cost metrics vary across sweep points"
    else:
        classification = "wiring_ok_but_metric_invariant"
        reason = "manifest_size is recorded, but success/failure/rescue/cost metrics are invariant across sweep points"

    return {
        "scheme": scheme,
        "classification": classification,
        "reason": reason,
        "expected_manifest_sizes": expected_manifest_sizes,
        "manifest_sizes_seen": manifest_sizes_seen,
        "run_ids": [run["run_id"] for run in sorted(run_reports, key=lambda item: int(item["manifest_size"]))],
        "metrics_by_manifest": {str(key): value for key, value in sorted(per_manifest.items())},
        "effect_visible": effect_visible,
        "suspicious_runs": suspicious_runs,
    }


def _overall_status(scheme_reports: list[dict[str, Any]]) -> str:
    classifications = {report["classification"] for report in scheme_reports}
    if "wiring_suspect" in classifications:
        return "wiring_suspect"
    if "wiring_ok_and_effect_visible" in classifications:
        return "wiring_ok_and_effect_visible"
    if "wiring_ok_but_metric_invariant" in classifications:
        return "wiring_ok_but_metric_invariant"
    return "not_consumed_by_design"


def main() -> int:
    args = parse_args()
    experiment_path = _resolve(args.experiment or STAGE_TO_EXPERIMENT[args.stage])
    experiment = load_json_yaml(experiment_path)
    output_path = _resolve(args.output_json or _default_output_path(args.stage))

    if args.dry_run:
        print(f"stage={args.stage}")
        print(f"experiment={experiment_path}")
        print(f"output_json={output_path}")
        print("statuses=wiring_ok_and_effect_visible,wiring_ok_but_metric_invariant,not_consumed_by_design,wiring_suspect")
        return 0

    run_ids = _load_run_ids(args)
    registry_rows = _load_registry_rows(run_ids)
    run_reports: list[dict[str, Any]] = []
    runs_by_scheme: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in registry_rows:
        run_report, _metrics = _collect_run_report(row)
        run_reports.append(run_report)
        runs_by_scheme[run_report["scheme"]].append(run_report)

    expected_manifest_sizes = [int(value) for value in experiment.get("manifest_sizes", [])]
    scheme_reports = [
        _scheme_report(scheme, scheme_run_reports, expected_manifest_sizes)
        for scheme, scheme_run_reports in sorted(runs_by_scheme.items())
    ]
    overall_status = _overall_status(scheme_reports)
    payload = {
        "stage": args.stage,
        "experiment_id": experiment["experiment_id"],
        "generated_at": isoformat_z(),
        "run_count": len(run_reports),
        "expected_manifest_sizes": expected_manifest_sizes,
        "overall_status": overall_status,
        "scheme_reports": scheme_reports,
        "run_reports": sorted(run_reports, key=lambda item: (item["scheme"], int(item["manifest_size"]), item["run_id"])),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"stage={args.stage}")
    print(f"overall_status={overall_status}")
    for scheme_report in scheme_reports:
        print(
            "SCHEME "
            + f"scheme={scheme_report['scheme']} "
            + f"classification={scheme_report['classification']} "
            + f"manifest_sizes={','.join(str(value) for value in scheme_report['manifest_sizes_seen'])} "
            + f"reason={scheme_report['reason']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
