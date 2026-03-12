"""Generate stable HiRoute run identifiers."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, sanitize_token, utc_timestamp


def make_run_id(experiment: dict, scheme: str, seed: int, timestamp: str | None = None) -> str:
    timestamp = timestamp or utc_timestamp()
    return "__".join(
        [
            sanitize_token(experiment["experiment_id"]),
            sanitize_token(scheme),
            sanitize_token(experiment["dataset_id"]),
            f"seed{seed}",
            timestamp,
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--timestamp")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment = load_json_yaml(args.experiment)
    print(make_run_id(experiment, args.scheme, args.seed, args.timestamp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
