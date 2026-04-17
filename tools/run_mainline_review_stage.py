"""Stage-oriented mainline rerun workflow with quick gates and freshness metadata."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import git_head, isoformat_z, load_json_yaml, read_csv, repo_root

PROJECT_PYTHON_PATH = repo_root() / ".venv" / "bin" / "python"
PYTHON = str(PROJECT_PYTHON_PATH if PROJECT_PYTHON_PATH.exists() else Path(sys.executable))


STAGES = {
    "source_sync",
    "object_main_quick",
    "object_main",
    "ablation_quick",
    "ablation",
    "routing_main",
    "state_scaling",
    "robustness",
    "diagnostic_object_routing",
    "object_ablation_routing",
    "full_mainline",
    "paper_freeze",
}

PACKAGEABLE_STAGES = {
    "source_sync",
    "diagnostic_object_routing",
    "object_main_quick",
    "object_main",
    "ablation_quick",
    "ablation",
}

OBJECT_MAIN_ALLOWED_ABLATION_DECISIONS = {
    "ready_for_main_figure",
    "proceed_ablation_quick",
    "cost_only_figure",
    "support_only_figure",
}

QUICK_REQUIRED_VALIDATIONS = (
    "validate_run",
    "validate_runtime_slice",
    "validate_manifest_regression",
    "validate_aggregate_traceability",
)

ABLATION_QUICK_REQUIRED_VALIDATIONS = (
    "validate_run",
    "validate_runtime_slice",
    "validate_aggregate_traceability",
)

DATASET_FINGERPRINT_FILES = [
    "configs/datasets/smartcity.yaml",
    "configs/hierarchy/hiroute_hkm.yaml",
    "scripts/build_dataset/build_queries_and_qrels.py",
    "scripts/build_dataset/build_hierarchy_and_hslsa.py",
    "docs/datasets/schema_reference.md",
]

BINARY_FINGERPRINT_FILES = [
    "ns-3/src/ndnSIM/apps/hiroute-controller-app.cpp",
    "ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp",
    "ns-3/src/ndnSIM/examples/hiroute-scenario-common.hpp",
]

SIMULATION_FINGERPRINT_FILES = [
    "scripts/run/run_experiment.py",
]

SIMULATION_IDENTITY_KEYS = (
    "experiment_id",
    "dataset_id",
    "topology_id",
    "comparison_topologies",
    "scenario",
    "schemes",
    "seeds",
    "budgets",
    "manifest_sizes",
    "default_budget",
    "default_manifest_size",
    "reference_schemes",
    "frontier_schemes",
    "query_filters",
    "inputs",
)

SIMULATION_RUNNER_KEYS = (
    "type",
    "params",
    "scenario_variants",
    "default_variant",
)

STAGE_CONTRACT_EXPERIMENT_KEYS = (
    "promotion_rule",
    "measurement_mode",
    "outputs",
)

COMMON_STAGE_CONTRACT_FILES = [
    "tools/run_mainline_review_stage.py",
    "tools/validate_run.py",
    "tools/validate_runtime_slice.py",
    "tools/validate_aggregate_traceability.py",
    "tools/validate_figures.py",
    "tools/validate_manifest_regression.py",
    "tools/validate_manifest_wiring.py",
    "scripts/eval/promote_runs.py",
    "scripts/eval/aggregate_experiment.py",
    "scripts/plots/plot_experiment.py",
    "scripts/run/run_experiment_matrix.py",
]

STAGE_CONTRACT_FILE_MAP = {
    "object_main_quick": [
        "scripts/eval/build_stage_quick_summary.py",
        "scripts/eval/build_stage_decision.py",
    ],
    "object_main": [
        "scripts/eval/build_object_main_manifest_sweep.py",
        "scripts/eval/build_failure_breakdown.py",
        "scripts/eval/build_stage_decision.py",
    ],
    "ablation_quick": [
        "scripts/eval/build_stage_quick_summary.py",
        "scripts/eval/build_stage_decision.py",
    ],
    "ablation": [
        "scripts/eval/build_ablation_summary.py",
        "scripts/eval/build_stage_decision.py",
    ],
    "routing_main": [
        "scripts/eval/aggregate_query_metrics.py",
        "scripts/eval/build_candidate_shrinkage.py",
        "scripts/eval/build_deadline_summary.py",
    ],
    "state_scaling": [
        "scripts/eval/build_state_scaling_summary.py",
    ],
    "robustness": [
        "scripts/eval/build_robustness_summary.py",
    ],
}

OBJECT_MAIN_QUICK_MATRIX = [
    {"scheme": "hiroute", "manifest_size": 1, "seed": 1},
    {"scheme": "hiroute", "manifest_size": 2, "seed": 1},
    {"scheme": "hiroute", "manifest_size": 3, "seed": 1},
    {"scheme": "inf_tag_forwarding", "manifest_size": 1, "seed": 1},
    {"scheme": "central_directory", "manifest_size": 1, "seed": 1},
]

ABLATION_QUICK_MATRIX = [
    {"scheme": "predicates_only", "manifest_size": 1, "seed": 1},
    {"scheme": "flat_semantic_only", "manifest_size": 1, "seed": 1},
    {"scheme": "predicates_plus_flat", "manifest_size": 1, "seed": 1},
    {"scheme": "full_hiroute", "manifest_size": 1, "seed": 1},
]

EXPERIMENT_PATHS = {
    "object_main": "configs/experiments/object_main.yaml",
    "ablation": "configs/experiments/ablation.yaml",
    "routing_main": "configs/experiments/routing_main.yaml",
    "state_scaling": "configs/experiments/state_scaling.yaml",
    "robustness": "configs/experiments/robustness.yaml",
    "routing_debug": "configs/experiments/routing_debug.yaml",
    "object_debug": "configs/experiments/object_debug.yaml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mode", choices=["official", "dry"], default="official")
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--allow-dirty-worktree", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    parser.add_argument("--package", action="store_true")
    parser.add_argument("--force-rerun", action="store_true")
    parser.add_argument("--force-rebuild-dataset", action="store_true")
    parser.add_argument("--force-rebuild-binary", action="store_true")
    return parser.parse_args()


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else repo_root() / path


def _print_cmd(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))


def _run(
    cmd: list[str],
    *,
    output_path: Path | None = None,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> str:
    if dry_run:
        _print_cmd(cmd)
        if output_path is not None:
            print(f"  -> {output_path}")
        return ""
    result = subprocess.run(
        cmd,
        cwd=cwd or repo_root(),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(stdout + stderr, encoding="utf-8")
    else:
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{stdout}{stderr}")
    return stdout.strip()


def _run_env(*, allow_dirty_worktree: bool) -> dict[str, str] | None:
    if not allow_dirty_worktree:
        return None
    return {**os.environ, "HIROUTE_ALLOW_DIRTY_WORKTREE": "1"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_stage_status(status: dict[str, Any]) -> dict[str, Any]:
    if not status:
        return {}
    normalized = dict(status)
    normalized.setdefault("run_assignments", {})
    normalized.setdefault("completed_run_ids", [])
    normalized.setdefault("validation_status", {})
    normalized.setdefault("aggregate_outputs", [])
    normalized.setdefault("simulation_fingerprint", {})
    normalized.setdefault("stage_contract_fingerprint", {})
    normalized.setdefault("experiment_fingerprint", {})
    normalized.setdefault("runtime_fingerprint", {})
    normalized.setdefault("inherited_runs", [])
    normalized.setdefault("newly_executed_runs", [])
    normalized.setdefault("skipped_runs", [])
    normalized.setdefault("figure_guidance", [])
    normalized.setdefault("recommend_next_stage", "")
    normalized.setdefault("stage_decision", normalized.get("decision", "paused"))
    normalized.setdefault("decision", normalized.get("stage_decision", "paused"))
    representative_runs = normalized.get("representative_runs")
    if representative_runs is None:
        representative_run = str(normalized.get("representative_run", "")).strip()
        representative_runs = [representative_run] if representative_run else []
    normalized["representative_runs"] = list(representative_runs)
    if not normalized.get("representative_run") and normalized["representative_runs"]:
        normalized["representative_run"] = normalized["representative_runs"][0]
    return normalized


def _sha256(paths: list[str]) -> dict[str, Any]:
    hasher = hashlib.sha256()
    resolved_paths: list[str] = []
    for raw in paths:
        path = _resolve(raw)
        resolved_paths.append(str(path.relative_to(repo_root())))
        hasher.update(raw.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return {"sha256": hasher.hexdigest(), "files": resolved_paths}


def _payload_fingerprint(files: list[str], payload: dict[str, Any]) -> dict[str, Any]:
    normalized_files = sorted(dict.fromkeys(files))
    hasher = hashlib.sha256()
    for raw in normalized_files:
        path = _resolve(raw)
        hasher.update(raw.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    hasher.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return {
        "sha256": hasher.hexdigest(),
        "files": normalized_files,
        "payload": payload,
    }


def _normalized_matrix(experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "scheme": str(entry.get("scheme", "")),
                "topology_id": str(entry.get("topology_id", experiment.get("topology_id", ""))),
                "seed": int(entry.get("seed", 1)),
                "manifest_size": int(entry.get("manifest_size", 0)),
                "budget": int(entry.get("budget", 0)),
                "variant": str(entry.get("variant", "")),
            }
            for entry in matrix
        ],
        key=_assignment_key,
    )


def _select_keys(source: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {
        key: source[key]
        for key in keys
        if key in source
    }


def _config_dependency_files(node: Any) -> list[str]:
    discovered: set[str] = set()

    def _visit(value: Any) -> None:
        if isinstance(value, dict):
            for nested in value.values():
                _visit(nested)
            return
        if isinstance(value, list):
            for nested in value:
                _visit(nested)
            return
        if not isinstance(value, str):
            return
        candidate = _resolve(value)
        if not candidate.exists() or not candidate.is_file():
            return
        try:
            discovered.add(str(candidate.relative_to(repo_root())))
        except ValueError:
            return

    _visit(node)
    return sorted(discovered)


def _simulation_payload(experiment_path: Path, experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage_identity": str(experiment_path.relative_to(repo_root())),
        "experiment": _select_keys(experiment, SIMULATION_IDENTITY_KEYS),
        "runner": _select_keys(experiment.get("runner", {}) or {}, SIMULATION_RUNNER_KEYS),
        "matrix": _normalized_matrix(experiment, matrix),
    }


def _simulation_fingerprint(experiment_path: Path, experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    files = [
        *SIMULATION_FINGERPRINT_FILES,
        *_config_dependency_files(experiment.get("configs", {})),
    ]
    return _payload_fingerprint(files, _simulation_payload(experiment_path, experiment, matrix))


def _stage_contract_payload(stage: str, experiment_path: Path, experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage": stage,
        "experiment_path": str(experiment_path.relative_to(repo_root())),
        "contract": _select_keys(experiment, STAGE_CONTRACT_EXPERIMENT_KEYS),
        "matrix": _normalized_matrix(experiment, matrix),
    }


def _stage_contract_fingerprint(stage: str, experiment_path: Path, experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, Any]:
    files = [
        *COMMON_STAGE_CONTRACT_FILES,
        *STAGE_CONTRACT_FILE_MAP.get(stage, []),
    ]
    return _payload_fingerprint(files, _stage_contract_payload(stage, experiment_path, experiment, matrix))


def _fingerprint_changed(previous: dict[str, Any], key: str, current: dict[str, Any]) -> bool:
    previous_fp = previous.get(key, {}) or {}
    previous_sha = str(previous_fp.get("sha256", "")).strip()
    if not previous_sha:
        return False
    return previous_sha != current["sha256"]


def _missing_fingerprint(previous: dict[str, Any], key: str) -> bool:
    previous_fp = previous.get(key, {}) or {}
    return not str(previous_fp.get("sha256", "")).strip()


def _simulation_rerun_required(
    args: argparse.Namespace,
    previous: dict[str, Any],
    dataset_fingerprint: dict[str, Any],
    binary_fingerprint: dict[str, Any],
    simulation_fingerprint: dict[str, Any],
) -> bool:
    return (
        args.force_rerun
        or _fingerprint_changed(previous, "dataset_fingerprint", dataset_fingerprint)
        or _fingerprint_changed(previous, "binary_fingerprint", binary_fingerprint)
        or _fingerprint_changed(previous, "simulation_fingerprint", simulation_fingerprint)
    )


def _stage_refresh_required(
    args: argparse.Namespace,
    previous: dict[str, Any],
    dataset_fingerprint: dict[str, Any],
    binary_fingerprint: dict[str, Any],
    simulation_fingerprint: dict[str, Any],
    stage_contract_fingerprint: dict[str, Any],
) -> bool:
    return (
        not previous
        or _simulation_rerun_required(args, previous, dataset_fingerprint, binary_fingerprint, simulation_fingerprint)
        or _fingerprint_changed(previous, "stage_contract_fingerprint", stage_contract_fingerprint)
        or _missing_fingerprint(previous, "simulation_fingerprint")
        or _missing_fingerprint(previous, "stage_contract_fingerprint")
    )


def _stage_root(stage: str) -> Path:
    return repo_root() / "review_artifacts" / stage


def _stage_paths(stage: str) -> dict[str, Path]:
    root = _stage_root(stage)
    return {
        "root": root,
        "validation": root / "validation",
        "runs": root / "runs",
        "aggregate": root / "aggregate",
        "audits": root / "audits",
        "checks": root / "checks.txt",
        "readme": root / "README.md",
        "status": root / "stage_status.json",
        "bundle_manifest": root / "bundle_manifest.json",
    }


def _clear_stage_for_rerun(paths: dict[str, Path]) -> None:
    for key in ("validation", "runs", "aggregate", "audits"):
        if paths[key].exists():
            shutil.rmtree(paths[key])
    for key in ("checks", "readme", "status", "bundle_manifest"):
        if paths[key].exists():
            paths[key].unlink()


def _assignment_key(entry: dict[str, Any]) -> str:
    return "|".join(
        [
            f"scheme={entry.get('scheme', '')}",
            f"topology_id={entry.get('topology_id', 'rf_3967_exodus_compact')}",
            f"seed={entry.get('seed', 1)}",
            f"manifest_size={entry.get('manifest_size', 0)}",
            f"budget={entry.get('budget', 0)}",
            f"variant={entry.get('variant', '')}",
        ]
    )


def _load_stage_status(stage: str) -> dict[str, Any]:
    return _normalize_stage_status(_load_json(_stage_paths(stage)["status"]))


def _save_stage_status(paths: dict[str, Path], status: dict[str, Any], dry_run: bool) -> None:
    if dry_run:
        print(f"stage_status={paths['status']}")
        return
    _write_json(paths["status"], status)


def _csv_line(values: list[str]) -> str:
    return ",".join(value for value in values if value)


def _write_readme(
    paths: dict[str, Path],
    *,
    status: dict[str, Any],
    change_scope: str,
    completed_experiments: str,
    known_incomplete_items: str,
    dry_run: bool,
) -> None:
    stage_decision = str(status.get("stage_decision", status.get("decision", "paused")))
    content = "\n".join(
        [
            "# Review Bundle Metadata",
            f"current_git_commit: {git_head()}",
            f"change_scope: {change_scope}",
            f"completed_experiments: {completed_experiments}",
            f"stage_decision: {stage_decision}",
            f"figure_guidance: {_csv_line(list(status.get('figure_guidance', [])))}",
            f"representative_runs: {_csv_line(list(status.get('representative_runs', [])))}",
            f"recommend_next_stage: {status.get('recommend_next_stage', '')}",
            f"known_incomplete_items: {known_incomplete_items}",
            "",
        ]
    )
    if dry_run:
        print(f"README={paths['readme']}")
        return
    paths["readme"].write_text(content, encoding="utf-8")


def _write_checks(paths: dict[str, Path], checks: list[str], dry_run: bool) -> None:
    if dry_run:
        print(f"checks={paths['checks']}")
        for line in checks:
            print(f"CHECK {line}")
        return
    paths["checks"].write_text("\n".join(checks) + "\n", encoding="utf-8")


def _write_dispatch_log(path: Path, lines: list[str], dry_run: bool) -> None:
    if dry_run:
        print(f"dispatch_log={path}")
        for line in lines:
            print(f"DISPATCH {line}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _extract_run_id(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("run_experiment.py did not emit a run id")
    return lines[-1]


def _copy_run_to_stage(run_id: str, stage_runs_root: Path, dry_run: bool) -> None:
    source = repo_root() / "runs" / "completed" / run_id
    dest = stage_runs_root / run_id
    if dry_run:
        print(f"STAGE_RUN {source} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest, dirs_exist_ok=True)


def _load_experiment(experiment_key: str) -> tuple[Path, dict[str, Any]]:
    experiment_path = _resolve(EXPERIMENT_PATHS[experiment_key])
    experiment = load_json_yaml(experiment_path)
    return experiment_path, experiment


def _minimal_dataset_rebuild(dry_run: bool) -> list[str]:
    outputs: list[str] = []
    outputs.append(
        _run(
            [PYTHON, str(repo_root() / "scripts/build_dataset/build_queries_and_qrels.py"), "--config", str(_resolve("configs/datasets/smartcity.yaml"))],
            output_path=None,
            dry_run=dry_run,
        )
    )
    outputs.append(
        _run(
            [
                PYTHON,
                str(repo_root() / "scripts/build_dataset/build_hierarchy_and_hslsa.py"),
                "--dataset-config",
                str(_resolve("configs/datasets/smartcity.yaml")),
                "--hierarchy-config",
                str(_resolve("configs/hierarchy/hiroute_hkm.yaml")),
            ],
            output_path=None,
            dry_run=dry_run,
        )
    )
    outputs.append(
        _run(
            [
                PYTHON,
                str(repo_root() / "scripts/build_dataset/validate_dataset.py"),
                "--config",
                str(_resolve("configs/datasets/smartcity.yaml")),
            ],
            output_path=None,
            dry_run=dry_run,
        )
    )
    outputs.append(
        _run(
            [
                PYTHON,
                str(repo_root() / "scripts/build_dataset/audit_query_workloads.py"),
                "--config",
                str(_resolve("configs/datasets/smartcity.yaml")),
            ],
            output_path=None,
            dry_run=dry_run,
        )
    )
    return outputs


def _ensure_dataset_and_binary(
    *,
    dry_run: bool,
    force_rebuild_dataset: bool,
    force_rebuild_binary: bool,
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    cache_root = repo_root() / "review_artifacts" / "_cache"
    cache_root.mkdir(parents=True, exist_ok=True)
    dataset_fingerprint = _sha256(DATASET_FINGERPRINT_FILES)
    binary_fingerprint = _sha256(BINARY_FINGERPRINT_FILES)
    dataset_cache_path = cache_root / "dataset_fingerprint.json"
    binary_cache_path = cache_root / "binary_fingerprint.json"
    previous_dataset = _load_json(dataset_cache_path)
    previous_binary = _load_json(binary_cache_path)

    dataset_action = "reused"
    if force_rebuild_dataset or previous_dataset.get("sha256") != dataset_fingerprint["sha256"]:
        _minimal_dataset_rebuild(dry_run)
        if not dry_run:
            _write_json(dataset_cache_path, dataset_fingerprint)
        dataset_action = "rebuilt"

    binary_action = "reused"
    if force_rebuild_binary or previous_binary.get("sha256") != binary_fingerprint["sha256"]:
        _run(["./waf", "build"], dry_run=dry_run, cwd=repo_root() / "ns-3")
        if not dry_run:
            _write_json(binary_cache_path, binary_fingerprint)
        binary_action = "rebuilt"

    return dataset_action, binary_action, dataset_fingerprint, binary_fingerprint


def _current_stage_status(
    stage: str,
    requested_matrix: list[dict[str, Any]],
    dataset_fingerprint: dict[str, Any],
    binary_fingerprint: dict[str, Any],
    simulation_fingerprint: dict[str, Any],
    stage_contract_fingerprint: dict[str, Any],
    previous: dict[str, Any],
) -> dict[str, Any]:
    previous = _normalize_stage_status(previous)
    return {
        "stage": stage,
        "git_sha": git_head(),
        "generated_at": previous.get("generated_at", isoformat_z()),
        "updated_at": isoformat_z(),
        "dataset_fingerprint": dataset_fingerprint,
        "binary_fingerprint": binary_fingerprint,
        "simulation_fingerprint": simulation_fingerprint,
        "stage_contract_fingerprint": stage_contract_fingerprint,
        "requested_matrix": requested_matrix,
        "run_assignments": previous.get("run_assignments", {}),
        "completed_run_ids": previous.get("completed_run_ids", []),
        "validation_status": previous.get("validation_status", {}),
        "aggregate_outputs": previous.get("aggregate_outputs", []),
        "decision": previous.get("decision", previous.get("stage_decision", "paused")),
        "stage_decision": previous.get("stage_decision", previous.get("decision", "paused")),
        "completed_experiments": previous.get("completed_experiments", stage),
        "representative_run": previous.get("representative_run", ""),
        "representative_runs": previous.get("representative_runs", []),
        "figure_guidance": previous.get("figure_guidance", []),
        "recommend_next_stage": previous.get("recommend_next_stage", ""),
        "inherited_runs": previous.get("inherited_runs", []),
        "newly_executed_runs": previous.get("newly_executed_runs", []),
        "skipped_runs": previous.get("skipped_runs", []),
    }


def _matrix_skip_ok(status: dict[str, Any], entry: dict[str, Any]) -> str:
    run_id = status.get("run_assignments", {}).get(_assignment_key(entry), "")
    if not run_id:
        return ""
    if not (repo_root() / "runs" / "completed" / run_id / "manifest.yaml").exists():
        return ""
    return run_id


def _write_run_ids_file(paths: dict[str, Path], name: str, run_ids: list[str], dry_run: bool) -> Path:
    target = paths["root"] / name
    if dry_run:
        print(f"run_ids_file={target}")
        return target
    target.write_text("\n".join(run_ids) + ("\n" if run_ids else ""), encoding="utf-8")
    return target


def _selected_latest_runs(experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> dict[str, str]:
    desired = {_assignment_key(entry): entry for entry in matrix}
    selected: dict[str, dict[str, str]] = {}
    for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv"):
        if row["experiment_id"] != experiment["experiment_id"] or row["status"] != "completed":
            continue
        entry = {
            "scheme": row["scheme"],
            "topology_id": row["topology_id"],
            "seed": int(row["seed"]),
            "manifest_size": int(row.get("manifest_size") or 0),
            "budget": int(row.get("budget") or 0),
            "variant": "",
        }
        manifest_path = repo_root() / row["run_dir"] / "manifest.yaml"
        if manifest_path.exists():
            manifest = load_json_yaml(manifest_path)
            entry["variant"] = manifest.get("scenario_variant", "") or ""
        key = _assignment_key(entry)
        if key not in desired:
            continue
        incumbent = selected.get(key)
        if incumbent is None or row["start_time"] > incumbent["start_time"]:
            selected[key] = row
    return {key: selected[key]["run_id"] for key in sorted(selected)}


def _seed_run_assignments_from_latest(status: dict[str, Any], experiment: dict[str, Any], matrix: list[dict[str, Any]]) -> None:
    latest = _selected_latest_runs(experiment, matrix)
    run_assignments = status.setdefault("run_assignments", {})
    for key, run_id in latest.items():
        if run_assignments.get(key):
            continue
        run_assignments[key] = run_id


def _matrix_topologies(experiment: dict[str, Any]) -> list[str]:
    comparison = [str(value) for value in experiment.get("comparison_topologies", []) if str(value)]
    if comparison:
        return comparison
    topology_id = str(experiment.get("topology_id", "") or "")
    return [topology_id] if topology_id else []


def _matrix_seeds(experiment: dict[str, Any]) -> list[int]:
    return [int(value) for value in experiment.get("seeds", [1])]


def _matrix_variants(experiment: dict[str, Any]) -> list[str]:
    variants = list((experiment.get("runner", {}) or {}).get("scenario_variants", {}).keys())
    return variants if variants else [""]


def _resolved_default_budget(experiment: dict[str, Any]) -> int:
    value = int(experiment.get("default_budget") or 0)
    if value:
        return value
    runner_params = (experiment.get("runner", {}) or {}).get("params", {}) or {}
    return int(runner_params.get("exportBudget") or 0)


def _resolved_default_manifest_size(experiment: dict[str, Any]) -> int:
    value = int(experiment.get("default_manifest_size") or 0)
    if value:
        return value
    runner_params = (experiment.get("runner", {}) or {}).get("params", {}) or {}
    return int(runner_params.get("manifestSize") or 0)


def _generic_requested_matrix(experiment: dict[str, Any]) -> list[dict[str, Any]]:
    requested: list[dict[str, Any]] = []
    reference_schemes = {str(value) for value in experiment.get("reference_schemes", [])}
    topologies = _matrix_topologies(experiment)
    seeds = _matrix_seeds(experiment)
    variants = _matrix_variants(experiment)
    schemes = [str(value) for value in experiment.get("schemes", [])]

    if experiment.get("manifest_sizes"):
        manifest_sizes = [int(value) for value in experiment.get("manifest_sizes", [])]
        default_manifest = _resolved_default_manifest_size(experiment)
        budget = _resolved_default_budget(experiment)
        for topology_id in topologies:
            for scheme in schemes:
                selected_manifest_sizes = manifest_sizes
                if scheme in reference_schemes and default_manifest:
                    selected_manifest_sizes = [default_manifest]
                for manifest_size in selected_manifest_sizes:
                    for seed in seeds:
                        for variant in variants:
                            requested.append(
                                {
                                    "scheme": scheme,
                                    "topology_id": topology_id,
                                    "seed": seed,
                                    "manifest_size": int(manifest_size),
                                    "budget": int(budget),
                                    "variant": variant,
                                }
                            )
        return requested

    budgets = [int(value) for value in experiment.get("budgets", [])]
    default_budget = _resolved_default_budget(experiment)
    manifest_size = _resolved_default_manifest_size(experiment)
    for topology_id in topologies:
        for scheme in schemes:
            selected_budgets = budgets
            if scheme in reference_schemes and default_budget:
                selected_budgets = [default_budget]
            for budget in selected_budgets:
                for seed in seeds:
                    for variant in variants:
                        requested.append(
                            {
                                "scheme": scheme,
                                "topology_id": topology_id,
                                "seed": seed,
                                "manifest_size": int(manifest_size),
                                "budget": int(budget),
                                "variant": variant,
                            }
                        )
    return requested


def _validate_run(experiment_path: Path, output_path: Path, dry_run: bool, extra_args: list[str]) -> None:
    _run(
        [PYTHON, str(repo_root() / "tools/validate_run.py"), "--experiment", str(experiment_path), "--mode", "dry", *extra_args],
        output_path=output_path,
        dry_run=dry_run,
    )


def _run_experiment(
    experiment_path: Path,
    output_path: Path,
    dry_run: bool,
    mode: str,
    extra_args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> str:
    return _run(
        [PYTHON, str(repo_root() / "scripts/run/run_experiment.py"), "--experiment", str(experiment_path), "--mode", mode, *extra_args],
        output_path=output_path,
        dry_run=dry_run,
        env=env,
    )


def _experiment_entry_extra_args(entry: dict[str, Any]) -> list[str]:
    extra_args = ["--scheme", str(entry["scheme"]), "--seed", str(entry["seed"])]
    if int(entry.get("manifest_size", 0) or 0):
        extra_args.extend(["--manifest-size", str(int(entry["manifest_size"]))])
    if int(entry.get("budget", 0) or 0):
        extra_args.extend(["--budget", str(int(entry["budget"]))])
    variant = str(entry.get("variant", "") or "")
    if variant:
        extra_args.extend(["--variant", variant])
    topology_id = str(entry.get("topology_id", "") or "")
    if topology_id:
        extra_args.extend(["--topology-id", topology_id])
    return extra_args


def _run_experiment_entries_parallel(
    *,
    stage: str,
    experiment_path: Path,
    pending_entries: list[dict[str, Any]],
    validation_dir: Path,
    dry_run: bool,
    mode: str,
    max_workers: int,
    env: dict[str, str] | None,
) -> dict[str, str]:
    if not pending_entries:
        return {}
    if dry_run:
        return {_assignment_key(entry): "DRY_RUN" for entry in pending_entries}

    def _worker(entry: dict[str, Any]) -> tuple[str, str]:
        key = _assignment_key(entry)
        output = _run_experiment(
            experiment_path,
            validation_dir / f"{key.replace('|', '__').replace('=', '-')}.txt",
            dry_run,
            mode,
            _experiment_entry_extra_args(entry),
            env=env,
        )
        return key, _extract_run_id(output)

    run_ids: dict[str, str] = {}
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = {executor.submit(_worker, entry): _assignment_key(entry) for entry in pending_entries}
        for future in as_completed(futures):
            key = futures[future]
            try:
                completed_key, run_id = future.result()
                run_ids[completed_key] = run_id
            except Exception as exc:
                failures.append(f"{key}: {exc}")

    if failures:
        raise RuntimeError(f"{stage} run dispatch failed:\n" + "\n\n".join(failures))
    return run_ids


def _run_matrix(
    experiment_path: Path,
    output_path: Path,
    dry_run: bool,
    mode: str,
    max_workers: int,
    force_rerun: bool,
    *,
    env: dict[str, str] | None = None,
) -> None:
    cmd = [
        PYTHON,
        str(repo_root() / "scripts/run/run_experiment_matrix.py"),
        "--experiment",
        str(experiment_path),
        "--mode",
        mode,
        "--max-workers",
        str(max_workers),
    ]
    if force_rerun:
        cmd.append("--force-rerun")
    _run(cmd, output_path=output_path, dry_run=dry_run, env=env)


def _validate_runtime_slice(experiment_path: Path, output_path: Path, run_ids_file: Path, dry_run: bool) -> None:
    _run(
        [
            PYTHON,
            str(repo_root() / "tools/validate_runtime_slice.py"),
            "--experiment",
            str(experiment_path),
            "--registry-source",
            "runs",
            "--run-ids-file",
            str(run_ids_file),
        ],
        output_path=output_path,
        dry_run=dry_run,
    )


def _validate_manifest_regression(experiment_id: str, scheme: str | None, output_path: Path, run_ids_file: Path, dry_run: bool) -> None:
    cmd = [
        PYTHON,
        str(repo_root() / "tools/validate_manifest_regression.py"),
        "--run-ids-file",
        str(run_ids_file),
        "--experiment-id",
        experiment_id,
    ]
    if scheme:
        cmd.extend(["--scheme", scheme])
    _run(cmd, output_path=output_path, dry_run=dry_run)


def _promote_runs(
    experiment_path: Path,
    output_path: Path,
    run_ids_file: Path,
    dry_run: bool,
    env: dict[str, str] | None,
) -> None:
    _run(
        [
            PYTHON,
            str(repo_root() / "scripts/eval/promote_runs.py"),
            "--experiment",
            str(experiment_path),
            "--run-ids-file",
            str(run_ids_file),
        ],
        output_path=output_path,
        dry_run=dry_run,
        env=env,
    )


def _aggregate_experiment(experiment_path: Path, output_path: Path, run_ids_file: Path, dry_run: bool) -> None:
    _run(
        [
            PYTHON,
            str(repo_root() / "scripts/eval/aggregate_experiment.py"),
            "--experiment",
            str(experiment_path),
            "--run-ids-file",
            str(run_ids_file),
        ],
        output_path=output_path,
        dry_run=dry_run,
    )


def _validate_traceability(
    experiment_path: Path,
    output_path: Path,
    run_ids_file: Path,
    dry_run: bool,
    *,
    registry_source: str,
    aggregate_root: Path | None = None,
) -> None:
    cmd = [
        PYTHON,
        str(repo_root() / "tools/validate_aggregate_traceability.py"),
        "--experiment",
        str(experiment_path),
        "--registry-source",
        registry_source,
        "--run-ids-file",
        str(run_ids_file),
    ]
    if aggregate_root is not None:
        cmd.extend(["--aggregate-root", str(aggregate_root)])
    _run(cmd, output_path=output_path, dry_run=dry_run)


def _plot_experiment(experiment_path: Path, output_path: Path, dry_run: bool) -> None:
    _run(
        [PYTHON, str(repo_root() / "scripts/plots/plot_experiment.py"), "--experiment", str(experiment_path)],
        output_path=output_path,
        dry_run=dry_run,
    )


def _validate_figures(experiment_path: Path, experiment: dict[str, Any], output_path: Path, dry_run: bool) -> None:
    csv_outputs = [str(path) for path in experiment.get("outputs", []) if str(path).endswith(".csv")]
    if dry_run:
        for output in csv_outputs:
            _print_cmd(
                [
                    PYTHON,
                    str(repo_root() / "tools/validate_figures.py"),
                    "--experiment",
                    str(experiment_path),
                    "--aggregate",
                    str(_resolve(output)),
                ]
            )
        print(f"  -> {output_path}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    chunks: list[str] = []
    for output in csv_outputs:
        cmd = [
            PYTHON,
            str(repo_root() / "tools/validate_figures.py"),
            "--experiment",
            str(experiment_path),
            "--aggregate",
            str(_resolve(output)),
        ]
        result = subprocess.run(
            cmd,
            cwd=repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        chunks.append("+ " + " ".join(cmd))
        if stdout:
            chunks.append(stdout.rstrip())
        if stderr:
            chunks.append(stderr.rstrip())
        if result.returncode != 0:
            output_path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")
            raise RuntimeError(f"command failed: {' '.join(cmd)}\n{stdout}{stderr}")
    output_path.write_text("\n".join(chunks).rstrip() + ("\n" if chunks else ""), encoding="utf-8")


def _plot_mainline_figures(output_path: Path, dry_run: bool) -> None:
    _run(
        [PYTHON, str(repo_root() / "scripts/plots/plot_main_figures.py")],
        output_path=output_path,
        dry_run=dry_run,
    )


def _build_quick_summary(experiment_path: Path, stage: str, run_ids_file: Path, output_csv: Path, output_json: Path, dry_run: bool) -> str:
    return _run(
        [
            PYTHON,
            str(repo_root() / "scripts/eval/build_stage_quick_summary.py"),
            "--experiment",
            str(experiment_path),
            "--run-ids-file",
            str(run_ids_file),
            "--output-csv",
            str(output_csv),
            "--decision-json",
            str(output_json),
            "--stage",
            stage,
        ],
        output_path=output_json.with_suffix(".stdout.txt"),
        dry_run=dry_run,
    )


def _build_stage_decision(experiment_path: Path, stage: str, run_ids_file: Path, output_json: Path, dry_run: bool) -> str:
    return _build_stage_decision_with_wiring(experiment_path, stage, run_ids_file, output_json, None, dry_run)


def _build_stage_decision_with_wiring(
    experiment_path: Path,
    stage: str,
    run_ids_file: Path,
    output_json: Path,
    wiring_report: Path | None,
    dry_run: bool,
) -> str:
    cmd = [
        PYTHON,
        str(repo_root() / "scripts/eval/build_stage_decision.py"),
        "--experiment",
        str(experiment_path),
        "--run-ids-file",
        str(run_ids_file),
        "--output-json",
        str(output_json),
        "--stage",
        stage,
    ]
    if wiring_report is not None:
        cmd.extend(["--wiring-report", str(wiring_report)])
    return _run(
        cmd,
        output_path=output_json.with_suffix(".stdout.txt"),
        dry_run=dry_run,
    )


def _validate_manifest_wiring(stage: str, experiment_path: Path, run_ids_file: Path, output_json: Path, output_path: Path, dry_run: bool) -> None:
    _run(
        [
            PYTHON,
            str(repo_root() / "tools/validate_manifest_wiring.py"),
            "--stage",
            stage,
            "--experiment",
            str(experiment_path),
            "--run-ids-file",
            str(run_ids_file),
            "--output-json",
            str(output_json),
        ],
        output_path=output_path,
        dry_run=dry_run,
    )


def _manifest_assignment_key(run_id: str) -> str:
    manifest_path = repo_root() / "runs" / "completed" / run_id / "manifest.yaml"
    if not manifest_path.exists():
        raise RuntimeError(f"missing manifest for run: {run_id}")
    manifest = load_json_yaml(manifest_path)
    return _assignment_key(
        {
            "scheme": manifest.get("scheme", ""),
            "topology_id": manifest.get("topology_id", ""),
            "seed": int(manifest.get("seed", 1) or 1),
            "manifest_size": int(manifest.get("manifest_size", 0) or 0),
            "budget": int(manifest.get("budget", 0) or 0),
            "variant": str(manifest.get("scenario_variant", "") or ""),
        }
    )


def _representative_runs_from_status(status: dict[str, Any]) -> list[str]:
    runs = [run_id for run_id in status.get("representative_runs", []) if run_id]
    if runs:
        return runs
    representative_run = str(status.get("representative_run", "")).strip()
    return [representative_run] if representative_run else []


def _compatibility_files_match(previous_fingerprint: dict[str, Any], current_fingerprint: dict[str, Any]) -> bool:
    def _compatibility_subset(fingerprint: dict[str, Any]) -> set[str]:
        files = [str(path) for path in fingerprint.get("files", [])]
        baseline_files = {path for path in files if path.startswith("configs/baselines/")}
        if baseline_files:
            return baseline_files
        return {
            path
            for path in files
            if path.endswith(".yaml") and not path.endswith("configs/experiments/object_main.yaml") and not path.endswith("configs/experiments/ablation.yaml")
        }

    previous_files = _compatibility_subset(previous_fingerprint)
    current_files = _compatibility_subset(current_fingerprint)
    if not previous_files:
        return True
    return previous_files.issubset(current_files)


def _object_main_allows_ablation(status: dict[str, Any]) -> bool:
    return status.get("stage_decision", status.get("decision", "paused")) in OBJECT_MAIN_ALLOWED_ABLATION_DECISIONS


def _package_stage(stage: str, dry_run: bool) -> None:
    cmd = [PYTHON, str(repo_root() / "tools/package_review_bundle.py"), stage]
    if dry_run:
        cmd.append("--dry-run")
    _run(cmd, dry_run=False)


def _finalize_stage(
    stage: str,
    paths: dict[str, Path],
    status: dict[str, Any],
    checks: list[str],
    *,
    change_scope: str,
    completed_experiments: str,
    known_incomplete_items: str,
    dry_run: bool,
) -> None:
    status["completed_experiments"] = completed_experiments
    stage_decision = str(status.get("stage_decision", "")).strip() or str(status.get("decision", "paused"))
    if stage_decision == "paused" and str(status.get("decision", "paused")).strip() not in ("", "paused"):
        stage_decision = str(status.get("decision", "paused")).strip()
    status["stage_decision"] = stage_decision
    status["decision"] = stage_decision
    if not status.get("representative_run") and status.get("representative_runs"):
        status["representative_run"] = status["representative_runs"][0]
    _save_stage_status(paths, status, dry_run)
    _write_readme(
        paths,
        status=status,
        change_scope=change_scope,
        completed_experiments=completed_experiments,
        known_incomplete_items=known_incomplete_items,
        dry_run=dry_run,
    )
    _write_checks(paths, checks, dry_run)


def _object_main_quick(args: argparse.Namespace) -> dict[str, Any]:
    stage = "object_main_quick"
    paths = _stage_paths(stage)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    previous = _load_stage_status(stage)
    experiment_path, experiment = _load_experiment("object_main")
    requested_matrix = [
        {**entry, "topology_id": experiment["topology_id"], "budget": 0, "variant": ""}
        for entry in OBJECT_MAIN_QUICK_MATRIX
    ]
    simulation_fp = _simulation_fingerprint(experiment_path, experiment, requested_matrix)
    stage_contract_fp = _stage_contract_fingerprint(stage, experiment_path, experiment, requested_matrix)
    rerun_simulation = _simulation_rerun_required(args, previous, dataset_fp, binary_fp, simulation_fp)
    refresh_stage = _stage_refresh_required(args, previous, dataset_fp, binary_fp, simulation_fp, stage_contract_fp)
    if refresh_stage and not args.dry_run:
        _clear_stage_for_rerun(paths)
    for key in ("root", "validation", "runs", "aggregate"):
        paths[key].mkdir(parents=True, exist_ok=True)

    run_env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    status = _current_stage_status(stage, requested_matrix, dataset_fp, binary_fp, simulation_fp, stage_contract_fp, {} if refresh_stage else previous)
    if not rerun_simulation:
        _seed_run_assignments_from_latest(status, experiment, requested_matrix)
    status["inherited_runs"] = []
    status["newly_executed_runs"] = []
    status["skipped_runs"] = []
    checks = [
        "completed_experiments: object_main_quick",
        "decision: paused",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    _validate_run(
        experiment_path,
        paths["validation"] / "object_main_quick_validate_run.txt",
        args.dry_run,
        ["--scheme", "hiroute", "--seed", "1", "--manifest-size", "1"],
    )
    status["validation_status"]["validate_run"] = "PASS"
    checks.append("object_main_quick.validate_run.py PASS")

    pending_entries: list[dict[str, Any]] = []
    for entry in requested_matrix:
        key = _assignment_key(entry)
        existing_run_id = "" if rerun_simulation else _matrix_skip_ok(status, entry)
        if existing_run_id:
            status["run_assignments"][key] = existing_run_id
            status["skipped_runs"].append(existing_run_id)
            _copy_run_to_stage(existing_run_id, paths["runs"], args.dry_run)
            continue
        pending_entries.append(entry)

    executed_run_ids = _run_experiment_entries_parallel(
        stage=stage,
        experiment_path=experiment_path,
        pending_entries=pending_entries,
        validation_dir=paths["validation"],
        dry_run=args.dry_run,
        mode=args.mode,
        max_workers=args.max_workers,
        env=run_env,
    )
    for entry in pending_entries:
        key = _assignment_key(entry)
        run_id = executed_run_ids[key]
        status["run_assignments"][key] = run_id
        if run_id != "DRY_RUN":
            status["newly_executed_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)

    completed_run_ids = [
        run_id
        for run_id in status.get("run_assignments", {}).values()
        if run_id and run_id != "DRY_RUN"
    ]
    status["completed_run_ids"] = sorted(dict.fromkeys(completed_run_ids))
    status["representative_run"] = next(
        (
            status["run_assignments"][_assignment_key(entry)]
            for entry in requested_matrix
            if entry["scheme"] == "hiroute" and entry["manifest_size"] == 1 and _assignment_key(entry) in status["run_assignments"]
        ),
        "",
    )
    if status["representative_run"]:
        status["representative_runs"] = [status["representative_run"]]
        checks.append(f"representative_run: {status['representative_run']}")

    run_ids_file = _write_run_ids_file(paths, "run_ids.txt", status["completed_run_ids"], args.dry_run)
    _validate_runtime_slice(
        experiment_path,
        paths["validation"] / "object_main_quick_validate_runtime_slice.txt",
        run_ids_file,
        args.dry_run,
    )
    status["validation_status"]["validate_runtime_slice"] = "PASS"
    checks.append("object_main_quick.validate_runtime_slice.py PASS")

    _validate_manifest_regression(
        "object_main",
        None,
        paths["validation"] / "object_main_quick_validate_manifest_regression.txt",
        run_ids_file,
        args.dry_run,
    )
    status["validation_status"]["validate_manifest_regression"] = "PASS"
    checks.append("object_main_quick.validate_manifest_regression.py PASS")

    summary_csv = paths["aggregate"] / "object_main_quick_summary.csv"
    decision_json = paths["aggregate"] / "object_main_quick_decision.json"
    _build_quick_summary(experiment_path, stage, run_ids_file, summary_csv, decision_json, args.dry_run)
    if not args.dry_run:
        decision_payload = _load_json(decision_json)
        status["decision"] = decision_payload["decision"]
        status["stage_decision"] = decision_payload["decision"]
        status["representative_run"] = decision_payload.get("representative_run", status["representative_run"])
        status["representative_runs"] = [status["representative_run"]] if status["representative_run"] else []
        status["figure_guidance"] = []
        status["recommend_next_stage"] = "object_main" if status["stage_decision"] == "proceed_full_object_main" else "stop"
    status["aggregate_outputs"] = [str(summary_csv.relative_to(repo_root()))]
    checks[1] = f"decision: {status['decision']}"

    _validate_traceability(
        experiment_path,
        paths["validation"] / "object_main_quick_validate_aggregate_traceability.txt",
        run_ids_file,
        args.dry_run,
        registry_source="runs",
        aggregate_root=paths["aggregate"],
    )
    status["validation_status"]["validate_aggregate_traceability"] = "PASS"
    checks.append("object_main_quick.validate_aggregate_traceability.py PASS")

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Sparse quick gate for object_main plus fresh stage-local summary and decision.",
        completed_experiments="object_main_quick",
        known_incomplete_items="object_main, ablation_quick, ablation, routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _object_main_full(args: argparse.Namespace) -> dict[str, Any]:
    quick_status = _load_stage_status("object_main_quick")
    if quick_status.get("decision") != "proceed_full_object_main":
        raise RuntimeError("object_main quick gate has not produced decision=proceed_full_object_main")

    stage = "object_main"
    paths = _stage_paths(stage)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    previous = _load_stage_status(stage)
    experiment_path, experiment = _load_experiment("object_main")
    requested_matrix = [
        {
            "scheme": scheme,
            "topology_id": experiment["topology_id"],
            "seed": 1,
            "manifest_size": manifest_size,
            "budget": 0,
            "variant": "",
        }
        for scheme in experiment["schemes"]
        for manifest_size in experiment["manifest_sizes"]
    ]
    simulation_fp = _simulation_fingerprint(experiment_path, experiment, requested_matrix)
    stage_contract_fp = _stage_contract_fingerprint(stage, experiment_path, experiment, requested_matrix)
    rerun_simulation = _simulation_rerun_required(args, previous, dataset_fp, binary_fp, simulation_fp)
    refresh_stage = _stage_refresh_required(args, previous, dataset_fp, binary_fp, simulation_fp, stage_contract_fp)
    if refresh_stage and not args.dry_run:
        _clear_stage_for_rerun(paths)
    for key in ("root", "validation", "runs", "aggregate"):
        paths[key].mkdir(parents=True, exist_ok=True)

    quick_requested_matrix = [
        {
            "scheme": str(entry.get("scheme", "")),
            "topology_id": str(entry.get("topology_id", experiment["topology_id"])),
            "seed": int(entry.get("seed", 1)),
            "manifest_size": int(entry.get("manifest_size", 0)),
            "budget": int(entry.get("budget", 0)),
            "variant": str(entry.get("variant", "")),
        }
        for entry in (quick_status.get("requested_matrix") or OBJECT_MAIN_QUICK_MATRIX)
    ]
    quick_simulation_fp = _simulation_fingerprint(experiment_path, experiment, quick_requested_matrix)
    if not args.force_rerun:
        validation_mismatches = [
            key for key in QUICK_REQUIRED_VALIDATIONS if quick_status.get("validation_status", {}).get(key) != "PASS"
        ]
        if validation_mismatches:
            raise RuntimeError(f"validation mismatch: object_main_quick missing PASS for {validation_mismatches}")
        if quick_status.get("dataset_fingerprint", {}).get("sha256") != dataset_fp["sha256"]:
            raise RuntimeError("fingerprint mismatch: object_main_quick dataset_fingerprint differs from current full stage")
        if quick_status.get("binary_fingerprint", {}).get("sha256") != binary_fp["sha256"]:
            raise RuntimeError("fingerprint mismatch: object_main_quick binary_fingerprint differs from current full stage")
        stored_quick_simulation_fp = quick_status.get("simulation_fingerprint", {}) or {}
        if stored_quick_simulation_fp:
            if stored_quick_simulation_fp.get("sha256") != quick_simulation_fp["sha256"]:
                raise RuntimeError("fingerprint mismatch: object_main_quick simulation_fingerprint differs from current full stage")
        else:
            quick_experiment_fp = quick_status.get("experiment_fingerprint") or {}
            current_quick_fp = {
                "files": quick_simulation_fp.get("files", []),
            }
            if quick_experiment_fp and not _compatibility_files_match(quick_experiment_fp, current_quick_fp):
                raise RuntimeError("fingerprint mismatch: object_main_quick baseline config set differs from current full stage")

    run_env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    status = _current_stage_status(stage, requested_matrix, dataset_fp, binary_fp, simulation_fp, stage_contract_fp, {} if refresh_stage else previous)
    if not rerun_simulation:
        _seed_run_assignments_from_latest(status, experiment, requested_matrix)
    status["inherited_runs"] = []
    status["newly_executed_runs"] = []
    status["skipped_runs"] = []
    checks = [
        "completed_experiments: object_main",
        "decision: paused",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    _validate_run(
        experiment_path,
        paths["validation"] / "object_main_validate_run.txt",
        args.dry_run,
        ["--scheme", "hiroute", "--seed", "1", "--manifest-size", "1"],
    )
    status["validation_status"]["validate_run"] = "PASS"
    checks.append("object_main.validate_run.py PASS")

    quick_inherited_map: dict[str, str] = {}
    if not args.force_rerun:
        expected_quick_keys = {_assignment_key(entry) for entry in quick_requested_matrix}
        for key in sorted(expected_quick_keys):
            run_id = str(quick_status.get("run_assignments", {}).get(key, "")).strip()
            if not run_id:
                raise RuntimeError(f"assignment mismatch: object_main_quick missing run for {key}")
            if _manifest_assignment_key(run_id) != key:
                raise RuntimeError(f"assignment mismatch: object_main_quick run {run_id} does not match {key}")
            quick_inherited_map[key] = run_id

    dispatch_lines = []
    pending_entries: list[dict[str, Any]] = []
    for entry in requested_matrix:
        key = _assignment_key(entry)
        if key in quick_inherited_map:
            run_id = quick_inherited_map[key]
            status["run_assignments"][key] = run_id
            status["inherited_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)
            dispatch_lines.append(f"inherited {key} -> {run_id}")
            continue

        existing_run_id = "" if rerun_simulation else _matrix_skip_ok(status, entry)
        if existing_run_id:
            status["run_assignments"][key] = existing_run_id
            status["skipped_runs"].append(existing_run_id)
            _copy_run_to_stage(existing_run_id, paths["runs"], args.dry_run)
            dispatch_lines.append(f"skipped {key} -> {existing_run_id}")
            continue

        pending_entries.append(entry)

    executed_run_ids = _run_experiment_entries_parallel(
        stage=stage,
        experiment_path=experiment_path,
        pending_entries=pending_entries,
        validation_dir=paths["validation"],
        dry_run=args.dry_run,
        mode=args.mode,
        max_workers=args.max_workers,
        env=run_env,
    )
    for entry in pending_entries:
        key = _assignment_key(entry)
        run_id = executed_run_ids[key]
        status["run_assignments"][key] = run_id
        if run_id != "DRY_RUN":
            status["newly_executed_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)
        dispatch_lines.append(f"execute {key} -> {run_id}")

    if args.dry_run:
        print(
            f"inheritance_summary={len(status['inherited_runs'])} inherited + "
            f"{sum(1 for line in dispatch_lines if line.startswith('execute '))} to run"
        )
        print(f"dispatch_log={paths['validation'] / 'object_main_run_experiment_matrix.txt'}")
        for line in dispatch_lines:
            print(f"DISPATCH {line}")
    else:
        (paths["validation"] / "object_main_run_experiment_matrix.txt").write_text(
            "\n".join(dispatch_lines) + ("\n" if dispatch_lines else ""),
            encoding="utf-8",
        )
    status["validation_status"]["run_experiment_matrix"] = "PASS"
    checks.append("object_main.run_experiment_matrix.py PASS")

    completed_run_ids = [
        run_id
        for run_id in status.get("run_assignments", {}).values()
        if run_id and run_id != "DRY_RUN"
    ]
    status["completed_run_ids"] = sorted(dict.fromkeys(completed_run_ids))
    if not args.dry_run and len(status["completed_run_ids"]) != len(requested_matrix):
        missing = [
            _assignment_key(entry)
            for entry in requested_matrix
            if status["run_assignments"].get(_assignment_key(entry), "") in ("", "DRY_RUN")
        ]
        raise RuntimeError(f"object_main full stage is missing completed runs for: {missing}")

    run_ids_file = _write_run_ids_file(paths, "run_ids.txt", status.get("completed_run_ids", []), args.dry_run)
    _validate_runtime_slice(experiment_path, paths["validation"] / "object_main_validate_runtime_slice.txt", run_ids_file, args.dry_run)
    status["validation_status"]["validate_runtime_slice"] = "PASS"
    checks.append("object_main.validate_runtime_slice.py PASS")

    _validate_manifest_regression("object_main", None, paths["validation"] / "object_main_validate_manifest_regression.txt", run_ids_file, args.dry_run)
    status["validation_status"]["validate_manifest_regression"] = "PASS"
    checks.append("object_main.validate_manifest_regression.py PASS")

    env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    _promote_runs(experiment_path, paths["validation"] / "object_main_promote_runs.txt", run_ids_file, args.dry_run, env)
    status["validation_status"]["promote_runs"] = "PASS"
    checks.append("object_main.promote_runs.py PASS")

    _aggregate_experiment(experiment_path, paths["validation"] / "object_main_aggregate_experiment.txt", run_ids_file, args.dry_run)
    status["validation_status"]["aggregate_experiment"] = "PASS"
    checks.append("object_main.aggregate_experiment.py PASS")

    _validate_traceability(
        experiment_path,
        paths["validation"] / "object_main_validate_aggregate_traceability.txt",
        run_ids_file,
        args.dry_run,
        registry_source="promoted",
    )
    status["validation_status"]["validate_aggregate_traceability"] = "PASS"
    checks.append("object_main.validate_aggregate_traceability.py PASS")

    wiring_report = paths["aggregate"] / "object_main_manifest_wiring_report.json"
    _validate_manifest_wiring(
        stage,
        experiment_path,
        run_ids_file,
        wiring_report,
        paths["validation"] / "object_main_validate_manifest_wiring.txt",
        args.dry_run,
    )
    status["validation_status"]["validate_manifest_wiring"] = "PASS"
    checks.append("object_main.validate_manifest_wiring.py PASS")

    _plot_experiment(experiment_path, paths["validation"] / "object_main_plot_experiment.txt", args.dry_run)
    status["validation_status"]["plot_experiment"] = "PASS"
    checks.append("object_main.plot_experiment.py PASS")

    _validate_figures(experiment_path, experiment, paths["validation"] / "object_main_validate_figures.txt", args.dry_run)
    status["validation_status"]["validate_figures"] = "PASS"
    checks.append("object_main.validate_figures.py PASS")

    decision_json = paths["aggregate"] / "object_main_decision.json"
    _build_stage_decision_with_wiring(experiment_path, stage, run_ids_file, decision_json, wiring_report, args.dry_run)
    if not args.dry_run:
        decision_payload = _load_json(decision_json)
        status["decision"] = decision_payload["decision"]
        status["stage_decision"] = decision_payload["decision"]
        status["figure_guidance"] = list(decision_payload.get("figure_guidance", []))
        status["representative_runs"] = list(decision_payload.get("representative_runs", []))
        status["representative_run"] = status["representative_runs"][0] if status["representative_runs"] else ""
        status["recommend_next_stage"] = str(decision_payload.get("recommend_next_stage", ""))
    status["aggregate_outputs"] = [
        "results/aggregate/mainline/object_main_manifest_sweep.csv",
        "results/aggregate/mainline/failure_breakdown.csv",
        str(wiring_report.relative_to(repo_root())),
        str(decision_json.relative_to(repo_root())),
        str(decision_json.with_suffix(".stdout.txt").relative_to(repo_root())),
    ]
    checks[1] = f"decision: {status['decision']}"
    checks.append(f"inherited_from_quick: {'yes' if status['inherited_runs'] else 'no'}")
    checks.append(f"inherited_run_count: {len(status['inherited_runs'])}")
    checks.append(f"newly_executed_run_count: {len(status['newly_executed_runs'])}")
    if status.get("figure_guidance"):
        checks.append(f"figure_guidance: {_csv_line(list(status['figure_guidance']))}")
    if status.get("recommend_next_stage"):
        checks.append(f"recommend_next_stage: {status['recommend_next_stage']}")
    representative_runs = _representative_runs_from_status(status)
    if representative_runs:
        checks.append(f"representative_runs: {_csv_line(representative_runs)}")
    if status["representative_run"]:
        checks.append(f"representative_run: {status['representative_run']}")

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Full object_main stage after quick inheritance, with official aggregate refresh and stage-local Figure 5 decision artifacts.",
        completed_experiments="object_main",
        known_incomplete_items="ablation_quick, ablation, routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _ablation_quick(args: argparse.Namespace) -> dict[str, Any]:
    object_status = _load_stage_status("object_main")
    object_decision = object_status.get("stage_decision", object_status.get("decision", "paused"))
    if object_decision not in OBJECT_MAIN_ALLOWED_ABLATION_DECISIONS:
        raise RuntimeError("object_main full stage has not confirmed a usable signal for ablation_quick")

    stage = "ablation_quick"
    paths = _stage_paths(stage)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    previous = _load_stage_status(stage)
    experiment_path, experiment = _load_experiment("ablation")
    requested_matrix = [
        {**entry, "topology_id": experiment["topology_id"], "budget": 0, "variant": ""}
        for entry in ABLATION_QUICK_MATRIX
    ]
    simulation_fp = _simulation_fingerprint(experiment_path, experiment, requested_matrix)
    stage_contract_fp = _stage_contract_fingerprint(stage, experiment_path, experiment, requested_matrix)
    rerun_simulation = _simulation_rerun_required(args, previous, dataset_fp, binary_fp, simulation_fp)
    refresh_stage = _stage_refresh_required(args, previous, dataset_fp, binary_fp, simulation_fp, stage_contract_fp)
    if refresh_stage and not args.dry_run:
        _clear_stage_for_rerun(paths)
    for key in ("root", "validation", "runs", "aggregate"):
        paths[key].mkdir(parents=True, exist_ok=True)

    run_env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    status = _current_stage_status(stage, requested_matrix, dataset_fp, binary_fp, simulation_fp, stage_contract_fp, {} if refresh_stage else previous)
    if not rerun_simulation:
        _seed_run_assignments_from_latest(status, experiment, requested_matrix)
    status["inherited_runs"] = []
    status["newly_executed_runs"] = []
    status["skipped_runs"] = []
    checks = [
        "completed_experiments: ablation_quick",
        "decision: paused",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    _validate_run(
        experiment_path,
        paths["validation"] / "ablation_quick_validate_run.txt",
        args.dry_run,
        ["--scheme", "full_hiroute", "--seed", "1", "--manifest-size", "1"],
    )
    status["validation_status"]["validate_run"] = "PASS"
    checks.append("ablation_quick.validate_run.py PASS")

    pending_entries: list[dict[str, Any]] = []
    for entry in requested_matrix:
        key = _assignment_key(entry)
        existing_run_id = "" if rerun_simulation else _matrix_skip_ok(status, entry)
        if existing_run_id:
            status["run_assignments"][key] = existing_run_id
            status["skipped_runs"].append(existing_run_id)
            _copy_run_to_stage(existing_run_id, paths["runs"], args.dry_run)
            continue
        pending_entries.append(entry)

    executed_run_ids = _run_experiment_entries_parallel(
        stage=stage,
        experiment_path=experiment_path,
        pending_entries=pending_entries,
        validation_dir=paths["validation"],
        dry_run=args.dry_run,
        mode=args.mode,
        max_workers=args.max_workers,
        env=run_env,
    )
    for entry in pending_entries:
        key = _assignment_key(entry)
        run_id = executed_run_ids[key]
        status["run_assignments"][key] = run_id
        if run_id != "DRY_RUN":
            status["newly_executed_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)

    status["completed_run_ids"] = sorted(
        {
            run_id
            for run_id in status.get("run_assignments", {}).values()
            if run_id and run_id != "DRY_RUN"
        }
    )
    status["representative_run"] = next(
        (run_id for key, run_id in status["run_assignments"].items() if "scheme=full_hiroute" in key and "manifest_size=1" in key),
        "",
    )
    if status["representative_run"]:
        status["representative_runs"] = [status["representative_run"]]
        checks.append(f"representative_run: {status['representative_run']}")

    run_ids_file = _write_run_ids_file(paths, "run_ids.txt", status["completed_run_ids"], args.dry_run)
    _validate_runtime_slice(experiment_path, paths["validation"] / "ablation_quick_validate_runtime_slice.txt", run_ids_file, args.dry_run)
    status["validation_status"]["validate_runtime_slice"] = "PASS"
    checks.append("ablation_quick.validate_runtime_slice.py PASS")

    summary_csv = paths["aggregate"] / "ablation_quick_summary.csv"
    decision_json = paths["aggregate"] / "ablation_quick_decision.json"
    _build_quick_summary(experiment_path, stage, run_ids_file, summary_csv, decision_json, args.dry_run)
    if not args.dry_run:
        decision_payload = _load_json(decision_json)
        status["decision"] = decision_payload["decision"]
        status["stage_decision"] = decision_payload["decision"]
        status["representative_run"] = decision_payload.get("representative_run", status["representative_run"])
        status["representative_runs"] = [status["representative_run"]] if status["representative_run"] else []
        status["figure_guidance"] = []
        status["recommend_next_stage"] = "ablation" if status["stage_decision"] == "proceed_full_ablation" else "stop"
    status["aggregate_outputs"] = [str(summary_csv.relative_to(repo_root()))]
    checks[1] = f"decision: {status['decision']}"

    _validate_traceability(
        experiment_path,
        paths["validation"] / "ablation_quick_validate_aggregate_traceability.txt",
        run_ids_file,
        args.dry_run,
        registry_source="runs",
        aggregate_root=paths["aggregate"],
    )
    status["validation_status"]["validate_aggregate_traceability"] = "PASS"
    checks.append("ablation_quick.validate_aggregate_traceability.py PASS")
    checks.append("ablation_quick.validate_manifest_regression.py SKIPPED (single manifest size)")
    checks.append("inherited_from_quick: no")
    checks.append(f"inherited_run_count: {len(status['inherited_runs'])}")
    checks.append(f"newly_executed_run_count: {len(status['newly_executed_runs'])}")
    if status.get("recommend_next_stage"):
        checks.append(f"recommend_next_stage: {status['recommend_next_stage']}")
    if status.get("representative_runs"):
        checks.append(f"representative_runs: {_csv_line(list(status['representative_runs']))}")

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Sparse quick gate for ablation after object_main recovery.",
        completed_experiments="ablation_quick",
        known_incomplete_items="ablation, routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _ablation_full(args: argparse.Namespace) -> dict[str, Any]:
    quick_status = _load_stage_status("ablation_quick")
    if quick_status.get("decision") != "proceed_full_ablation":
        raise RuntimeError("ablation quick gate has not produced decision=proceed_full_ablation")

    stage = "ablation"
    paths = _stage_paths(stage)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    previous = _load_stage_status(stage)
    experiment_path, experiment = _load_experiment("ablation")
    requested_matrix = [
        {
            "scheme": scheme,
            "topology_id": experiment["topology_id"],
            "seed": 1,
            "manifest_size": manifest_size,
            "budget": 0,
            "variant": "",
        }
        for scheme in experiment["schemes"]
        for manifest_size in experiment["manifest_sizes"]
    ]
    simulation_fp = _simulation_fingerprint(experiment_path, experiment, requested_matrix)
    stage_contract_fp = _stage_contract_fingerprint(stage, experiment_path, experiment, requested_matrix)
    rerun_simulation = _simulation_rerun_required(args, previous, dataset_fp, binary_fp, simulation_fp)
    refresh_stage = _stage_refresh_required(args, previous, dataset_fp, binary_fp, simulation_fp, stage_contract_fp)
    if refresh_stage and not args.dry_run:
        _clear_stage_for_rerun(paths)
    for key in ("root", "validation", "runs", "aggregate"):
        paths[key].mkdir(parents=True, exist_ok=True)

    quick_requested_matrix = [
        {
            "scheme": str(entry.get("scheme", "")),
            "topology_id": str(entry.get("topology_id", experiment["topology_id"])),
            "seed": int(entry.get("seed", 1)),
            "manifest_size": int(entry.get("manifest_size", 0)),
            "budget": int(entry.get("budget", 0)),
            "variant": str(entry.get("variant", "")),
        }
        for entry in (quick_status.get("requested_matrix") or ABLATION_QUICK_MATRIX)
    ]
    quick_simulation_fp = _simulation_fingerprint(experiment_path, experiment, quick_requested_matrix)
    if not args.force_rerun:
        validation_mismatches = [
            key for key in ABLATION_QUICK_REQUIRED_VALIDATIONS if quick_status.get("validation_status", {}).get(key) != "PASS"
        ]
        if validation_mismatches:
            raise RuntimeError(f"validation mismatch: ablation_quick missing PASS for {validation_mismatches}")
        if quick_status.get("dataset_fingerprint", {}).get("sha256") != dataset_fp["sha256"]:
            raise RuntimeError("fingerprint mismatch: ablation_quick dataset_fingerprint differs from current full stage")
        if quick_status.get("binary_fingerprint", {}).get("sha256") != binary_fp["sha256"]:
            raise RuntimeError("fingerprint mismatch: ablation_quick binary_fingerprint differs from current full stage")
        stored_quick_simulation_fp = quick_status.get("simulation_fingerprint", {}) or {}
        if stored_quick_simulation_fp:
            if stored_quick_simulation_fp.get("sha256") != quick_simulation_fp["sha256"]:
                raise RuntimeError("fingerprint mismatch: ablation_quick simulation_fingerprint differs from current full stage")
        else:
            quick_experiment_fp = quick_status.get("experiment_fingerprint") or {}
            current_quick_fp = {
                "files": quick_simulation_fp.get("files", []),
            }
            if quick_experiment_fp and not _compatibility_files_match(quick_experiment_fp, current_quick_fp):
                raise RuntimeError("fingerprint mismatch: ablation_quick baseline config set differs from current full stage")

    run_env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    status = _current_stage_status(stage, requested_matrix, dataset_fp, binary_fp, simulation_fp, stage_contract_fp, {} if refresh_stage else previous)
    if not rerun_simulation:
        _seed_run_assignments_from_latest(status, experiment, requested_matrix)
    status["inherited_runs"] = []
    status["newly_executed_runs"] = []
    status["skipped_runs"] = []
    checks = [
        "completed_experiments: ablation",
        "decision: paused",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    _validate_run(
        experiment_path,
        paths["validation"] / "ablation_validate_run.txt",
        args.dry_run,
        ["--scheme", "full_hiroute", "--seed", "1", "--manifest-size", "1"],
    )
    status["validation_status"]["validate_run"] = "PASS"
    checks.append("ablation.validate_run.py PASS")

    quick_inherited_map: dict[str, str] = {}
    if not args.force_rerun:
        expected_quick_keys = {_assignment_key(entry) for entry in quick_requested_matrix}
        for key in sorted(expected_quick_keys):
            run_id = str(quick_status.get("run_assignments", {}).get(key, "")).strip()
            if not run_id:
                raise RuntimeError(f"assignment mismatch: ablation_quick missing run for {key}")
            if _manifest_assignment_key(run_id) != key:
                raise RuntimeError(f"assignment mismatch: ablation_quick run {run_id} does not match {key}")
            quick_inherited_map[key] = run_id

    dispatch_lines = []
    pending_entries: list[dict[str, Any]] = []
    for entry in requested_matrix:
        key = _assignment_key(entry)
        if key in quick_inherited_map:
            run_id = quick_inherited_map[key]
            status["run_assignments"][key] = run_id
            status["inherited_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)
            dispatch_lines.append(f"inherited {key} -> {run_id}")
            continue

        existing_run_id = "" if rerun_simulation else _matrix_skip_ok(status, entry)
        if existing_run_id:
            status["run_assignments"][key] = existing_run_id
            status["skipped_runs"].append(existing_run_id)
            _copy_run_to_stage(existing_run_id, paths["runs"], args.dry_run)
            dispatch_lines.append(f"skipped {key} -> {existing_run_id}")
            continue

        pending_entries.append(entry)

    executed_run_ids = _run_experiment_entries_parallel(
        stage=stage,
        experiment_path=experiment_path,
        pending_entries=pending_entries,
        validation_dir=paths["validation"],
        dry_run=args.dry_run,
        mode=args.mode,
        max_workers=args.max_workers,
        env=run_env,
    )
    for entry in pending_entries:
        key = _assignment_key(entry)
        run_id = executed_run_ids[key]
        status["run_assignments"][key] = run_id
        if run_id != "DRY_RUN":
            status["newly_executed_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)
        dispatch_lines.append(f"execute {key} -> {run_id}")

    if args.dry_run:
        print(
            f"inheritance_summary={len(status['inherited_runs'])} inherited + "
            f"{sum(1 for line in dispatch_lines if line.startswith('execute '))} to run"
        )
        print(f"dispatch_log={paths['validation'] / 'ablation_run_experiment_matrix.txt'}")
        for line in dispatch_lines:
            print(f"DISPATCH {line}")
    else:
        (paths["validation"] / "ablation_run_experiment_matrix.txt").write_text(
            "\n".join(dispatch_lines) + ("\n" if dispatch_lines else ""),
            encoding="utf-8",
        )
    status["validation_status"]["run_experiment_matrix"] = "PASS"
    checks.append("ablation.run_experiment_matrix.py PASS")

    completed_run_ids = [
        run_id
        for run_id in status.get("run_assignments", {}).values()
        if run_id and run_id != "DRY_RUN"
    ]
    status["completed_run_ids"] = sorted(dict.fromkeys(completed_run_ids))
    if not args.dry_run and len(status["completed_run_ids"]) != len(requested_matrix):
        missing = [
            _assignment_key(entry)
            for entry in requested_matrix
            if status["run_assignments"].get(_assignment_key(entry), "") in ("", "DRY_RUN")
        ]
        raise RuntimeError(f"ablation full stage is missing completed runs for: {missing}")

    run_ids_file = _write_run_ids_file(paths, "run_ids.txt", status.get("completed_run_ids", []), args.dry_run)
    _validate_runtime_slice(
        experiment_path,
        paths["validation"] / "ablation_validate_runtime_slice.txt",
        run_ids_file,
        args.dry_run,
    )
    status["validation_status"]["validate_runtime_slice"] = "PASS"
    checks.append("ablation.validate_runtime_slice.py PASS")

    _validate_manifest_regression(
        "ablation",
        None,
        paths["validation"] / "ablation_validate_manifest_regression.txt",
        run_ids_file,
        args.dry_run,
    )
    status["validation_status"]["validate_manifest_regression"] = "PASS"
    checks.append("ablation.validate_manifest_regression.py PASS")

    env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    _promote_runs(experiment_path, paths["validation"] / "ablation_promote_runs.txt", run_ids_file, args.dry_run, env)
    status["validation_status"]["promote_runs"] = "PASS"
    checks.append("ablation.promote_runs.py PASS")

    _aggregate_experiment(experiment_path, paths["validation"] / "ablation_aggregate_experiment.txt", run_ids_file, args.dry_run)
    status["validation_status"]["aggregate_experiment"] = "PASS"
    checks.append("ablation.aggregate_experiment.py PASS")

    _validate_traceability(
        experiment_path,
        paths["validation"] / "ablation_validate_aggregate_traceability.txt",
        run_ids_file,
        args.dry_run,
        registry_source="promoted",
    )
    status["validation_status"]["validate_aggregate_traceability"] = "PASS"
    checks.append("ablation.validate_aggregate_traceability.py PASS")

    wiring_report = paths["aggregate"] / "ablation_manifest_wiring_report.json"
    _validate_manifest_wiring(
        stage,
        experiment_path,
        run_ids_file,
        wiring_report,
        paths["validation"] / "ablation_validate_manifest_wiring.txt",
        args.dry_run,
    )
    status["validation_status"]["validate_manifest_wiring"] = "PASS"
    checks.append("ablation.validate_manifest_wiring.py PASS")

    _plot_experiment(experiment_path, paths["validation"] / "ablation_plot_experiment.txt", args.dry_run)
    status["validation_status"]["plot_experiment"] = "PASS"
    checks.append("ablation.plot_experiment.py PASS")

    _validate_figures(experiment_path, experiment, paths["validation"] / "ablation_validate_figures.txt", args.dry_run)
    status["validation_status"]["validate_figures"] = "PASS"
    checks.append("ablation.validate_figures.py PASS")

    decision_json = paths["aggregate"] / "ablation_decision.json"
    _build_stage_decision_with_wiring(experiment_path, stage, run_ids_file, decision_json, wiring_report, args.dry_run)
    if not args.dry_run:
        decision_payload = _load_json(decision_json)
        status["decision"] = decision_payload["decision"]
        status["stage_decision"] = decision_payload["decision"]
        status["figure_guidance"] = list(decision_payload.get("figure_guidance", []))
        status["representative_runs"] = list(decision_payload.get("representative_runs", []))
        status["representative_run"] = status["representative_runs"][0] if status["representative_runs"] else ""
        status["recommend_next_stage"] = str(decision_payload.get("recommend_next_stage", ""))
    status["aggregate_outputs"] = [
        "results/aggregate/mainline/ablation_summary.csv",
        "results/aggregate/mainline/ablation_summary.trace.json",
        str(wiring_report.relative_to(repo_root())),
        str(decision_json.relative_to(repo_root())),
        str(decision_json.with_suffix(".stdout.txt").relative_to(repo_root())),
    ]
    checks[1] = f"decision: {status['decision']}"
    checks.append(f"inherited_from_quick: {'yes' if status['inherited_runs'] else 'no'}")
    checks.append(f"inherited_run_count: {len(status['inherited_runs'])}")
    checks.append(f"newly_executed_run_count: {len(status['newly_executed_runs'])}")
    if status.get("figure_guidance"):
        checks.append(f"figure_guidance: {_csv_line(list(status['figure_guidance']))}")
    if status.get("recommend_next_stage"):
        checks.append(f"recommend_next_stage: {status['recommend_next_stage']}")
    representative_runs = _representative_runs_from_status(status)
    if representative_runs:
        checks.append(f"representative_runs: {_csv_line(representative_runs)}")
    if status.get("representative_run"):
        checks.append(f"representative_run: {status['representative_run']}")

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Full ablation stage after ablation_quick inheritance, with official aggregate refresh and stage-local Figure 10 decision artifacts.",
        completed_experiments="ablation",
        known_incomplete_items="routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _generic_full_experiment_stage(
    args: argparse.Namespace,
    *,
    stage: str,
    experiment_key: str,
    change_scope: str,
    known_incomplete_items: str,
    require_quick_stage: tuple[str, str] | None = None,
    plot: bool = False,
) -> dict[str, Any]:
    if require_quick_stage is not None:
        required_stage, required_decision = require_quick_stage
        gate_status = _load_stage_status(required_stage)
        if gate_status.get("decision") != required_decision:
            raise RuntimeError(f"{required_stage} has not produced decision={required_decision}")

    paths = _stage_paths(stage)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    previous = _load_stage_status(stage)

    experiment_path, experiment = _load_experiment(experiment_key)
    run_env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    requested_matrix = _generic_requested_matrix(experiment)
    simulation_fp = _simulation_fingerprint(experiment_path, experiment, requested_matrix)
    stage_contract_fp = _stage_contract_fingerprint(stage, experiment_path, experiment, requested_matrix)
    rerun_simulation = _simulation_rerun_required(args, previous, dataset_fp, binary_fp, simulation_fp)
    refresh_stage = _stage_refresh_required(args, previous, dataset_fp, binary_fp, simulation_fp, stage_contract_fp)
    if refresh_stage and not args.dry_run:
        _clear_stage_for_rerun(paths)
    for key in ("root", "validation", "runs", "aggregate"):
        paths[key].mkdir(parents=True, exist_ok=True)
    status = _current_stage_status(stage, requested_matrix, dataset_fp, binary_fp, simulation_fp, stage_contract_fp, {} if refresh_stage else previous)
    if not rerun_simulation:
        _seed_run_assignments_from_latest(status, experiment, requested_matrix)
    status["inherited_runs"] = []
    status["newly_executed_runs"] = []
    status["skipped_runs"] = []
    checks = [
        f"completed_experiments: {stage}",
        "decision: completed",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    first = requested_matrix[0]
    validate_args = ["--scheme", first["scheme"], "--seed", "1"]
    if first["manifest_size"]:
        validate_args += ["--manifest-size", str(first["manifest_size"])]
    elif first["budget"]:
        validate_args += ["--budget", str(first["budget"])]
    _validate_run(experiment_path, paths["validation"] / f"{stage}_validate_run.txt", args.dry_run, validate_args)
    status["validation_status"]["validate_run"] = "PASS"
    checks.append(f"{stage}.validate_run.py PASS")

    existing_run_map: dict[str, str] = {}
    if not rerun_simulation:
        for entry in requested_matrix:
            key = _assignment_key(entry)
            run_id = _matrix_skip_ok(status, entry)
            if run_id:
                existing_run_map[key] = run_id

    dispatch_lines: list[str] = []
    if not rerun_simulation and len(existing_run_map) == len(requested_matrix):
        for entry in requested_matrix:
            key = _assignment_key(entry)
            dispatch_lines.append(f"skipped {key} -> {existing_run_map[key]}")
        if args.dry_run:
            print(f"reuse_summary={len(existing_run_map)} reused + 0 to run")
        _write_dispatch_log(paths["validation"] / f"{stage}_run_experiment_matrix.txt", dispatch_lines, args.dry_run)
    else:
        if not rerun_simulation:
            missing_count = 0
            for entry in requested_matrix:
                key = _assignment_key(entry)
                if key in existing_run_map:
                    dispatch_lines.append(f"skipped {key} -> {existing_run_map[key]}")
                    continue
                missing_count += 1
                dispatch_lines.append(f"execute {key}")
            if args.dry_run:
                print(f"reuse_summary={len(existing_run_map)} reused + {missing_count} to run")
        _run_matrix(
            experiment_path,
            paths["validation"] / f"{stage}_run_experiment_matrix.txt",
            args.dry_run,
            args.mode,
            args.max_workers,
            rerun_simulation,
            env=run_env,
        )
        if dispatch_lines:
            _write_dispatch_log(paths["validation"] / f"{stage}_run_experiment_dispatch.txt", dispatch_lines, args.dry_run)
    status["validation_status"]["run_experiment_matrix"] = "PASS"
    checks.append(f"{stage}.run_experiment_matrix.py PASS")

    selected_run_map = _selected_latest_runs(experiment, requested_matrix)
    if not args.dry_run and len(selected_run_map) != len(requested_matrix):
        missing = [
            _assignment_key(entry)
            for entry in requested_matrix
            if _assignment_key(entry) not in selected_run_map
        ]
        raise RuntimeError(f"{stage} is missing completed runs for: {missing}")
    if not args.dry_run:
        status["completed_run_ids"] = [selected_run_map[key] for key in sorted(selected_run_map)]
        for entry in requested_matrix:
            key = _assignment_key(entry)
            run_id = selected_run_map.get(key, "")
            if not run_id:
                continue
            status["run_assignments"][key] = run_id
            if key in existing_run_map and not rerun_simulation:
                status["skipped_runs"].append(run_id)
            else:
                status["newly_executed_runs"].append(run_id)
            _copy_run_to_stage(run_id, paths["runs"], args.dry_run)

    run_ids_file = _write_run_ids_file(paths, "run_ids.txt", status.get("completed_run_ids", []), args.dry_run)
    _validate_runtime_slice(experiment_path, paths["validation"] / f"{stage}_validate_runtime_slice.txt", run_ids_file, args.dry_run)
    status["validation_status"]["validate_runtime_slice"] = "PASS"
    checks.append(f"{stage}.validate_runtime_slice.py PASS")

    if experiment.get("manifest_sizes") and len(experiment.get("manifest_sizes", [])) > 1:
        _validate_manifest_regression(experiment["experiment_id"], None, paths["validation"] / f"{stage}_validate_manifest_regression.txt", run_ids_file, args.dry_run)
        status["validation_status"]["validate_manifest_regression"] = "PASS"
        checks.append(f"{stage}.validate_manifest_regression.py PASS")
    else:
        checks.append(f"{stage}.validate_manifest_regression.py SKIPPED")

    env = _run_env(allow_dirty_worktree=args.allow_dirty_worktree)
    _promote_runs(experiment_path, paths["validation"] / f"{stage}_promote_runs.txt", run_ids_file, args.dry_run, env)
    status["validation_status"]["promote_runs"] = "PASS"
    checks.append(f"{stage}.promote_runs.py PASS")

    _aggregate_experiment(experiment_path, paths["validation"] / f"{stage}_aggregate_experiment.txt", run_ids_file, args.dry_run)
    status["validation_status"]["aggregate_experiment"] = "PASS"
    checks.append(f"{stage}.aggregate_experiment.py PASS")

    _validate_traceability(experiment_path, paths["validation"] / f"{stage}_validate_aggregate_traceability.txt", run_ids_file, args.dry_run, registry_source="promoted")
    status["validation_status"]["validate_aggregate_traceability"] = "PASS"
    checks.append(f"{stage}.validate_aggregate_traceability.py PASS")

    if plot:
        _plot_experiment(experiment_path, paths["validation"] / f"{stage}_plot_experiment.txt", args.dry_run)
        status["validation_status"]["plot_experiment"] = "PASS"
        checks.append(f"{stage}.plot_experiment.py PASS")
    else:
        checks.append(f"{stage}.plot_experiment.py SKIPPED")

    _validate_figures(experiment_path, experiment, paths["validation"] / f"{stage}_validate_figures.txt", args.dry_run)
    status["validation_status"]["validate_figures"] = "PASS"
    checks.append(f"{stage}.validate_figures.py PASS")

    if status["completed_run_ids"]:
        status["representative_run"] = status["completed_run_ids"][0]
        checks.append(f"representative_run: {status['representative_run']}")
    checks.append(f"reused_run_count: {len(status['skipped_runs'])}")
    checks.append(f"newly_executed_run_count: {len(status['newly_executed_runs'])}")
    status["aggregate_outputs"] = [str(path) for path in experiment.get("outputs", [])]
    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope=change_scope,
        completed_experiments=stage,
        known_incomplete_items=known_incomplete_items,
        dry_run=args.dry_run,
    )
    return status


def _source_sync(args: argparse.Namespace) -> dict[str, Any]:
    stage = "source_sync"
    paths = _stage_paths(stage)
    for key in ("root", "validation"):
        paths[key].mkdir(parents=True, exist_ok=True)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    status = _current_stage_status(stage, [], dataset_fp, binary_fp, {}, {}, {})
    status["decision"] = "completed"
    checks = [
        "completed_experiments: source_sync",
        "decision: completed",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]

    _run(
        [PYTHON, str(repo_root() / "scripts/build_dataset/audit_query_workloads.py"), "--config", str(_resolve("configs/datasets/smartcity.yaml"))],
        output_path=paths["validation"] / "audit_query_workloads.txt",
        dry_run=args.dry_run,
    )
    checks.append("audit_query_workloads.py PASS")

    _run(
        [PYTHON, str(repo_root() / "scripts/build_dataset/validate_dataset.py"), "--config", str(_resolve("configs/datasets/smartcity.yaml"))],
        output_path=paths["validation"] / "validate_dataset.txt",
        dry_run=args.dry_run,
    )
    checks.append("validate_dataset.py PASS")
    status["validation_status"]["source_sync"] = "PASS"

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Mainline source-sync validation and cache/fingerprint refresh.",
        completed_experiments="source_sync",
        known_incomplete_items="object_main_quick, object_main, ablation_quick, ablation, routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _diagnostic_object_routing(args: argparse.Namespace) -> dict[str, Any]:
    stage = "diagnostic_object_routing"
    paths = _stage_paths(stage)
    for key in ("root", "validation", "audits", "runs"):
        paths[key].mkdir(parents=True, exist_ok=True)
    dataset_action, binary_action, dataset_fp, binary_fp = _ensure_dataset_and_binary(
        dry_run=args.dry_run,
        force_rebuild_dataset=args.force_rebuild_dataset,
        force_rebuild_binary=args.force_rebuild_binary,
    )
    status = _current_stage_status(stage, [], dataset_fp, binary_fp, {}, {}, {})
    status["decision"] = "completed"
    checks = [
        "completed_experiments: diagnostic_object_routing",
        "decision: completed",
        f"cache_status: dataset={dataset_action} binary={binary_action}",
    ]
    _run(
        [
            PYTHON,
            str(repo_root() / "scripts/build_dataset/audit_level0_predicate_coverage.py"),
            "--queries",
            str(_resolve("data/processed/smartcity/rf_3967_exodus/queries_master.csv")),
            "--qrels-domain",
            str(_resolve("data/processed/smartcity/rf_3967_exodus/qrels_domain.csv")),
            "--hslsa",
            str(_resolve("data/processed/smartcity/hslsa_export.csv")),
            "--details-csv",
            str(paths["audits"] / "level0_predicate_coverage_details.csv"),
            "--summary-json",
            str(paths["audits"] / "level0_predicate_coverage_summary.json"),
        ],
        output_path=paths["validation"] / "audit_level0_predicate_coverage.txt",
        dry_run=args.dry_run,
    )
    _run(
        [
            PYTHON,
            str(repo_root() / "scripts/build_dataset/audit_controller_manifest_coverage.py"),
            "--queries",
            str(_resolve("data/processed/smartcity/rf_3967_exodus/queries_master.csv")),
            "--qrels-domain",
            str(_resolve("data/processed/smartcity/rf_3967_exodus/qrels_domain.csv")),
            "--qrels-object",
            str(_resolve("data/processed/smartcity/rf_3967_exodus/qrels_object.csv")),
            "--objects",
            str(_resolve("data/processed/smartcity/objects_master.csv")),
            "--controller-local-index",
            str(_resolve("data/processed/smartcity/controller_local_index.csv")),
            "--hslsa",
            str(_resolve("data/processed/smartcity/hslsa_export.csv")),
            "--details-csv",
            str(paths["audits"] / "controller_manifest_coverage_details.csv"),
            "--summary-json",
            str(paths["audits"] / "controller_manifest_coverage_summary.json"),
        ],
        output_path=paths["validation"] / "audit_controller_manifest_coverage.txt",
        dry_run=args.dry_run,
    )
    checks.append("audit_level0_predicate_coverage.py PASS")
    checks.append("audit_controller_manifest_coverage.py PASS")
    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope="Offline routing/object diagnostics and focused debug evidence.",
        completed_experiments="diagnostic_object_routing",
        known_incomplete_items="object_main_quick, object_main, ablation_quick, ablation, routing_main, state_scaling, robustness, paper_freeze",
        dry_run=args.dry_run,
    )
    return status


def _run_full_mainline_tail(args: argparse.Namespace, *, known_incomplete_items: str) -> None:
    _generic_full_experiment_stage(
        args,
        stage="routing_main",
        experiment_key="routing_main",
        change_scope="Manual routing_main stage after object/ablation recovery.",
        known_incomplete_items=known_incomplete_items,
        plot=True,
    )
    _generic_full_experiment_stage(
        args,
        stage="state_scaling",
        experiment_key="state_scaling",
        change_scope="Mainline state_scaling stage after routing recovery.",
        known_incomplete_items="robustness, paper_freeze" if "paper_freeze" in known_incomplete_items else "robustness",
        plot=True,
    )
    _generic_full_experiment_stage(
        args,
        stage="robustness",
        experiment_key="robustness",
        change_scope="Mainline robustness stage after scaling promotion.",
        known_incomplete_items="paper_freeze" if "paper_freeze" in known_incomplete_items else "",
        plot=True,
    )


def _finalize_full_mainline_figures(stage: str, dry_run: bool) -> None:
    paths = _stage_paths(stage)
    paths["validation"].mkdir(parents=True, exist_ok=True)
    _plot_mainline_figures(paths["validation"] / f"{stage}_plot_main_figures.txt", dry_run)


def _finalize_meta_stage(
    stage: str,
    *,
    change_scope: str,
    completed_experiments: str,
    known_incomplete_items: str,
    dry_run: bool,
    extra_validation_status: dict[str, str] | None = None,
    extra_checks: list[str] | None = None,
) -> None:
    paths = _stage_paths(stage)
    for key in ("root", "validation"):
        paths[key].mkdir(parents=True, exist_ok=True)

    previous = _load_stage_status(stage)
    status = _current_stage_status(
        stage,
        [],
        _sha256(DATASET_FINGERPRINT_FILES),
        _sha256(BINARY_FINGERPRINT_FILES),
        {},
        {},
        previous,
    )
    status["decision"] = "completed"
    status["stage_decision"] = "completed"
    status["validation_status"]["plot_main_figures"] = "PASS"
    if extra_validation_status:
        status["validation_status"].update(extra_validation_status)
    representative_runs: list[str] = []
    for substage in ("object_main", "ablation", "routing_main", "state_scaling", "robustness"):
        representative_runs.extend(_representative_runs_from_status(_load_stage_status(substage)))
    status["representative_runs"] = list(dict.fromkeys(run_id for run_id in representative_runs if run_id))
    status["representative_run"] = status["representative_runs"][0] if status["representative_runs"] else ""
    status["aggregate_outputs"] = [
        str(path.relative_to(repo_root()))
        for path in sorted((_resolve("results/figures/mainline")).glob("fig_*.pdf"))
    ]
    checks = [
        f"completed_experiments: {completed_experiments}",
        "decision: completed",
        f"{stage}.plot_main_figures.py PASS",
    ]
    if extra_checks:
        checks.extend(extra_checks)
    representative_runs = _representative_runs_from_status(status)
    if representative_runs:
        checks.append(f"representative_runs: {_csv_line(representative_runs)}")

    _finalize_stage(
        stage,
        paths,
        status,
        checks,
        change_scope=change_scope,
        completed_experiments=completed_experiments,
        known_incomplete_items=known_incomplete_items,
        dry_run=dry_run,
    )


def main() -> int:
    args = parse_args()
    if args.stage not in STAGES:
        print(f"ERROR: unsupported stage '{args.stage}'", file=sys.stderr)
        return 1

    try:
        if args.stage == "source_sync":
            _source_sync(args)
        elif args.stage == "object_main_quick":
            _object_main_quick(args)
        elif args.stage == "object_main":
            _object_main_full(args)
        elif args.stage == "ablation_quick":
            _ablation_quick(args)
        elif args.stage == "ablation":
            _ablation_full(args)
        elif args.stage == "routing_main":
            _generic_full_experiment_stage(
                args,
                stage="routing_main",
                experiment_key="routing_main",
                change_scope="Manual routing_main stage after object/ablation recovery.",
                known_incomplete_items="state_scaling, robustness, paper_freeze",
                plot=True,
            )
        elif args.stage == "state_scaling":
            _generic_full_experiment_stage(
                args,
                stage="state_scaling",
                experiment_key="state_scaling",
                change_scope="Mainline state_scaling stage after routing recovery.",
                known_incomplete_items="robustness, paper_freeze",
                plot=True,
            )
        elif args.stage == "robustness":
            _generic_full_experiment_stage(
                args,
                stage="robustness",
                experiment_key="robustness",
                change_scope="Mainline robustness stage after scaling promotion.",
                known_incomplete_items="paper_freeze",
                plot=True,
            )
        elif args.stage == "diagnostic_object_routing":
            _diagnostic_object_routing(args)
        elif args.stage == "object_ablation_routing":
            _object_main_quick(args)
            if _load_stage_status("object_main_quick").get("decision") == "proceed_full_object_main":
                _object_main_full(args)
            if _object_main_allows_ablation(_load_stage_status("object_main")):
                _ablation_quick(args)
            if _load_stage_status("ablation_quick").get("decision") == "proceed_full_ablation":
                _ablation_full(args)
        elif args.stage == "full_mainline":
            _object_main_quick(args)
            if _load_stage_status("object_main_quick").get("decision") == "proceed_full_object_main":
                _object_main_full(args)
            if _object_main_allows_ablation(_load_stage_status("object_main")):
                _ablation_quick(args)
            if _load_stage_status("ablation_quick").get("decision") == "proceed_full_ablation":
                _ablation_full(args)
            _run_full_mainline_tail(args, known_incomplete_items="paper_freeze")
            _finalize_full_mainline_figures("full_mainline", args.dry_run)
            _finalize_meta_stage(
                "full_mainline",
                change_scope="Top-level mainline refresh across object_main, ablation, routing_main, state_scaling, and robustness.",
                completed_experiments="object_main_quick, object_main, ablation_quick, ablation, routing_main, state_scaling, robustness",
                known_incomplete_items="paper_freeze",
                dry_run=args.dry_run,
            )
        elif args.stage == "paper_freeze":
            _stage_paths("paper_freeze")["validation"].mkdir(parents=True, exist_ok=True)
            _run(
                [PYTHON, str(repo_root() / "scripts/build_dataset/build_all.py"), "--config", str(_resolve("configs/datasets/smartcity.yaml"))],
                output_path=_stage_paths("paper_freeze")["validation"] / "build_all.txt",
                dry_run=args.dry_run,
            )
            _object_main_quick(args)
            if _load_stage_status("object_main_quick").get("decision") == "proceed_full_object_main":
                _object_main_full(args)
            if _object_main_allows_ablation(_load_stage_status("object_main")):
                _ablation_quick(args)
            if _load_stage_status("ablation_quick").get("decision") == "proceed_full_ablation":
                _ablation_full(args)
            _run_full_mainline_tail(args, known_incomplete_items="")
            _finalize_full_mainline_figures("paper_freeze", args.dry_run)
            _finalize_meta_stage(
                "paper_freeze",
                change_scope="Paper-freeze refresh after full dataset rebuild and all five mainline experiments.",
                completed_experiments="paper_freeze",
                known_incomplete_items="",
                dry_run=args.dry_run,
                extra_validation_status={"build_all": "PASS"},
                extra_checks=["paper_freeze.build_all.py PASS"],
            )

        if (not args.skip_package or args.package) and args.stage in PACKAGEABLE_STAGES:
            _package_stage(args.stage, args.dry_run)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
