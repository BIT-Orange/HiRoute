"""Read-only readiness audit for mainline paper Figures 3-9."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import read_csv, repo_root


@dataclass(frozen=True)
class FigureSpec:
    number: int
    label: str
    experiment: str
    aggregate: str
    figure: str
    note: str
    intended_role: str
    caution: str
    decision_json: str | None = None
    allowed_decisions: tuple[str, ...] = ()


FIGURES = [
    FigureSpec(
        3,
        "fig:ablation",
        "configs/experiments/ablation.yaml",
        "results/aggregate/mainline/ablation_summary.csv",
        "results/figures/mainline/fig_ablation_summary.pdf",
        "paper/notes/fig_ablation.md",
        "ablation diagnostic",
        "small manifest-1 gap; not standalone superiority proof",
        "review_artifacts/ablation/aggregate/ablation_decision.json",
        ("ready_for_main_figure", "ready_for_support_figure"),
    ),
    FigureSpec(
        4,
        "fig:main",
        "configs/experiments/routing_main.yaml",
        "results/aggregate/mainline/routing_support.csv",
        "results/figures/mainline/fig_routing_support.pdf",
        "paper/notes/fig_routing_support.md",
        "routing diagnostic",
        "promoted routing query-count gate must pass before paper-facing promotion",
    ),
    FigureSpec(
        5,
        "fig:waterfall",
        "configs/experiments/object_main.yaml",
        "results/aggregate/mainline/object_main_manifest_sweep.csv",
        "results/figures/mainline/fig_object_manifest_sweep.pdf",
        "paper/notes/fig_object_manifest_sweep.md",
        "checked support",
        "fallback/rescue evidence, not first-object top-1 evidence",
        "review_artifacts/object_main/aggregate/object_main_decision.json",
        ("ready_for_main_figure", "support_only_figure", "cost_only_figure"),
    ),
    FigureSpec(
        6,
        "fig:shrinkage",
        "configs/experiments/routing_main.yaml",
        "results/aggregate/mainline/candidate_shrinkage.csv",
        "results/figures/mainline/fig_candidate_shrinkage.pdf",
        "paper/notes/fig_candidate_shrinkage.md",
        "routing diagnostic",
        "shares routing promoted-run gate with Figure 4",
    ),
    FigureSpec(
        7,
        "fig:latency",
        "configs/experiments/routing_main.yaml",
        "results/aggregate/mainline/deadline_summary.csv",
        "results/figures/mainline/fig_deadline_summary.pdf",
        "paper/notes/fig_deadline_summary.md",
        "routing diagnostic",
        "latency tradeoff; not universal latency superiority",
    ),
    FigureSpec(
        8,
        "fig:state",
        "configs/experiments/state_scaling.yaml",
        "results/aggregate/mainline/state_scaling_summary.csv",
        "results/figures/mainline/fig_state_scaling.pdf",
        "paper/notes/fig_state_scaling.md",
        "state-only support",
        "query-side success/latency/bytes intentionally undefined",
    ),
    FigureSpec(
        9,
        "fig:robust",
        "configs/experiments/robustness.yaml",
        "results/aggregate/mainline/robustness_summary.csv",
        "results/figures/mainline/fig_robustness.pdf",
        "paper/notes/fig_robustness.md",
        "robustness diagnostic",
        "raw-run provenance and promoted query-count gate must pass",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="emit a markdown table instead of a tab-separated table",
    )
    parser.add_argument(
        "--allow-diagnostic",
        action="store_true",
        help="return success even when some figures remain diagnostic",
    )
    return parser.parse_args()


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else repo_root() / candidate


def _run_figure_gate(spec: FigureSpec) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(repo_root() / "tools" / "validate_figures.py"),
        "--experiment",
        str(_resolve(spec.experiment)),
        "--aggregate",
        str(_resolve(spec.aggregate)),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    output = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
    message = output.splitlines()[0] if output else "OK"
    return result.returncode == 0, message


def _claim_hygiene_gate() -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(repo_root() / "tools" / "audit_paper_claim_hygiene.py"),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    output = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
    if result.returncode == 0:
        return True, "ok"
    lines = [line for line in output.splitlines() if line.strip()]
    message = lines[1] if len(lines) > 1 else lines[0] if lines else "claim hygiene failed"
    return False, message


def _worktree_gate() -> tuple[bool, str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        output = "\n".join(part.strip() for part in [result.stdout, result.stderr] if part.strip())
        return False, output.splitlines()[0] if output else "git status failed"
    dirty_paths = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty_paths:
        return False, f"dirty({len(dirty_paths)})"
    return True, "clean"


def _missing_source_query_logs(aggregate: str) -> list[str]:
    aggregate_path = _resolve(aggregate)
    if not aggregate_path.exists():
        return []
    runs_path = repo_root() / "runs" / "registry" / "runs.csv"
    if not runs_path.exists():
        return []
    run_index = {row["run_id"]: row for row in read_csv(runs_path)}
    missing: set[str] = set()
    for row in read_csv(aggregate_path):
        for run_id in str(row.get("source_run_ids", "")).split("|"):
            if not run_id:
                continue
            run_row = run_index.get(run_id)
            run_dir = run_row.get("run_dir", "") if run_row else ""
            if not run_dir or not (repo_root() / run_dir / "query_log.csv").exists():
                missing.add(run_id)
    return sorted(missing)


def _file_status(path: str) -> str:
    resolved = _resolve(path)
    if not resolved.exists():
        return "missing"
    if resolved.is_file() and resolved.stat().st_size == 0:
        return "empty"
    return "ok"


def _decision_gate(spec: FigureSpec) -> tuple[bool, str]:
    if spec.decision_json is None:
        return True, "not_applicable"
    decision_path = _resolve(spec.decision_json)
    if not decision_path.exists():
        return False, f"missing {spec.decision_json}"
    try:
        decision = str(json.loads(decision_path.read_text(encoding="utf-8")).get("decision", ""))
    except json.JSONDecodeError as error:
        return False, f"invalid json: {error}"
    if decision in spec.allowed_decisions:
        return True, decision
    return False, f"{decision} not in {','.join(spec.allowed_decisions)}"


def _caption_for_label(label: str) -> str | None:
    paper_path = repo_root() / "paper" / "main.tex"
    if not paper_path.exists():
        return None
    text = paper_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"\\caption\{(?P<caption>[^{}]*)\}\s*\\label\{" + re.escape(label) + r"\}",
        re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return None
    return " ".join(match.group("caption").split())


def _note_caption_gate(spec: FigureSpec) -> tuple[bool, str]:
    note_path = _resolve(spec.note)
    if not note_path.exists():
        return False, f"missing {spec.note}"
    paper_caption = _caption_for_label(spec.label)
    if paper_caption is None:
        return False, f"missing caption for {spec.label}"
    text = note_path.read_text(encoding="utf-8")
    match = re.search(r"^- caption target: `(?P<caption>.*)`$", text, flags=re.MULTILINE)
    if not match:
        return False, "missing caption target"
    note_caption = " ".join(match.group("caption").split())
    if note_caption == paper_caption:
        return True, "ok"
    return False, "caption target mismatch"


def _markdown_cell(value: str) -> str:
    return " ".join(value.replace("|", "/").split())


def main() -> int:
    args = parse_args()
    rows: list[dict[str, str]] = []
    all_ready = True
    worktree_ok, worktree_message = _worktree_gate()
    claim_hygiene_ok, claim_hygiene_message = _claim_hygiene_gate()

    for spec in FIGURES:
        figure_status = _file_status(spec.figure)
        aggregate_status = _file_status(spec.aggregate)
        gate_ok, gate_message = _run_figure_gate(spec)
        decision_ok, decision_message = _decision_gate(spec)
        note_ok, note_message = _note_caption_gate(spec)
        missing_logs = _missing_source_query_logs(spec.aggregate)
        ready = (
            figure_status == "ok"
            and aggregate_status == "ok"
            and gate_ok
            and decision_ok
            and note_ok
            and claim_hygiene_ok
            and worktree_ok
            and not missing_logs
        )
        all_ready = all_ready and ready
        rows.append(
            {
                "figure": str(spec.number),
                "label": spec.label,
                "role": spec.intended_role,
                "figure_file": figure_status,
                "aggregate": aggregate_status,
                "figure_gate": "ok" if gate_ok else gate_message,
                "decision_gate": "ok" if decision_ok else decision_message,
                "note_caption": "ok" if note_ok else note_message,
                "claim_hygiene": "ok" if claim_hygiene_ok else claim_hygiene_message,
                "worktree_gate": "ok" if worktree_ok else worktree_message,
                "missing_query_logs": str(len(missing_logs)),
                "status": "paper-facing checked" if ready else "diagnostic/blocking",
                "caution": spec.caution,
            }
        )

    headers = [
        "figure",
        "label",
        "role",
        "figure_file",
        "aggregate",
        "figure_gate",
        "decision_gate",
        "note_caption",
        "claim_hygiene",
        "worktree_gate",
        "missing_query_logs",
        "status",
        "caution",
    ]
    if args.markdown:
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for row in rows:
            print("| " + " | ".join(_markdown_cell(row[header]) for header in headers) + " |")
    else:
        print("\t".join(headers))
        for row in rows:
            print("\t".join(row[header] for header in headers))

    if all_ready or args.allow_diagnostic:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
