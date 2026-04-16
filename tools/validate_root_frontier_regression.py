"""Validate that a root frontier hint resolves concrete descendants after the controller fix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import read_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--details-csv", required=True, type=Path)
    parser.add_argument("--summary-json", required=True, type=Path)
    parser.add_argument("--query-id", required=True)
    parser.add_argument("--frontier-hint", required=True)
    parser.add_argument("--baseline-descendant-miss", type=int, default=342)
    parser.add_argument("--require-post-filter-hit", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    details_rows = read_csv(args.details_csv)
    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))

    descendant_miss = int(summary.get("zero_reason_counts", {}).get("descendant_miss", 0))
    if descendant_miss >= args.baseline_descendant_miss:
        raise SystemExit(
            f"descendant_miss did not improve: {descendant_miss} >= {args.baseline_descendant_miss}"
        )

    matching_rows = [
        row
        for row in details_rows
        if row.get("query_id") == args.query_id
        and row.get("frontier_hint_cell_id") == args.frontier_hint
    ]
    if not matching_rows:
        raise SystemExit(
            f"missing coverage row for query_id={args.query_id} frontier_hint={args.frontier_hint}"
        )

    row = matching_rows[0]
    if row.get("zero_reason") == "descendant_miss":
        raise SystemExit("root frontier still reports zero_reason=descendant_miss")
    if int(row.get("descendant_cell_count") or 0) <= 0:
        raise SystemExit("root frontier descendant_cell_count must be > 0")
    if int(row.get("candidate_object_count_pre_filter") or 0) <= 0:
        raise SystemExit("root frontier candidate_object_count_pre_filter must be > 0")
    if args.require_post_filter_hit and int(row.get("candidate_object_count_post_filter") or 0) <= 0:
        raise SystemExit("root frontier candidate_object_count_post_filter must be > 0")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
