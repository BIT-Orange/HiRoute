"""Package staged review artifacts into zip bundles with freshness validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import git_head, isoformat_z, read_csv, repo_root

PROJECT_PYTHON_PATH = repo_root() / ".venv" / "bin" / "python"
PYTHON = str(PROJECT_PYTHON_PATH if PROJECT_PYTHON_PATH.exists() else Path(sys.executable))


BUNDLE_CONFIG = {
    "source_sync": {
        "stage_id": "source_sync",
        "manifest": "tools/review_manifests/source_sync.txt",
        "prefix": "hiroute-source-sync",
        "suffix": "",
    },
    "diagnostic_object_routing": {
        "stage_id": "diagnostic_object_routing",
        "manifest": "tools/review_manifests/diagnostic_object_routing.txt",
        "prefix": "hiroute-diagnostic-review",
        "suffix": "-object_routing",
    },
    "object_main_quick": {
        "stage_id": "object_main_quick",
        "manifest": "tools/review_manifests/object_main_quick.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-object_main_quick",
    },
    "object_main": {
        "stage_id": "object_main",
        "manifest": "tools/review_manifests/object_main.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-object_main",
    },
    "ablation_quick": {
        "stage_id": "ablation_quick",
        "manifest": "tools/review_manifests/ablation_quick.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-ablation_quick",
    },
    "ablation": {
        "stage_id": "ablation",
        "manifest": "tools/review_manifests/ablation.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-ablation",
    },
    "run_review_object_ablation_routing": {
        "stage_id": "object_ablation_routing",
        "manifest": "tools/review_manifests/run_review_object_ablation_routing.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-object_ablation_routing",
    },
    "object_ablation_routing": {
        "stage_id": "object_ablation_routing",
        "manifest": "tools/review_manifests/run_review_object_ablation_routing.txt",
        "prefix": "hiroute-run-review",
        "suffix": "-object_ablation_routing",
    },
    "teacher_review": {
        "stage_id": "teacher_review",
        "manifest": "tools/review_manifests/teacher_review.txt",
        "prefix": "hiroute-teacher-review",
        "suffix": "",
        "bundle_type": "teacher",
        "external_review": True,
        "partial_bundle": True,
        "include_note_status": False,
        "included_result_sets": [
            "object_main_sealed",
            "ablation_sealed",
            "routing_support_diagnostic",
        ],
        "excluded_result_sets": [
            "state_scaling",
            "robustness",
            "results_v3",
            "figures_v3",
            "tables_v3",
        ],
        "included_code_paths": [
            "configs/datasets/smartcity.yaml",
            "configs/hierarchy/hiroute_hkm.yaml",
            "configs/experiments/object_main.yaml",
            "configs/experiments/ablation.yaml",
            "configs/experiments/routing_main.yaml",
            "ns-3/src/ndnSIM/apps/hiroute-controller-app.cpp",
            "ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp",
            "ns-3/src/ndnSIM/model/hiroute-discovery-engine.cpp",
            "ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp",
            "scripts/build_dataset/build_queries_and_qrels.py",
            "scripts/build_dataset/build_hierarchy_and_hslsa.py",
            "scripts/eval/build_stage_decision.py",
            "tools/validate_manifest_wiring.py",
            "tools/package_review_bundle.py",
            "tools/package_review_bundle.sh",
        ],
        "included_paper_files": [
            "paper/main.tex",
            "paper/notes/claim_c001.md",
            "paper/notes/claim_c002.md",
            "paper/notes/claim_c003.md",
            "paper/notes/claim_c004.md",
            "paper/notes/fig_routing_support.md",
        ],
        "stale_note_paths": [
            "paper/notes/fig_object_manifest_sweep.md",
            "paper/notes/fig_ablation.md",
        ],
        "diagnostic_stage_notes": [
            "routing_support is included as diagnostic/support evidence only.",
            "Figure 3 and Figure 5 authority comes from latest stage decisions, not stale paper notes.",
        ],
    },
    "chatgpt_review": {
        "stage_id": "chatgpt_review",
        "manifest": "tools/review_manifests/chatgpt_review.txt",
        "prefix": "hiroute-chatgpt-review",
        "suffix": "",
        "bundle_type": "chatgpt",
        "external_review": True,
        "partial_bundle": False,
        "include_note_status": True,
        "included_result_sets": [
            "object_main_sealed",
            "ablation_sealed",
            "routing_support_diagnostic",
        ],
        "excluded_result_sets": [
            "state_scaling",
            "robustness",
            "results_v3",
            "figures_v3",
            "tables_v3",
        ],
        "included_code_paths": [
            "docs/workflows/mainline_workflow.md",
            "docs/experiments/experiment_matrix.md",
            "docs/datasets/schema_reference.md",
            "configs/datasets/smartcity.yaml",
            "configs/hierarchy/hiroute_hkm.yaml",
            "configs/experiments/object_main.yaml",
            "configs/experiments/ablation.yaml",
            "configs/experiments/routing_main.yaml",
            "scripts/build_dataset/build_queries_and_qrels.py",
            "scripts/build_dataset/audit_query_workloads.py",
            "scripts/build_dataset/build_hierarchy_and_hslsa.py",
            "scripts/eval/build_stage_quick_summary.py",
            "scripts/eval/build_stage_decision.py",
            "scripts/eval/aggregate_experiment.py",
            "scripts/eval/promote_runs.py",
            "scripts/eval/eval_support.py",
            "tools/validate_manifest_wiring.py",
            "tools/validate_manifest_regression.py",
            "tools/validate_runtime_slice.py",
            "tools/validate_aggregate_traceability.py",
            "tools/run_mainline_review_stage.py",
            "tools/run_mainline_review_stage.sh",
            "tools/package_review_bundle.py",
            "tools/package_review_bundle.sh",
            "tools/validate_bundle_freshness.py",
            "ns-3/src/ndnSIM/apps/hiroute-controller-app.cpp",
            "ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp",
            "ns-3/src/ndnSIM/model/hiroute-discovery-engine.cpp",
            "ns-3/src/ndnSIM/model/hiroute-summary-entry.cpp",
        ],
        "included_paper_files": [
            "paper/main.tex",
            "paper/notes/claim_c001.md",
            "paper/notes/claim_c002.md",
            "paper/notes/claim_c003.md",
            "paper/notes/claim_c004.md",
            "paper/notes/fig_object_manifest_sweep.md",
            "paper/notes/fig_ablation.md",
            "paper/notes/fig_routing_support.md",
        ],
        "stale_note_paths": [
            "paper/notes/fig_object_manifest_sweep.md",
            "paper/notes/fig_ablation.md",
        ],
        "diagnostic_stage_notes": [
            "routing_support is included as diagnostic/support evidence only.",
            "fig_object_manifest_sweep.md and fig_ablation.md may lag sealed stage decisions; review *_decision.json and *_manifest_wiring_report.json first.",
        ],
    },
}

SEALED_STAGE_REQUIREMENTS = {
    "object_main": "ready_for_main_figure",
    "ablation": "ready_for_support_figure",
}
ROUTING_SUPPORT_REQUIRED_FILES = [
    "results/aggregate/mainline/routing_support.csv",
    "results/aggregate/mainline/routing_support.trace.json",
    "results/figures/mainline/fig_routing_support.pdf",
    "results/figures/mainline/fig_routing_support.png",
    "paper/notes/fig_routing_support.md",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_key")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else repo_root() / path


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    _write_text(path, json.dumps(payload, indent=2, sort_keys=False) + "\n")


def _stage_root(stage_id: str) -> Path:
    return repo_root() / "review_artifacts" / stage_id


def _git_status_short() -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root()), "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _load_stage_status(stage_id: str) -> dict[str, Any]:
    stage_status_path = _stage_root(stage_id) / "stage_status.json"
    if not stage_status_path.exists():
        raise RuntimeError(f"missing required stage_status.json for {stage_id}: {stage_status_path}")
    return _load_json(stage_status_path)


def _load_required_json(path: str) -> dict[str, Any]:
    resolved = _resolve(path)
    if not resolved.exists():
        raise RuntimeError(f"missing required json artifact: {resolved}")
    return _load_json(resolved)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _copy_path(source: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"{source.relative_to(repo_root())} -> {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, dest, dirs_exist_ok=True)
    else:
        shutil.copy2(source, dest)


def _extract_evaluation_excerpt(source: Path, dest: Path, dry_run: bool) -> None:
    if dry_run:
        print(f"{source.relative_to(repo_root())} [excerpt] -> {dest}")
        return
    lines = source.read_text(encoding="utf-8").splitlines()
    capturing = False
    excerpt_lines: list[str] = []
    for line in lines:
        if line.strip() == "% BEGIN_MAINLINE_EVAL_EXCERPT":
            capturing = True
            continue
        if line.strip() == "% END_MAINLINE_EVAL_EXCERPT":
            capturing = False
            continue
        if capturing:
            excerpt_lines.append(line)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(excerpt_lines) + ("\n" if excerpt_lines else ""), encoding="utf-8")


def _copy_promoted_runs(experiment_id: str, bundle_root: Path, dry_run: bool) -> None:
    run_dir_by_id = {}
    for row in read_csv(repo_root() / "runs" / "registry" / "runs.csv"):
        if row.get("run_dir"):
            run_dir_by_id[row["run_id"]] = row["run_dir"]
    run_ids = [
        row["run_id"]
        for row in read_csv(repo_root() / "runs" / "registry" / "promoted_runs.csv")
        if row["experiment_id"] == experiment_id
    ]
    if not run_ids:
        raise RuntimeError(f"no promoted runs found for {experiment_id}")
    for run_id in run_ids:
        run_dir = repo_root() / run_dir_by_id[run_id]
        dest_dir = bundle_root / run_dir.relative_to(repo_root())
        _copy_path(run_dir, dest_dir, dry_run)


def _copy_run_ids(run_ids: list[str], bundle_root: Path, dry_run: bool) -> None:
    for run_id in run_ids:
        source = repo_root() / "runs" / "completed" / run_id
        if not source.exists():
            raise RuntimeError(f"missing completed run directory for {run_id}: {source}")
        dest = bundle_root / "runs" / run_id
        _copy_path(source, dest, dry_run)


def _collect_external_bundle_state(config: dict[str, Any]) -> dict[str, Any]:
    object_status = _load_stage_status("object_main")
    ablation_status = _load_stage_status("ablation")
    object_decision = str(object_status.get("stage_decision", object_status.get("decision", "")))
    ablation_decision = str(ablation_status.get("stage_decision", ablation_status.get("decision", "")))
    if object_decision != SEALED_STAGE_REQUIREMENTS["object_main"]:
        raise RuntimeError(f"object_main is not sealed as expected: {object_decision}")
    if ablation_decision != SEALED_STAGE_REQUIREMENTS["ablation"]:
        raise RuntimeError(f"ablation is not sealed as expected: {ablation_decision}")

    object_wiring = _load_required_json("review_artifacts/object_main/aggregate/object_main_manifest_wiring_report.json")
    ablation_wiring = _load_required_json("review_artifacts/ablation/aggregate/ablation_manifest_wiring_report.json")
    object_wiring_status = str(object_wiring.get("overall_status", "missing"))
    ablation_wiring_status = str(ablation_wiring.get("overall_status", "missing"))
    if object_wiring_status == "wiring_suspect":
        raise RuntimeError("object_main manifest wiring is wiring_suspect")
    if ablation_wiring_status == "wiring_suspect":
        raise RuntimeError("ablation manifest wiring is wiring_suspect")

    for raw_path in ROUTING_SUPPORT_REQUIRED_FILES:
        resolved = _resolve(raw_path)
        if not resolved.exists():
            raise RuntimeError(f"missing required routing support artifact: {resolved}")

    representative_runs = _dedupe(
        list(object_status.get("representative_runs", [])) + list(ablation_status.get("representative_runs", []))
    )
    teacher_run_ids = representative_runs
    chatgpt_run_ids = _dedupe(
        list(object_status.get("completed_run_ids", [])) + list(ablation_status.get("completed_run_ids", []))
    )
    worktree_status = _git_status_short()
    worktree_dirty = bool(worktree_status.strip())

    bundle_type = str(config["bundle_type"])
    completed_run_ids = teacher_run_ids if bundle_type == "teacher" else chatgpt_run_ids
    stage_id = str(config["stage_id"])
    stage_decision = "ready_for_external_review"

    stage_status: dict[str, Any] = {
        "stage": stage_id,
        "git_sha": git_head(),
        "generated_at": isoformat_z(),
        "updated_at": isoformat_z(),
        "completed_experiments": stage_id,
        "decision": stage_decision,
        "stage_decision": stage_decision,
        "figure_guidance": [],
        "recommend_next_stage": "external_review_complete",
        "representative_runs": representative_runs,
        "representative_run": representative_runs[0] if representative_runs else "",
        "completed_run_ids": completed_run_ids,
        "validation_status": {"external_review_metadata": "PASS"},
        "aggregate_outputs": [
            "results/aggregate/mainline/object_main_manifest_sweep.csv",
            "results/aggregate/mainline/failure_breakdown.csv",
            "results/aggregate/mainline/object_main_discovery_reply_stage_matrix.csv",
            "results/aggregate/mainline/object_main_discovery_reply_stage_matrix.trace.json",
            "results/aggregate/mainline/ablation_summary.csv",
            "results/aggregate/mainline/routing_support.csv",
            "review_artifacts/object_main/aggregate/object_main_decision.json",
            "review_artifacts/object_main/aggregate/object_main_manifest_wiring_report.json",
            "review_artifacts/ablation/aggregate/ablation_decision.json",
            "review_artifacts/ablation/aggregate/ablation_manifest_wiring_report.json",
        ],
        "bundle_type": bundle_type,
        "worktree_dirty": worktree_dirty,
        "included_code_paths": list(config["included_code_paths"]),
        "included_result_sets": list(config["included_result_sets"]),
        "included_paper_files": list(config["included_paper_files"]),
        "sealed_stage_decisions": {
            "object_main": object_decision,
            "ablation": ablation_decision,
        },
        "sealed_wiring_statuses": {
            "object_main_manifest_wiring": object_wiring_status,
            "ablation_manifest_wiring": ablation_wiring_status,
        },
        "diagnostic_stage_notes": list(config["diagnostic_stage_notes"]),
        "excluded_result_sets": list(config["excluded_result_sets"]),
        "packaging_assertions": {
            "partial_bundle": bool(config["partial_bundle"]),
            "routing_support_required": True,
            "stale_notes_allowed": bool(config["include_note_status"]),
        },
        "stale_note_paths": list(config["stale_note_paths"]),
        "inherited_runs": [],
        "newly_executed_runs": [],
        "skipped_runs": [],
    }

    return {
        "stage_status": stage_status,
        "worktree_status": worktree_status,
        "object_decision": object_decision,
        "ablation_decision": ablation_decision,
        "object_wiring_status": object_wiring_status,
        "ablation_wiring_status": ablation_wiring_status,
        "teacher_run_ids": teacher_run_ids,
        "chatgpt_run_ids": chatgpt_run_ids,
    }


def _build_external_readme(stage_status: dict[str, Any]) -> str:
    lines = [
        "# External Review Bundle",
        f"bundle_type: {stage_status['bundle_type']}",
        f"current_git_commit: {stage_status['git_sha']}",
        f"completed_experiments: {stage_status['completed_experiments']}",
        f"stage_decision: {stage_status['stage_decision']}",
        f"figure_guidance: {','.join(stage_status.get('figure_guidance', []))}",
        f"representative_runs: {','.join(stage_status.get('representative_runs', []))}",
        f"recommend_next_stage: {stage_status.get('recommend_next_stage', '')}",
        (
            "known_incomplete_items: routing_main remains diagnostic/support only; "
            "state_scaling and robustness are excluded; package reflects the current worktree snapshot"
        ),
        "",
    ]
    return "\n".join(lines)


def _build_external_checks(stage_status: dict[str, Any]) -> str:
    sealed = stage_status["sealed_stage_decisions"]
    wiring = stage_status["sealed_wiring_statuses"]
    lines = [
        f"completed_experiments: {stage_status['completed_experiments']}",
        f"decision: {stage_status['decision']}",
        f"stage_decision: {stage_status['stage_decision']}",
        f"bundle_type: {stage_status['bundle_type']}",
        f"worktree_dirty: {'yes' if stage_status['worktree_dirty'] else 'no'}",
        f"object_main_stage_decision: {sealed['object_main']}",
        f"ablation_stage_decision: {sealed['ablation']}",
        f"object_main_manifest_wiring: {wiring['object_main_manifest_wiring']}",
        f"ablation_manifest_wiring: {wiring['ablation_manifest_wiring']}",
        "routing_support_status: diagnostic/support only",
        f"included_result_sets: {','.join(stage_status['included_result_sets'])}",
        f"excluded_result_sets: {','.join(stage_status['excluded_result_sets'])}",
        f"representative_runs: {','.join(stage_status.get('representative_runs', []))}",
        f"recommend_next_stage: {stage_status.get('recommend_next_stage', '')}",
    ]
    return "\n".join(lines) + "\n"


def _build_review_guide(stage_status: dict[str, Any]) -> str:
    bundle_type = stage_status["bundle_type"]
    extra = (
        "- ChatGPT bundle includes stale figure notes for context; always prioritize `*_decision.json` and `*_manifest_wiring_report.json`.\n"
        if bundle_type == "chatgpt"
        else "- Teacher bundle intentionally omits stale Figure 5/10 notes; use `RESULT_STATUS.md` for the current verdict.\n"
    )
    return (
        "# Review Guide\n\n"
        "## Source of Truth Priority\n"
        "1. Code and experiment configs\n"
        "2. Sealed stage decisions and manifest wiring reports\n"
        "3. Aggregate CSVs, trace JSONs, and representative runs\n"
        "4. `paper/main.tex`\n"
        "5. Legacy notes and old registry context\n\n"
        "## Current Boundary\n"
        "- `object_main` is sealed as the main result.\n"
        "- `ablation` is sealed as a support figure.\n"
        "- `routing_support` is included as diagnostic/support only, not as a sealed headline result.\n"
        "- `state_scaling`, `robustness`, and all `v3` historical outputs are excluded.\n\n"
        "## Review Order\n"
        "1. `RESULT_STATUS.md`\n"
        "2. `review_artifacts/object_main/aggregate/object_main_decision.json` and `review_artifacts/ablation/aggregate/ablation_decision.json` if present\n"
        "3. Mainline aggregate CSVs and trace JSONs\n"
        "4. Representative runs\n"
        "5. Paper draft and notes\n\n"
        "## Notes\n"
        "- This bundle is produced from the current workspace snapshot and may include uncommitted changes.\n"
        "- `WORKTREE_STATUS.txt` records the exact `git status --short` output used at packaging time.\n"
        f"{extra}"
    )


def _build_result_status(stage_status: dict[str, Any]) -> str:
    sealed = stage_status["sealed_stage_decisions"]
    wiring = stage_status["sealed_wiring_statuses"]
    return (
        "# Result Status\n\n"
        f"- `object_main = {sealed['object_main']}`\n"
        f"- `ablation = {sealed['ablation']}`\n"
        f"- `object_main_manifest_wiring = {wiring['object_main_manifest_wiring']}`\n"
        f"- `ablation_manifest_wiring = {wiring['ablation_manifest_wiring']}`\n"
        "- `routing_support = diagnostic/support only`\n\n"
        "Figure 3 and Figure 5 should be interpreted from the latest sealed stage decisions, not from stale paper notes.\n"
    )


def _build_note_status(stage_status: dict[str, Any]) -> str:
    stale_notes = "\n".join(f"- `{path}`" for path in stage_status.get("stale_note_paths", []))
    return (
        "# Note Status\n\n"
        "The following notes may lag the sealed stage decisions and should be treated as contextual, not authoritative:\n\n"
        f"{stale_notes}\n\n"
        "When reviewing, prioritize:\n"
        "1. `review_artifacts/object_main/aggregate/object_main_decision.json`\n"
        "2. `review_artifacts/object_main/aggregate/object_main_manifest_wiring_report.json`\n"
        "3. `review_artifacts/ablation/aggregate/ablation_decision.json`\n"
        "4. `review_artifacts/ablation/aggregate/ablation_manifest_wiring_report.json`\n"
    )


def _prepare_external_review_stage(config: dict[str, Any], stage_root: Path, dry_run: bool) -> None:
    state = _collect_external_bundle_state(config)
    stage_status = state["stage_status"]

    if dry_run:
        print(f"external_stage={stage_status['stage']}")
        print(f"bundle_type={stage_status['bundle_type']}")
        print(f"included_result_sets={','.join(stage_status['included_result_sets'])}")
        print(f"excluded_result_sets={','.join(stage_status['excluded_result_sets'])}")
        print(f"representative_run_count={len(stage_status.get('representative_runs', []))}")
        print(f"completed_run_count={len(stage_status.get('completed_run_ids', []))}")
        return

    stage_root.mkdir(parents=True, exist_ok=True)
    placeholder_files = [
        stage_root / "README.md",
        stage_root / "checks.txt",
        stage_root / "stage_status.json",
        stage_root / "bundle_manifest.json",
        stage_root / "REVIEW_GUIDE.md",
        stage_root / "RESULT_STATUS.md",
        stage_root / "WORKTREE_STATUS.txt",
    ]
    if config.get("include_note_status"):
        placeholder_files.append(stage_root / "NOTE_STATUS.md")
    for path in placeholder_files:
        if path.suffix == ".json":
            _write_text(path, "{}\n")
        else:
            _write_text(path, "")

    state["worktree_status"] = _git_status_short()
    stage_status["worktree_dirty"] = bool(state["worktree_status"].strip())
    review_guide = _build_review_guide(stage_status)
    result_status = _build_result_status(stage_status)
    readme = _build_external_readme(stage_status)
    checks = _build_external_checks(stage_status)
    note_status = _build_note_status(stage_status) if config.get("include_note_status") else ""

    _write_json(stage_root / "stage_status.json", stage_status)
    _write_text(stage_root / "README.md", readme)
    _write_text(stage_root / "checks.txt", checks)
    _write_text(stage_root / "REVIEW_GUIDE.md", review_guide)
    _write_text(stage_root / "RESULT_STATUS.md", result_status)
    _write_text(stage_root / "WORKTREE_STATUS.txt", state["worktree_status"])
    if config.get("include_note_status"):
        _write_text(stage_root / "NOTE_STATUS.md", note_status)
    elif (stage_root / "NOTE_STATUS.md").exists():
        (stage_root / "NOTE_STATUS.md").unlink()


def _scan_run_ids(bundle_root: Path) -> list[str]:
    run_ids = set()
    for manifest_path in bundle_root.glob("runs/*/manifest.yaml"):
        run_ids.add(manifest_path.parent.name)
    for manifest_path in bundle_root.glob("runs/completed/*/manifest.yaml"):
        run_ids.add(manifest_path.parent.name)
    return sorted(run_ids)


def _scan_file_list(bundle_root: Path, subtree_name: str) -> list[str]:
    root = bundle_root / subtree_name
    if not root.exists():
        return []
    return sorted(
        str(path.relative_to(bundle_root))
        for path in root.rglob("*")
        if path.is_file()
    )


def _scan_validation_files(bundle_root: Path) -> list[str]:
    return sorted(
        str(path.relative_to(bundle_root))
        for path in bundle_root.rglob("*")
        if path.is_file() and path.parent.name == "validation"
    )


def _scan_audit_files(bundle_root: Path) -> list[str]:
    audit_files: set[str] = set()
    for path in bundle_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(bundle_root))
        if path.parent.name == "validation":
            continue
        if "audit" in {part.lower() for part in path.parts}:
            audit_files.add(rel)
            continue
        if path.name.endswith("_manifest_wiring_report.json"):
            audit_files.add(rel)
    return sorted(audit_files)


def _key_metrics_digest(bundle_root: Path) -> list[dict[str, object]]:
    candidates = list(bundle_root.glob("aggregate/*.csv")) + list(bundle_root.glob("results/aggregate/**/*.csv"))
    digest: list[dict[str, object]] = []
    for path in sorted(candidates):
        rows = read_csv(path)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.append(
            {
                "path": str(path.relative_to(bundle_root)),
                "row_count": len(rows),
                "sha256": sha,
            }
        )
    return digest


def _build_bundle_manifest(stage_id: str, bundle_root: Path, stage_root: Path) -> dict[str, object]:
    stage_status_path = stage_root / "stage_status.json"
    stage_status = json.loads(stage_status_path.read_text(encoding="utf-8")) if stage_status_path.exists() else {}
    representative_runs = list(stage_status.get("representative_runs", []))
    if not representative_runs and stage_status.get("representative_run"):
        representative_runs = [str(stage_status["representative_run"])]
    packaging_assertions = {
        "partial_bundle": False,
        "stage_status_present": stage_status_path.exists(),
    }
    packaging_assertions.update(stage_status.get("packaging_assertions", {}))
    manifest: dict[str, object] = {
        "git_sha": git_head(),
        "generated_at": isoformat_z(),
        "stage": stage_id,
        "stage_decision": stage_status.get("stage_decision", stage_status.get("decision", "paused")),
        "figure_guidance": list(stage_status.get("figure_guidance", [])),
        "representative_runs": representative_runs,
        "recommend_next_stage": stage_status.get("recommend_next_stage", ""),
        "included_run_ids": _scan_run_ids(bundle_root),
        "included_validation_files": _scan_validation_files(bundle_root),
        "included_audit_files": _scan_audit_files(bundle_root),
        "key_metrics_digest": _key_metrics_digest(bundle_root),
        "packaging_assertions": packaging_assertions,
        "inherited_runs": list(stage_status.get("inherited_runs", [])),
        "newly_executed_runs": list(stage_status.get("newly_executed_runs", [])),
        "skipped_runs": list(stage_status.get("skipped_runs", [])),
    }
    for key in (
        "bundle_type",
        "worktree_dirty",
        "included_code_paths",
        "included_result_sets",
        "included_paper_files",
        "sealed_stage_decisions",
        "sealed_wiring_statuses",
        "diagnostic_stage_notes",
        "excluded_result_sets",
        "stale_note_paths",
    ):
        if key in stage_status:
            manifest[key] = stage_status[key]
    return manifest


def _zip_bundle(output_zip: Path, bundle_root: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["zip", "-rq", str(output_zip), bundle_root.name],
        cwd=bundle_root.parent,
        check=True,
    )


def main() -> int:
    args = parse_args()
    if args.bundle_key not in BUNDLE_CONFIG:
        print(f"ERROR: unsupported bundle key '{args.bundle_key}'", file=sys.stderr)
        return 1

    config = BUNDLE_CONFIG[args.bundle_key]
    stage_id = str(config["stage_id"])
    manifest_path = _resolve(config["manifest"])
    stage_root = _stage_root(stage_id)
    if not manifest_path.exists():
        print(f"ERROR: missing bundle manifest file: {manifest_path}", file=sys.stderr)
        return 1
    if config.get("external_review"):
        _prepare_external_review_stage(config, stage_root, args.dry_run)
    elif not stage_root.exists() and not args.dry_run:
        print(f"ERROR: missing stage root: {stage_root}", file=sys.stderr)
        return 1

    date_stamp = subprocess.run(["date", "+%Y%m%d"], capture_output=True, text=True, check=True).stdout.strip()
    zip_name = f"{config['prefix']}-{date_stamp}-{git_head()}{config['suffix']}.zip"
    print(f"bundle_key={args.bundle_key}")
    print(f"manifest={manifest_path}")
    print(f"zip_name={zip_name}")

    with tempfile.TemporaryDirectory(prefix="hiroute-review-bundle.") as tmp_dir:
        bundle_root = Path(tmp_dir) / zip_name.removesuffix(".zip")
        bundle_root.mkdir(parents=True, exist_ok=True)

        core_paths = [
            ("README.md", stage_root / "README.md"),
            ("checks.txt", stage_root / "checks.txt"),
            ("stage_status.json", stage_root / "stage_status.json"),
            ("REVIEW_GUIDE.md", stage_root / "REVIEW_GUIDE.md"),
            ("RESULT_STATUS.md", stage_root / "RESULT_STATUS.md"),
            ("WORKTREE_STATUS.txt", stage_root / "WORKTREE_STATUS.txt"),
            ("NOTE_STATUS.md", stage_root / "NOTE_STATUS.md"),
            ("validation", stage_root / "validation"),
        ]
        for dest_rel, src in core_paths:
            if src.exists() or args.dry_run:
                _copy_path(src, bundle_root / dest_rel, args.dry_run)

        for raw_line in manifest_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            if line.startswith("@stage_subtree "):
                subtree = line.split(" ", 1)[1]
                _copy_path(stage_root / subtree, bundle_root / subtree, args.dry_run)
            elif line.startswith("@evaluation_excerpt "):
                source_rel = line.split(" ", 1)[1]
                _extract_evaluation_excerpt(_resolve(source_rel), bundle_root / "paper" / "evaluation_excerpt.tex", args.dry_run)
            elif line.startswith("@promoted_runs "):
                _copy_promoted_runs(line.split(" ", 1)[1], bundle_root, args.dry_run)
            elif line.startswith("@representative_runs "):
                source_stage = line.split(" ", 1)[1]
                source_status = _load_stage_status(source_stage)
                representative_runs = _dedupe(list(source_status.get("representative_runs", [])))
                _copy_run_ids(representative_runs, bundle_root, args.dry_run)
            elif line.startswith("@stage_runs "):
                source_stage = line.split(" ", 1)[1]
                source_status = _load_stage_status(source_stage)
                completed_run_ids = _dedupe(list(source_status.get("completed_run_ids", [])))
                _copy_run_ids(completed_run_ids, bundle_root, args.dry_run)
            else:
                source = _resolve(line)
                dest = bundle_root / Path(line)
                _copy_path(source, dest, args.dry_run)

        if args.dry_run:
            if config.get("external_review"):
                print(f"included_result_sets={','.join(config['included_result_sets'])}")
                print(f"excluded_result_sets={','.join(config['excluded_result_sets'])}")
            print(f"bundle_manifest={stage_root / 'bundle_manifest.json'}")
            print(f"dry_run_output={repo_root() / 'review_bundles' / zip_name}")
            return 0

        bundle_manifest = _build_bundle_manifest(stage_id, bundle_root, stage_root)
        stage_bundle_manifest_path = stage_root / "bundle_manifest.json"
        stage_bundle_manifest_path.write_text(json.dumps(bundle_manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        (bundle_root / "bundle_manifest.json").write_text(
            json.dumps(bundle_manifest, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

        validation = subprocess.run(
            [
                PYTHON,
                str(repo_root() / "tools" / "validate_bundle_freshness.py"),
                "--stage-root",
                str(stage_root),
                "--bundle-root",
                str(bundle_root),
            ],
            cwd=repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        if validation.returncode != 0:
            sys.stderr.write(validation.stdout)
            sys.stderr.write(validation.stderr)
            return validation.returncode

        output_zip = repo_root() / "review_bundles" / zip_name
        _zip_bundle(output_zip, bundle_root)
        print(output_zip)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
