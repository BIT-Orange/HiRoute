"""Audit query/qrels consistency and workload-tier invariants."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, output_path
from tools.workflow_support import load_json_yaml, read_csv, repo_root


DOMAIN_RE = re.compile(r"\b(domain-\d+)\b")
ZONE_RE = re.compile(r"\b(domain-\d+-zone-\d+)\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v2.yaml", type=Path)
    return parser.parse_args()


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else repo_root() / path


def _rows_by_query(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["query_id"]].append(row)
    return grouped


def _audit_bundle(bundle_id: str,
                  bundle: dict[str, Any],
                  object_domain_by_id: dict[str, str],
                  object_zone_by_id: dict[str, str]) -> list[str]:
    errors: list[str] = []
    topology = load_json_yaml(_resolve(bundle["topology_config"]))
    active_domains = {row["domain_id"] for row in read_csv(repo_root() / topology["mapping_output_path"]) if row["domain_id"]}
    queries = read_csv(_resolve(bundle["queries_csv"]))
    qrels_object = read_csv(_resolve(bundle["qrels_object_csv"]))
    qrels_domain = read_csv(_resolve(bundle["qrels_domain_csv"]))

    qrels_object_by_query = _rows_by_query(qrels_object, "query_id")
    qrels_domain_by_query = _rows_by_query(qrels_domain, "query_id")
    test_counts = Counter(row["workload_tier"] for row in queries if row["split"] == "test")

    for tier in ("constraint_dominant", "routing_hard", "object_hard"):
        if test_counts[tier] < 240:
            errors.append(f"{bundle_id}: {tier} has only {test_counts[tier]} test queries")

    for query in queries:
        query_id = query["query_id"]
        object_rows = qrels_object_by_query.get(query_id, [])
        domain_rows = qrels_domain_by_query.get(query_id, [])
        relevant_domains = {row["domain_id"] for row in domain_rows if row.get("is_relevant_domain", "1") == "1"}
        relevant_object_domains = {row["domain_id"] for row in object_rows}
        relevant_zones = {object_zone_by_id[row["object_id"]] for row in object_rows if row["object_id"] in object_zone_by_id}

        if relevant_domains != relevant_object_domains:
            errors.append(f"{bundle_id}: {query_id} qrels_object/qrels_domain mismatch")
        if not relevant_domains.issubset(active_domains):
            errors.append(f"{bundle_id}: {query_id} has inactive relevant domains {sorted(relevant_domains - active_domains)}")

        text = query.get("query_text", "")
        text_domains = set(DOMAIN_RE.findall(text))
        text_zones = set(ZONE_RE.findall(text))
        if text_domains and text_domains != relevant_domains:
            errors.append(f"{bundle_id}: {query_id} explicit domain text disagrees with qrels")
        if text_zones and text_zones != relevant_zones:
            errors.append(f"{bundle_id}: {query_id} explicit zone text disagrees with qrels")

        zone_constraint = query.get("zone_constraint", "")
        if zone_constraint:
            if {zone_constraint} != relevant_zones:
                errors.append(f"{bundle_id}: {query_id} zone_constraint disagrees with qrels")
            zone_domain = zone_constraint.split("-zone-")[0]
            if zone_domain not in active_domains:
                errors.append(f"{bundle_id}: {query_id} zone_constraint points to inactive domain {zone_domain}")

        tier = query.get("workload_tier", "")
        domain_count = len(relevant_domains)
        if tier == "routing_hard" and not 1 <= domain_count <= 3:
            errors.append(f"{bundle_id}: {query_id} routing_hard relevant domains={domain_count}")
        if tier == "object_hard" and not 2 <= domain_count <= 4:
            errors.append(f"{bundle_id}: {query_id} object_hard relevant domains={domain_count}")
        if tier in {"routing_hard", "object_hard"}:
            if text_domains or text_zones:
                errors.append(f"{bundle_id}: {query_id} {tier} contains explicit domain/zone mention")
            if zone_constraint:
                errors.append(f"{bundle_id}: {query_id} {tier} should not carry zone_constraint")

    return errors


def main() -> int:
    args = parse_args()
    manifest = load_dataset_manifest(args.config)
    object_rows = read_csv(output_path(manifest, "objects_csv"))
    object_domain_by_id = {row["object_id"]: row["domain_id"] for row in object_rows}
    object_zone_by_id = {row["object_id"]: row["zone_id"] for row in object_rows}

    errors: list[str] = []
    for bundle_id, bundle in manifest.get("topology", {}).get("query_bundles", {}).items():
        errors.extend(_audit_bundle(bundle_id, bundle, object_domain_by_id, object_zone_by_id))

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
