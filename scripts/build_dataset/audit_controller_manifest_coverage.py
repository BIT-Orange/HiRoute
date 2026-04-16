"""Audit controller-local manifest coverage for relevant object domains."""

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
    parser.add_argument("--qrels-object", required=True, type=Path)
    parser.add_argument("--objects", required=True, type=Path)
    parser.add_argument("--controller-local-index", required=True, type=Path)
    parser.add_argument("--hslsa", required=True, type=Path)
    parser.add_argument("--details-csv", required=True, type=Path)
    parser.add_argument("--summary-json", required=True, type=Path)
    return parser.parse_args()


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _canonical_zone_token(zone_id: str) -> str:
    marker = zone_id.rfind("-zone-")
    if marker == -1:
        return zone_id
    return zone_id[marker + 1 :]


def _matches_zone_constraint(object_zone_id: str, constraint: str) -> bool:
    if not constraint:
        return True
    canonical = _canonical_zone_token(object_zone_id)
    return any(
        token and (token == object_zone_id or token == canonical)
        for token in constraint.split(";")
    )


def _matches_summary_bitmap(values: set[str], constraint: str) -> bool:
    if not constraint or not values:
        return True
    return any(token in values for token in constraint.split(";") if token)


def _parse_bitmap(value: str) -> set[str]:
    if not value:
        return set()
    return {token for token in value.split("|") if token}


def _matches_object_query(object_row: dict[str, str], query_row: dict[str, str]) -> bool:
    return (
        _matches_zone_constraint(object_row.get("zone_id", ""), query_row.get("zone_constraint", ""))
        and (
            not query_row.get("zone_type_constraint", "")
            or object_row.get("zone_type", "") == query_row.get("zone_type_constraint", "")
        )
        and (
            not query_row.get("service_constraint", "")
            or object_row.get("service_class", "") == query_row.get("service_constraint", "")
        )
        and (
            not query_row.get("freshness_constraint", "")
            or object_row.get("freshness_class", "") == query_row.get("freshness_constraint", "")
        )
    )


def _split_semicolon_tokens(value: str) -> list[str]:
    return [token for token in value.split(";") if token]


def _sequential_zero_reason(candidate_rows: list[dict[str, str]], query_row: dict[str, str]) -> str:
    remaining = list(candidate_rows)
    zone_constraint = query_row.get("zone_constraint", "")
    if zone_constraint:
        zone_rows = [
            row for row in remaining if _matches_zone_constraint(row.get("zone_id", ""), zone_constraint)
        ]
        if not zone_rows:
            return "zone_mismatch"
        remaining = zone_rows
    zone_type_constraint = query_row.get("zone_type_constraint", "")
    if zone_type_constraint:
        zone_type_rows = [row for row in remaining if row.get("zone_type", "") == zone_type_constraint]
        if not zone_type_rows:
            return "zone_type_mismatch"
        remaining = zone_type_rows
    service_constraint = query_row.get("service_constraint", "")
    if service_constraint:
        service_rows = [row for row in remaining if row.get("service_class", "") == service_constraint]
        if not service_rows:
            return "service_mismatch"
        remaining = service_rows
    freshness_constraint = query_row.get("freshness_constraint", "")
    if freshness_constraint:
        freshness_rows = [
            row for row in remaining if row.get("freshness_class", "") == freshness_constraint
        ]
        if not freshness_rows:
            return "freshness_mismatch"
    return ""


def _cell_depth(cell_id: str) -> int:
    if cell_id.endswith("-root"):
        return 0
    if "-mc-" in cell_id:
        return 2
    return 1


def _domain_root_for_cell(cell_id: str) -> str:
    parts = cell_id.split("-")
    if len(parts) >= 2 and parts[0] == "domain":
        return f"{parts[0]}-{parts[1]}-root"
    return cell_id + "-root"


def _candidate_frontier_cells(
    summary_rows_by_domain: dict[str, list[dict[str, str]]],
    query_row: dict[str, str],
    relevant_leaf_cells: set[str],
) -> list[tuple[str, int]]:
    if not relevant_leaf_cells:
        return []
    ancestors: set[str] = set()
    for cell_id in relevant_leaf_cells:
        ancestors.add(cell_id)
        if "-mc-" in cell_id:
            ancestors.add(cell_id.rsplit("-mc-", 1)[0])
        ancestors.add(_domain_root_for_cell(cell_id))

    matched: list[tuple[str, int]] = []
    for summary in summary_rows_by_domain.get(query_row["domain_id"], []):
        cell_id = summary["cell_id"]
        if cell_id not in ancestors:
            continue
        if not _matches_summary_bitmap(_parse_bitmap(summary.get("zone_bitmap", "")), query_row.get("zone_constraint", "")):
            continue
        if not _matches_summary_bitmap(
            _parse_bitmap(summary.get("zone_type_bitmap", "")),
            query_row.get("zone_type_constraint", ""),
        ):
            continue
        if not _matches_summary_bitmap(
            _parse_bitmap(summary.get("service_bitmap", "")),
            query_row.get("service_constraint", ""),
        ):
            continue
        if not _matches_summary_bitmap(
            _parse_bitmap(summary.get("freshness_bitmap", "")),
            query_row.get("freshness_constraint", ""),
        ):
            continue
        matched.append((cell_id, int(summary.get("level") or _cell_depth(cell_id))))
    return sorted(set(matched), key=lambda item: (item[1], item[0]))


def main() -> int:
    args = parse_args()
    queries = {
        row["query_id"]: row
        for row in read_csv(_resolve(args.queries))
        if row.get("workload_tier", "") == "object_main"
    }
    qrels_domain_rows = read_csv(_resolve(args.qrels_domain))
    qrels_object_rows = read_csv(_resolve(args.qrels_object))
    object_rows = read_csv(_resolve(args.objects))
    controller_rows = read_csv(_resolve(args.controller_local_index))
    summary_rows = read_csv(_resolve(args.hslsa))

    objects_by_id = {row["object_id"]: row for row in object_rows}
    relevant_domains_by_query: dict[str, set[str]] = defaultdict(set)
    for row in qrels_domain_rows:
        if row.get("is_relevant_domain", "1") == "1" and row["query_id"] in queries:
            relevant_domains_by_query[row["query_id"]].add(row["domain_id"])

    relevant_objects_by_query_domain: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in qrels_object_rows:
        if row["query_id"] not in queries:
            continue
        if int(row.get("relevance") or 0) >= 2:
            relevant_objects_by_query_domain[(row["query_id"], row["domain_id"])].append(row["object_id"])

    controller_rows_by_cell: dict[str, list[dict[str, str]]] = defaultdict(list)
    controller_cells_by_domain: dict[str, set[str]] = defaultdict(set)
    object_cells_by_domain_object: dict[tuple[str, str], set[str]] = defaultdict(set)
    controller_rows_by_frontier: dict[str, list[dict[str, str]]] = defaultdict(list)
    concrete_cells_by_frontier: dict[str, set[str]] = defaultdict(set)
    has_explicit_ancestor_frontier_index = False
    for row in controller_rows:
        controller_rows_by_cell[row["cell_id"]].append(row)
        controller_cells_by_domain[row["domain_id"]].add(row["cell_id"])
        object_cells_by_domain_object[(row["domain_id"], row["object_id"])].add(row["cell_id"])
        ancestor_frontier_ids = _split_semicolon_tokens(row.get("ancestor_frontier_ids", ""))
        if ancestor_frontier_ids:
            has_explicit_ancestor_frontier_index = True
            for frontier_hint_cell_id in ancestor_frontier_ids:
                controller_rows_by_frontier[frontier_hint_cell_id].append(row)
                concrete_cells_by_frontier[frontier_hint_cell_id].add(row["cell_id"])

    summary_rows_by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in summary_rows:
        summary_rows_by_domain[row["domain_id"]].append(row)

    output_rows: list[dict[str, Any]] = []
    zero_reason_counts: Counter[str] = Counter()
    missing_candidate_frontier_queries: list[str] = []

    for query_id, query in sorted(queries.items()):
        relevant_domains = sorted(relevant_domains_by_query.get(query_id, set()))
        for domain_id in relevant_domains:
            relevant_object_ids = sorted(relevant_objects_by_query_domain.get((query_id, domain_id), []))
            relevant_leaf_cells: set[str] = set()
            for object_id in relevant_object_ids:
                relevant_leaf_cells.update(object_cells_by_domain_object.get((domain_id, object_id), set()))

            query_with_domain = dict(query)
            query_with_domain["domain_id"] = domain_id
            candidate_cells = _candidate_frontier_cells(summary_rows_by_domain, query_with_domain, relevant_leaf_cells)
            if not candidate_cells:
                missing_candidate_frontier_queries.append(f"{query_id}:{domain_id}")
                output_rows.append(
                    {
                        "query_id": query_id,
                        "domain_id": domain_id,
                        "frontier_hint_cell_id": "",
                        "summary_level": "",
                        "candidate_frontier_cells": "",
                        "relevant_object_ids": ";".join(relevant_object_ids),
                        "relevant_object_cells": ";".join(sorted(relevant_leaf_cells)),
                        "exact_cell_exists": "0",
                        "descendant_cell_count": 0,
                        "candidate_object_count_pre_filter": 0,
                        "candidate_object_count_post_filter": 0,
                        "zero_reason": "summary_candidate_miss",
                    }
                )
                zero_reason_counts["summary_candidate_miss"] += 1
                continue

            candidate_frontier_cells = ";".join(cell_id for cell_id, _ in candidate_cells)
            for frontier_hint_cell_id, summary_level in candidate_cells:
                exact_rows = controller_rows_by_cell.get(frontier_hint_cell_id, [])
                exact_cell_exists = bool(exact_rows)
                descendant_cells: set[str] = set()
                if has_explicit_ancestor_frontier_index:
                    candidate_rows = controller_rows_by_frontier.get(frontier_hint_cell_id, [])
                    descendant_cells = set(concrete_cells_by_frontier.get(frontier_hint_cell_id, set()))
                    descendant_cells.discard(frontier_hint_cell_id)
                else:
                    descendant_rows: list[dict[str, str]] = []
                    descendant_prefix = frontier_hint_cell_id + "-"
                    for cell_id in controller_cells_by_domain.get(domain_id, set()):
                        if cell_id != frontier_hint_cell_id and cell_id.startswith(descendant_prefix):
                            descendant_cells.add(cell_id)
                            descendant_rows.extend(controller_rows_by_cell[cell_id])
                    candidate_rows = exact_rows if exact_rows else descendant_rows
                candidate_object_rows = [
                    objects_by_id[row["object_id"]]
                    for row in candidate_rows
                    if row["object_id"] in objects_by_id
                ]
                post_filter_rows = [
                    row for row in candidate_object_rows if _matches_object_query(row, query)
                ]

                zero_reason = ""
                if not candidate_object_rows:
                    if "-mc-" in frontier_hint_cell_id and not exact_cell_exists:
                        zero_reason = "cell_missing"
                    else:
                        zero_reason = "descendant_miss"
                elif not post_filter_rows:
                    zero_reason = _sequential_zero_reason(candidate_object_rows, query)
                if zero_reason:
                    zero_reason_counts[zero_reason] += 1

                output_rows.append(
                    {
                        "query_id": query_id,
                        "domain_id": domain_id,
                        "frontier_hint_cell_id": frontier_hint_cell_id,
                        "summary_level": summary_level,
                        "candidate_frontier_cells": candidate_frontier_cells,
                        "relevant_object_ids": ";".join(relevant_object_ids),
                        "relevant_object_cells": ";".join(sorted(relevant_leaf_cells)),
                        "exact_cell_exists": "1" if exact_cell_exists else "0",
                        "descendant_cell_count": len(descendant_cells),
                        "candidate_object_count_pre_filter": len(candidate_object_rows),
                        "candidate_object_count_post_filter": len(post_filter_rows),
                        "zero_reason": zero_reason,
                    }
                )

    write_csv(
        _resolve(args.details_csv),
        [
            "query_id",
            "domain_id",
            "frontier_hint_cell_id",
            "summary_level",
            "candidate_frontier_cells",
            "relevant_object_ids",
            "relevant_object_cells",
            "exact_cell_exists",
            "descendant_cell_count",
            "candidate_object_count_pre_filter",
            "candidate_object_count_post_filter",
            "zero_reason",
        ],
        output_rows,
    )

    summary_payload: dict[str, Any] = {
        "query_count": len(queries),
        "domain_candidate_rows": len(output_rows),
        "missing_candidate_frontier_query_domains": missing_candidate_frontier_queries[:20],
        "missing_candidate_frontier_query_domain_count": len(missing_candidate_frontier_queries),
        "zero_reason_counts": dict(sorted(zero_reason_counts.items())),
        "queries_with_post_filter_hits": sorted(
            {
                row["query_id"]
                for row in output_rows
                if int(row["candidate_object_count_post_filter"] or 0) > 0
            }
        )[:20],
    }
    summary_path = _resolve(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps(summary_payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
