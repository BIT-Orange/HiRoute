"""Audit level-0 HS-LSA predicate coverage against query/qrels inputs."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import read_csv, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", required=True, type=Path)
    parser.add_argument("--qrels-domain", required=True, type=Path)
    parser.add_argument("--hslsa", required=True, type=Path)
    parser.add_argument("--details-csv", required=True, type=Path)
    parser.add_argument("--summary-json", required=True, type=Path)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _split_bitmap(value: str, delimiter: str) -> set[str]:
    if not value:
        return set()
    return {token for token in value.split(delimiter) if token}


def _matches_bitmap(values: set[str], constraint: str) -> bool:
    if not constraint or not values:
        return True
    return any(token in values for token in constraint.split(";") if token)


def _mean(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / float(len(values)), 6)


def main() -> int:
    args = parse_args()
    query_rows = read_csv(_resolve(args.queries))
    qrels_domain_rows = read_csv(_resolve(args.qrels_domain))
    summary_rows = [
        row for row in read_csv(_resolve(args.hslsa)) if int(row.get("level") or 0) == 0
    ]

    relevant_domains_by_query: dict[str, set[str]] = defaultdict(set)
    for row in qrels_domain_rows:
        if row.get("is_relevant_domain", "1") == "1":
            relevant_domains_by_query[row["query_id"]].add(row["domain_id"])

    output_rows: list[dict[str, Any]] = []
    tier_buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for query in query_rows:
        zone_constraint = query.get("zone_constraint", "")
        zone_type_constraint = query.get("zone_type_constraint", "")
        service_constraint = query.get("service_constraint", "")
        freshness_constraint = query.get("freshness_constraint", "")

        matched_domains: list[str] = []
        zone_drop_count = 0
        zone_type_drop_count = 0
        service_drop_count = 0
        freshness_drop_count = 0

        for summary in summary_rows:
            zone_match = _matches_bitmap(_split_bitmap(summary.get("zone_bitmap", ""), "|"), zone_constraint)
            zone_type_match = _matches_bitmap(
                _split_bitmap(summary.get("zone_type_bitmap", ""), "|"),
                zone_type_constraint,
            )
            service_match = _matches_bitmap(
                _split_bitmap(summary.get("service_bitmap", ""), "|"),
                service_constraint,
            )
            freshness_match = _matches_bitmap(
                _split_bitmap(summary.get("freshness_bitmap", ""), "|"),
                freshness_constraint,
            )
            if not zone_match:
                zone_drop_count += 1
            if not zone_type_match:
                zone_type_drop_count += 1
            if not service_match:
                service_drop_count += 1
            if not freshness_match:
                freshness_drop_count += 1
            if zone_match and zone_type_match and service_match and freshness_match:
                matched_domains.append(summary["domain_id"])

        relevant_domains = sorted(relevant_domains_by_query.get(query["query_id"], set()))
        matched_domain_ids = sorted(set(matched_domains))
        matched_relevant_domain_ids = sorted(set(matched_domain_ids).intersection(relevant_domains))
        row = {
            "query_id": query["query_id"],
            "split": query.get("split", ""),
            "workload_tier": query.get("workload_tier", ""),
            "zone_constraint": zone_constraint,
            "zone_type_constraint": zone_type_constraint,
            "service_constraint": service_constraint,
            "freshness_constraint": freshness_constraint,
            "relevant_domain_ids": ";".join(relevant_domains),
            "matched_domain_ids": ";".join(matched_domain_ids),
            "matched_relevant_domain_ids": ";".join(matched_relevant_domain_ids),
            "matched_domain_count": len(matched_domain_ids),
            "matched_relevant_domain_count": len(matched_relevant_domain_ids),
            "zone_drop_count": zone_drop_count,
            "zone_type_drop_count": zone_type_drop_count,
            "service_drop_count": service_drop_count,
            "freshness_drop_count": freshness_drop_count,
        }
        output_rows.append(row)
        tier_buckets[row["workload_tier"]].append(row)

    write_csv(
        _resolve(args.details_csv),
        [
            "query_id",
            "split",
            "workload_tier",
            "zone_constraint",
            "zone_type_constraint",
            "service_constraint",
            "freshness_constraint",
            "relevant_domain_ids",
            "matched_domain_ids",
            "matched_relevant_domain_ids",
            "matched_domain_count",
            "matched_relevant_domain_count",
            "zone_drop_count",
            "zone_type_drop_count",
            "service_drop_count",
            "freshness_drop_count",
        ],
        output_rows,
    )

    summary_payload: dict[str, Any] = {
        "query_count": len(output_rows),
        "tier_summaries": {},
    }
    for tier, rows in sorted(tier_buckets.items()):
        matched_domain_counts = [int(row["matched_domain_count"]) for row in rows]
        matched_relevant_domain_counts = [int(row["matched_relevant_domain_count"]) for row in rows]
        zero_match_query_ids = [
            row["query_id"] for row in rows if int(row["matched_domain_count"]) == 0
        ]
        zero_relevant_match_query_ids = [
            row["query_id"] for row in rows if int(row["matched_relevant_domain_count"]) == 0
        ]
        summary_payload["tier_summaries"][tier] = {
            "query_count": len(rows),
            "mean_matched_domain_count": _mean(matched_domain_counts),
            "mean_matched_relevant_domain_count": _mean(matched_relevant_domain_counts),
            "matched_domain_count_support": sorted(set(matched_domain_counts)),
            "matched_relevant_domain_count_support": sorted(set(matched_relevant_domain_counts)),
            "zero_match_query_count": len(zero_match_query_ids),
            "zero_relevant_match_query_count": len(zero_relevant_match_query_ids),
            "zero_match_query_ids_sample": zero_match_query_ids[:20],
            "zero_relevant_match_query_ids_sample": zero_relevant_match_query_ids[:20],
            "drop_blockers_total": {
                "zone": sum(int(row["zone_drop_count"]) for row in rows),
                "zone_type": sum(int(row["zone_type_drop_count"]) for row in rows),
                "service": sum(int(row["service_drop_count"]) for row in rows),
                "freshness": sum(int(row["freshness_drop_count"]) for row in rows),
            },
        }

    summary_path = _resolve(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    routing_summary = summary_payload["tier_summaries"].get("routing_main", {})
    print(
        json.dumps(
            {
                "query_count": summary_payload["query_count"],
                "routing_main": routing_summary,
                "workload_tier_counts": Counter(row["workload_tier"] for row in output_rows),
            },
            indent=2,
            ensure_ascii=True,
            default=list,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
