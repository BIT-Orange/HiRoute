"""Scan current paper-facing text for stale or over-strong claim wording."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import repo_root


CURRENT_SOURCE_FILES = (
    "paper/main.tex",
    "paper/notes/claim_c001.md",
    "paper/notes/claim_c002.md",
    "paper/notes/claim_c003.md",
    "paper/notes/claim_c004.md",
    "paper/notes/fig_ablation.md",
    "paper/notes/fig_object_manifest_sweep.md",
    "paper/notes/fig_routing_support.md",
    "paper/notes/fig_candidate_shrinkage.md",
    "paper/notes/fig_deadline_summary.md",
    "paper/notes/fig_state_scaling.md",
    "paper/notes/fig_robustness.md",
    "scripts/plots/plot_main_figures.py",
    "scripts/eval/build_stage_decision.py",
    "scripts/eval/build_ablation_summary.py",
    "tools/run_mainline_review_stage.py",
    "tools/package_review_bundle.py",
    ".agents/skills/figure-caption-sanity/SKILL.md",
)


@dataclass(frozen=True)
class HygieneRule:
    rule_id: str
    pattern: str
    reason: str


RULES = (
    HygieneRule(
        "stale_figure10_authority",
        r"Figure 5 and Figure 10|Figure 10 authority|Figure 10 binding|stage-local Figure 10|Figure 10 更适合",
        "current ablation figure is Figure 3, not Figure 10",
    ),
    HygieneRule(
        "stale_figure10_placeholder",
        r"_placeholder\([^,\n]+,\s*['\"]Figure 10['\"]|Build Figure 10 ablation",
        "future generated placeholders/stdout must use Figure 3",
    ),
    HygieneRule(
        "stale_lower_cost_claim",
        r"lower discovery waste|has lower discovery bytes than every control",
        "current routing slice only supports lower bytes than INF-style tag forwarding",
    ),
    HygieneRule(
        "stale_ablation_strength",
        r"paper-grade mechanism|stable gap between|Route B main mechanism figure|strongest paper-facing evidence",
        "current ablation decision is rerun_needed and the gap is small",
    ),
    HygieneRule(
        "stale_state_strength",
        r"validates the bounded-state claim",
        "state scaling is support-only until final clean readiness",
    ),
    HygieneRule(
        "stale_caption_target",
        r"Mainline routing-support figure|Candidate shrinkage under hierarchical filtering|Deadline-sensitive latency evaluation\.|Robustness support figure",
        "figure note captions must match the current diagnostic captions",
    ),
    HygieneRule(
        "stale_controller_loss_wording",
        r"controller loss|controller-loss",
        "current Figure 9 wording uses controller failures/controller_down",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--markdown", action="store_true", help="emit a markdown table")
    return parser.parse_args()


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _line_at(text: str, line_number: int) -> str:
    return text.splitlines()[line_number - 1].strip()


def main() -> int:
    args = parse_args()
    findings: list[dict[str, str]] = []

    for rel_path in CURRENT_SOURCE_FILES:
        path = repo_root() / rel_path
        if not path.exists():
            findings.append(
                {
                    "file": rel_path,
                    "line": "0",
                    "rule": "missing_source",
                    "reason": "expected paper hygiene source is missing",
                    "text": "",
                }
            )
            continue
        text = path.read_text(encoding="utf-8")
        for rule in RULES:
            for match in re.finditer(rule.pattern, text, flags=re.IGNORECASE):
                line_number = _line_number(text, match.start())
                findings.append(
                    {
                        "file": rel_path,
                        "line": str(line_number),
                        "rule": rule.rule_id,
                        "reason": rule.reason,
                        "text": _line_at(text, line_number),
                    }
                )

    headers = ["file", "line", "rule", "reason", "text"]
    if args.markdown:
        print("| " + " | ".join(headers) + " |")
        print("| " + " | ".join("---" for _ in headers) + " |")
        for finding in findings:
            print("| " + " | ".join(finding[header].replace("|", "/") for header in headers) + " |")
    else:
        print("\t".join(headers))
        for finding in findings:
            print("\t".join(finding[header] for header in headers))

    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
