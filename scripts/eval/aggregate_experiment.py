"""Dispatch experiment-specific aggregate builders for Figure 4-10."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, repo_root


SCRIPT_MAP = {
    "exp_main_v1": [
        "scripts/eval/aggregate_query_metrics.py",
        "scripts/eval/build_failure_breakdown.py",
        "scripts/eval/build_candidate_shrinkage.py",
        "scripts/eval/build_deadline_summary.py",
        "scripts/eval/build_ablation_summary.py",
    ],
    "exp_scaling_v1": [
        "scripts/eval/build_state_scaling_summary.py",
    ],
    "exp_staleness_v1": [
        "scripts/eval/build_robustness_summary.py",
    ],
    "exp_failures_v1": [
        "scripts/eval/build_robustness_summary.py",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--registry-source", choices=["runs", "promoted"], default="promoted")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment_path = args.experiment if args.experiment.is_absolute() else repo_root() / args.experiment
    experiment = load_json_yaml(experiment_path)
    scripts = SCRIPT_MAP.get(experiment["experiment_id"], ["scripts/eval/aggregate_query_metrics.py"])

    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(repo_root() / script), "--experiment", str(experiment_path), "--registry-source", args.registry_source],
            cwd=repo_root(),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stderr or result.stdout)
            return result.returncode
        if result.stdout:
            sys.stdout.write(result.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
