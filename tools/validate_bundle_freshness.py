"""Validate review bundle freshness against stage metadata and copied files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import read_csv, repo_root


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-root", required=True, type=Path)
    parser.add_argument("--bundle-root", required=True, type=Path)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_root() / path


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_prefixed_lines(path: Path) -> dict[str, str]:
    payload: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip()
    return payload


def _parse_csvish(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bundle_run_ids(bundle_root: Path) -> set[str]:
    run_ids: set[str] = set()
    for manifest_path in bundle_root.glob("runs/*/manifest.yaml"):
        run_ids.add(manifest_path.parent.name)
    for manifest_path in bundle_root.glob("runs/completed/*/manifest.yaml"):
        run_ids.add(manifest_path.parent.name)
    return run_ids


def _bundle_validation_files(bundle_root: Path) -> set[str]:
    return {
        str(path.relative_to(bundle_root))
        for path in bundle_root.rglob("*")
        if path.is_file() and path.parent.name == "validation"
    }


def _bundle_audit_files(bundle_root: Path) -> set[str]:
    audit_files: set[str] = set()
    for path in bundle_root.rglob("*"):
        if not path.is_file():
            continue
        rel = str(path.relative_to(bundle_root))
        if "audit" in {part.lower() for part in path.parts}:
            audit_files.add(rel)
            continue
        if path.name.endswith("_manifest_wiring_report.json"):
            audit_files.add(rel)
    return audit_files


def _summary_source_run_ids(bundle_root: Path) -> set[str]:
    source_run_ids: set[str] = set()
    aggregate_candidates = list(bundle_root.glob("aggregate/*.csv")) + list(bundle_root.glob("results/aggregate/**/*.csv"))
    for aggregate_path in aggregate_candidates:
        rows = read_csv(aggregate_path)
        if not rows or "source_run_ids" not in rows[0]:
            continue
        for row in rows:
            for run_id in str(row.get("source_run_ids", "")).split("|"):
                if run_id:
                    source_run_ids.add(run_id)
    return source_run_ids


def _git_status_short() -> str:
    return subprocess.run(
        ["git", "-C", str(repo_root()), "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def main() -> int:
    args = parse_args()
    stage_root = _resolve(args.stage_root)
    bundle_root = _resolve(args.bundle_root)

    errors: list[str] = []
    stage_status_path = stage_root / "stage_status.json"
    stage_status = _load_json(stage_status_path) if stage_status_path.exists() else {}
    bundle_type = str(stage_status.get("bundle_type", ""))
    required_stage_files = [
        stage_root / "README.md",
        stage_root / "checks.txt",
        stage_status_path,
        stage_root / "bundle_manifest.json",
    ]
    required_bundle_files = [
        bundle_root / "README.md",
        bundle_root / "checks.txt",
        bundle_root / "bundle_manifest.json",
    ]
    if bundle_type in {"teacher", "chatgpt"}:
        required_stage_files.extend(
            [
                stage_root / "REVIEW_GUIDE.md",
                stage_root / "RESULT_STATUS.md",
                stage_root / "WORKTREE_STATUS.txt",
            ]
        )
        required_bundle_files.extend(
            [
                bundle_root / "REVIEW_GUIDE.md",
                bundle_root / "RESULT_STATUS.md",
                bundle_root / "WORKTREE_STATUS.txt",
            ]
        )
        if bundle_type == "chatgpt":
            required_stage_files.append(stage_root / "NOTE_STATUS.md")
            required_bundle_files.append(bundle_root / "NOTE_STATUS.md")
    for path in required_stage_files + required_bundle_files:
        if not path.exists():
            errors.append(f"missing required file: {path}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    stage_bundle_manifest = _load_json(stage_root / "bundle_manifest.json")
    bundle_manifest = _load_json(bundle_root / "bundle_manifest.json")
    readme = _parse_prefixed_lines(bundle_root / "README.md")
    checks = _parse_prefixed_lines(bundle_root / "checks.txt")

    if stage_bundle_manifest != bundle_manifest:
        errors.append("bundle_manifest.json in bundle root does not match stage artifact root")

    completed_experiments = readme.get("completed_experiments", "")
    expected_completed = stage_status.get("completed_experiments", "")
    if completed_experiments != expected_completed:
        errors.append(
            f"README completed_experiments={completed_experiments!r} does not match stage_status={expected_completed!r}"
        )
    if checks.get("completed_experiments", "") != expected_completed:
        errors.append("checks.txt completed_experiments does not match stage_status")

    decision = str(stage_status.get("decision", "paused"))
    if decision != "paused" and readme.get("known_incomplete_items", "").lower() == "paused":
        errors.append("README still says paused after stage decision moved past paused")
    if checks.get("decision", "") != decision:
        errors.append("checks.txt decision does not match stage_status decision")

    stage_decision = str(stage_status.get("stage_decision", decision))
    if readme.get("stage_decision", "") != stage_decision:
        errors.append("README stage_decision does not match stage_status")
    if bundle_manifest.get("stage_decision", "") != stage_decision:
        errors.append("bundle_manifest stage_decision does not match stage_status")

    stage_guidance = list(stage_status.get("figure_guidance", []))
    readme_guidance = _parse_csvish(readme.get("figure_guidance", ""))
    checks_guidance = _parse_csvish(checks.get("figure_guidance", ""))
    if readme_guidance != stage_guidance:
        errors.append("README figure_guidance does not match stage_status")
    if checks_guidance and checks_guidance != stage_guidance:
        errors.append("checks.txt figure_guidance does not match stage_status")
    if list(bundle_manifest.get("figure_guidance", [])) != stage_guidance:
        errors.append("bundle_manifest figure_guidance does not match stage_status")

    stage_representative_runs = list(stage_status.get("representative_runs", []))
    if not stage_representative_runs and stage_status.get("representative_run"):
        stage_representative_runs = [str(stage_status["representative_run"])]
    readme_representative_runs = _parse_csvish(readme.get("representative_runs", ""))
    checks_representative_runs = _parse_csvish(checks.get("representative_runs", ""))
    if readme_representative_runs and readme_representative_runs != stage_representative_runs:
        errors.append("README representative_runs does not match stage_status")
    if checks_representative_runs and checks_representative_runs != stage_representative_runs:
        errors.append("checks.txt representative_runs does not match stage_status")
    if list(bundle_manifest.get("representative_runs", [])) != stage_representative_runs:
        errors.append("bundle_manifest representative_runs does not match stage_status")

    recommend_next_stage = str(stage_status.get("recommend_next_stage", ""))
    if readme.get("recommend_next_stage", "") != recommend_next_stage:
        errors.append("README recommend_next_stage does not match stage_status")
    if checks.get("recommend_next_stage", "") and checks.get("recommend_next_stage", "") != recommend_next_stage:
        errors.append("checks.txt recommend_next_stage does not match stage_status")
    if bundle_manifest.get("recommend_next_stage", "") != recommend_next_stage:
        errors.append("bundle_manifest recommend_next_stage does not match stage_status")

    bundle_run_ids = _bundle_run_ids(bundle_root)
    included_run_ids = set(stage_bundle_manifest.get("included_run_ids", []))
    stage_run_ids = set(stage_status.get("completed_run_ids", []))
    if bundle_run_ids != included_run_ids:
        errors.append(
            f"bundle run ids {sorted(bundle_run_ids)} do not match bundle_manifest included_run_ids {sorted(included_run_ids)}"
        )

    partial_bundle = bool(stage_bundle_manifest.get("packaging_assertions", {}).get("partial_bundle", False))
    if included_run_ids != stage_run_ids and not partial_bundle:
        errors.append("bundle_manifest included_run_ids do not cover all stage completed_run_ids")
    if partial_bundle and not included_run_ids.issubset(stage_run_ids):
        errors.append("partial bundle includes run ids outside stage completed_run_ids")

    representative_run = checks.get("representative_run", "")
    if representative_run:
        manifest_path = bundle_root / "runs" / representative_run / "manifest.yaml"
        query_log_path = bundle_root / "runs" / representative_run / "query_log.csv"
        alt_manifest_path = bundle_root / "runs" / "completed" / representative_run / "manifest.yaml"
        alt_query_log_path = bundle_root / "runs" / "completed" / representative_run / "query_log.csv"
        if not (
            (manifest_path.exists() and query_log_path.exists())
            or (alt_manifest_path.exists() and alt_query_log_path.exists())
        ):
            errors.append(f"representative_run={representative_run} is missing manifest/query_log in bundle")

    for representative_run in stage_representative_runs:
        manifest_path = bundle_root / "runs" / representative_run / "manifest.yaml"
        query_log_path = bundle_root / "runs" / representative_run / "query_log.csv"
        alt_manifest_path = bundle_root / "runs" / "completed" / representative_run / "manifest.yaml"
        alt_query_log_path = bundle_root / "runs" / "completed" / representative_run / "query_log.csv"
        if not (
            (manifest_path.exists() and query_log_path.exists())
            or (alt_manifest_path.exists() and alt_query_log_path.exists())
        ):
            errors.append(f"representative_runs entry {representative_run} is missing manifest/query_log in bundle")

    if checks.get("inherited_from_quick", "") == "yes":
        inherited_count = int(checks.get("inherited_run_count", "0") or "0")
        if inherited_count != len(stage_status.get("inherited_runs", [])):
            errors.append("checks.txt inherited_run_count does not match stage_status inherited_runs")

    bundle_validation_files = _bundle_validation_files(bundle_root)
    manifest_validation_files = set(stage_bundle_manifest.get("included_validation_files", []))
    if bundle_validation_files != manifest_validation_files:
        errors.append("bundle validation files do not match bundle_manifest included_validation_files")

    bundle_audit_files = _bundle_audit_files(bundle_root)
    manifest_audit_files = set(stage_bundle_manifest.get("included_audit_files", []))
    if bundle_audit_files != manifest_audit_files:
        errors.append("bundle audit files do not match bundle_manifest included_audit_files")

    summary_source_run_ids = _summary_source_run_ids(bundle_root)
    effective_summary_source_run_ids = set(summary_source_run_ids)
    included_result_sets = set(bundle_manifest.get("included_result_sets", []))
    if bundle_type in {"teacher", "chatgpt"} and "routing_support_diagnostic" in included_result_sets:
        effective_summary_source_run_ids = {
            run_id for run_id in effective_summary_source_run_ids if not run_id.startswith("routing_main__")
        }
    if effective_summary_source_run_ids:
        if partial_bundle:
            if not included_run_ids.issubset(effective_summary_source_run_ids):
                errors.append("partial bundle run ids are not a subset of aggregate/source summary run ids")
        elif effective_summary_source_run_ids != included_run_ids:
            errors.append("aggregate/source summary run ids do not match bundle_manifest included_run_ids")

    if bundle_type in {"teacher", "chatgpt"}:
        if bundle_manifest.get("bundle_type", "") != bundle_type:
            errors.append("bundle_manifest bundle_type does not match stage_status")
        if bundle_manifest.get("worktree_dirty") != stage_status.get("worktree_dirty"):
            errors.append("bundle_manifest worktree_dirty does not match stage_status")
        for key in (
            "included_code_paths",
            "included_result_sets",
            "included_paper_files",
            "sealed_stage_decisions",
            "sealed_wiring_statuses",
            "diagnostic_stage_notes",
            "excluded_result_sets",
        ):
            if bundle_manifest.get(key) != stage_status.get(key):
                errors.append(f"bundle_manifest {key} does not match stage_status")

        worktree_stage = (stage_root / "WORKTREE_STATUS.txt").read_text(encoding="utf-8")
        worktree_bundle = (bundle_root / "WORKTREE_STATUS.txt").read_text(encoding="utf-8")
        if worktree_stage != worktree_bundle:
            errors.append("WORKTREE_STATUS.txt in bundle does not match stage root")
        if worktree_stage != _git_status_short():
            errors.append("WORKTREE_STATUS.txt does not match current git status --short")

        review_guide_stage = (stage_root / "REVIEW_GUIDE.md").read_text(encoding="utf-8")
        review_guide_bundle = (bundle_root / "REVIEW_GUIDE.md").read_text(encoding="utf-8")
        if review_guide_stage != review_guide_bundle:
            errors.append("REVIEW_GUIDE.md in bundle does not match stage root")
        result_status_stage = (stage_root / "RESULT_STATUS.md").read_text(encoding="utf-8")
        result_status_bundle = (bundle_root / "RESULT_STATUS.md").read_text(encoding="utf-8")
        if result_status_stage != result_status_bundle:
            errors.append("RESULT_STATUS.md in bundle does not match stage root")
        if bundle_type == "chatgpt":
            note_status_stage = (stage_root / "NOTE_STATUS.md").read_text(encoding="utf-8")
            note_status_bundle = (bundle_root / "NOTE_STATUS.md").read_text(encoding="utf-8")
            if note_status_stage != note_status_bundle:
                errors.append("NOTE_STATUS.md in bundle does not match stage root")

        sealed_stage_decisions = stage_status.get("sealed_stage_decisions", {})
        if sealed_stage_decisions.get("object_main") != "ready_for_main_figure":
            errors.append("external bundle requires object_main=ready_for_main_figure")
        if sealed_stage_decisions.get("ablation") != "ready_for_support_figure":
            errors.append("external bundle requires ablation=ready_for_support_figure")
        sealed_wiring_statuses = stage_status.get("sealed_wiring_statuses", {})
        for key in ("object_main_manifest_wiring", "ablation_manifest_wiring"):
            if not sealed_wiring_statuses.get(key):
                errors.append(f"missing sealed wiring status: {key}")
            elif sealed_wiring_statuses.get(key) == "wiring_suspect":
                errors.append(f"sealed wiring status is wiring_suspect: {key}")

        for rel_path in (
            "results/aggregate/mainline/routing_support.csv",
            "results/aggregate/mainline/routing_support.trace.json",
            "results/figures/mainline/fig_routing_support.pdf",
            "results/figures/mainline/fig_routing_support.png",
            "paper/notes/fig_routing_support.md",
        ):
            if "routing_support_diagnostic" in included_result_sets and not (bundle_root / rel_path).exists():
                errors.append(f"routing support diagnostic file missing from external bundle: {rel_path}")

        forbidden_prefixes = (
            "results/aggregate/v3/",
            "results/figures/v3/",
            "results/tables/v3/",
        )
        forbidden_patterns = (
            "state_scaling",
            "robustness",
        )
        for path in bundle_root.rglob("*"):
            if not path.is_file():
                continue
            rel = str(path.relative_to(bundle_root))
            if any(rel.startswith(prefix) for prefix in forbidden_prefixes):
                errors.append(f"forbidden historical result included in external bundle: {rel}")
            if any(token in rel for token in forbidden_patterns):
                errors.append(f"forbidden unsealed result included in external bundle: {rel}")

        stale_note_paths = [str(path) for path in stage_status.get("stale_note_paths", [])]
        if bundle_type == "teacher":
            for rel in stale_note_paths:
                if (bundle_root / rel).exists():
                    errors.append(f"teacher bundle must not include stale note: {rel}")
            if any("review_artifacts/object_main/runs/" in str(path.relative_to(bundle_root)) for path in bundle_root.rglob("*") if path.is_file()):
                errors.append("teacher bundle must not include full review_artifacts object_main runs subtree")
            if any("review_artifacts/ablation/runs/" in str(path.relative_to(bundle_root)) for path in bundle_root.rglob("*") if path.is_file()):
                errors.append("teacher bundle must not include full review_artifacts ablation runs subtree")
        else:
            for rel in stale_note_paths:
                if not (bundle_root / rel).exists():
                    errors.append(f"chatgpt bundle must include stale note for context: {rel}")
            if not (bundle_root / "review_artifacts/object_main/stage_status.json").exists():
                errors.append("chatgpt bundle must include review_artifacts/object_main subtree")
            if not (bundle_root / "review_artifacts/ablation/stage_status.json").exists():
                errors.append("chatgpt bundle must include review_artifacts/ablation subtree")

        if bundle_type == "teacher" and len(included_run_ids) != 8:
            errors.append(f"teacher bundle should include 8 representative runs, found {len(included_run_ids)}")
        if bundle_type == "chatgpt" and len(included_run_ids) != 24:
            errors.append(f"chatgpt bundle should include 24 object/ablation runs, found {len(included_run_ids)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
