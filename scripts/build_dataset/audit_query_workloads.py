"""Audit query/qrels consistency and workload-tier invariants."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_dataset.build_workload_tiers import parse_zone_constraint, zone_slot_token
from tools.dataset_support import load_dataset_manifest, output_path
from tools.workflow_support import load_json_yaml, read_csv, repo_root


DOMAIN_RE = re.compile(r"\b(domain-\d+)\b")
ZONE_RE = re.compile(r"\b(domain-\d+-zone-\d+)\b")


def _semantic_tiers(manifest: dict[str, Any]) -> tuple[str, str, str]:
    if manifest.get("dataset_id") == "smartcity":
        return ("routing_main", "object_main", "sanity_appendix")
    return ("routing_hard_v3", "object_hard_v3", "sanity_appendix_v3")


def _audit_output_path(manifest: dict[str, Any]) -> Path:
    filename = "workload_audit_mainline.json" if manifest.get("dataset_id") == "smartcity" else "workload_audit_v3.json"
    return repo_root() / "data" / "processed" / "eval" / filename


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


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _parse_embedding_rows(index_path: Path, vector_path: Path, id_key: str) -> dict[str, np.ndarray]:
    rows = read_csv(index_path)
    vectors = np.load(vector_path)
    return {row[id_key]: vectors[int(row["embedding_row"])] for row in rows}


def _audit_bundle_v3(
    bundle_id: str,
    bundle: dict[str, Any],
    object_rows: list[dict[str, str]],
    manifest: dict[str, Any],
    object_vectors: dict[str, np.ndarray],
    query_vectors: dict[str, np.ndarray],
    object_domain_by_id: dict[str, str],
    object_zone_by_id: dict[str, str],
    thresholds: dict[str, float],
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    routing_tier, object_tier, sanity_tier = _semantic_tiers(manifest)
    topology = load_json_yaml(_resolve(bundle["topology_config"]))
    active_domains = {row["domain_id"] for row in read_csv(repo_root() / topology["mapping_output_path"]) if row["domain_id"]}
    queries = read_csv(_resolve(bundle["queries_csv"]))
    qrels_object = read_csv(_resolve(bundle["qrels_object_csv"]))
    qrels_domain = read_csv(_resolve(bundle["qrels_domain_csv"]))

    qrels_object_by_query = _rows_by_query(qrels_object, "query_id")
    qrels_domain_by_query = _rows_by_query(qrels_domain, "query_id")
    test_counts = Counter(row["workload_tier"] for row in queries if row["split"] == "test")
    for tier in (routing_tier, object_tier, sanity_tier):
        if test_counts[tier] < 240:
            errors.append(f"{bundle_id}: {tier} has only {test_counts[tier]} test queries")

    summary: dict[str, dict[str, list[float] | int]] = {
        routing_tier: {
            "query_count": 0,
            "mean_relevant_domains": [],
            "mean_confuser_domains": [],
            "mean_candidates_per_relevant_domain": [],
            "explicit_domain_mentions": 0,
            "topology_inconsistent_queries": 0,
            "zone_constraint_coverage": [],
            "relevant_domain_count_support": [],
            "confuser_domain_count_support": [],
        },
        object_tier: {
            "query_count": 0,
            "mean_relevant_domains": [],
            "mean_confuser_objects_per_query": [],
            "manifest_rescue_potential_mean": [],
            "top1_top2_margin_mean": [],
            "topology_inconsistent_queries": 0,
            "zone_constraint_coverage": [],
            "relevant_domain_count_support": [],
            "confuser_object_count_support": [],
        },
        sanity_tier: {
            "query_count": 0,
            "mean_relevant_domains": [],
        },
    }

    for query in queries:
        query_id = query["query_id"]
        query_object_rows = qrels_object_by_query.get(query_id, [])
        domain_rows = qrels_domain_by_query.get(query_id, [])
        strong_domains = {row["domain_id"] for row in domain_rows if row.get("is_relevant_domain", "1") == "1"}
        weak_domains = {row["domain_id"] for row in domain_rows if row.get("relevance_strength", "") == "weak"}
        relevant_object_domains = {row["domain_id"] for row in query_object_rows if row.get("relevance") == "2"}
        relevant_zones = {
            object_zone_by_id[row["object_id"]]
            for row in query_object_rows
            if row["object_id"] in object_zone_by_id and row.get("relevance") == "2"
        }
        relevant_zone_tokens = {
            zone_slot_token(object_zone_by_id[row["object_id"]])
            for row in query_object_rows
            if row["object_id"] in object_zone_by_id and row.get("relevance") == "2"
        }

        if strong_domains != relevant_object_domains:
            errors.append(f"{bundle_id}: {query_id} qrels_object/qrels_domain mismatch")
        if not strong_domains.issubset(active_domains):
            errors.append(f"{bundle_id}: {query_id} has inactive relevant domains {sorted(strong_domains - active_domains)}")

        text = query.get("query_text", "")
        text_domains = set(DOMAIN_RE.findall(text))
        text_zones = set(ZONE_RE.findall(text))
        if text_domains and text_domains != strong_domains:
            errors.append(f"{bundle_id}: {query_id} explicit domain text disagrees with qrels")
        if text_zones and text_zones != relevant_zones:
            errors.append(f"{bundle_id}: {query_id} explicit zone text disagrees with qrels")

        zone_constraint = query.get("zone_constraint", "")
        zone_tokens = set(parse_zone_constraint(zone_constraint))
        if zone_constraint:
            if zone_tokens != relevant_zone_tokens:
                errors.append(f"{bundle_id}: {query_id} zone_constraint disagrees with qrels")
            inactive_zone_domains = sorted(
                {
                    token.split("-zone-")[0]
                    for token in zone_tokens
                    if token.startswith("domain-") and token.split("-zone-")[0] not in active_domains
                }
            )
            if inactive_zone_domains:
                errors.append(
                    f"{bundle_id}: {query_id} zone_constraint points to inactive domains {inactive_zone_domains}"
                )

        tier = query.get("workload_tier", "")
        domain_count = len(strong_domains)
        if tier == routing_tier:
            summary[tier]["query_count"] += 1
            summary[tier]["mean_relevant_domains"].append(float(domain_count))
            summary[tier]["mean_confuser_domains"].append(float(len(weak_domains)))
            summary[tier]["zone_constraint_coverage"].append(1.0 if zone_constraint else 0.0)
            summary[tier]["relevant_domain_count_support"].append(float(domain_count))
            summary[tier]["confuser_domain_count_support"].append(float(len(weak_domains)))
            summary[tier]["mean_candidates_per_relevant_domain"].append(
                float(len([row for row in query_object_rows if row["domain_id"] in strong_domains]))
                / max(1.0, float(len(strong_domains)))
            )
            if text_domains:
                summary[tier]["explicit_domain_mentions"] += 1
            if text_domains or text_zones or int(query.get("explicit_domain_mention", "0")) != 0:
                errors.append(f"{bundle_id}: {query_id} {routing_tier} contains explicit domain/zone mention")
            if not 2 <= domain_count <= 4:
                errors.append(f"{bundle_id}: {query_id} {routing_tier} relevant domains={domain_count}")
            if len(weak_domains) < 2:
                errors.append(f"{bundle_id}: {query_id} {routing_tier} confuser domains={len(weak_domains)}")
            if not zone_constraint:
                errors.append(f"{bundle_id}: {query_id} {routing_tier} missing zone_constraint")
            if not strong_domains.issubset(active_domains):
                summary[tier]["topology_inconsistent_queries"] += 1
        elif tier == object_tier:
            summary[tier]["query_count"] += 1
            summary[tier]["mean_relevant_domains"].append(float(domain_count))
            summary[tier]["zone_constraint_coverage"].append(1.0 if zone_constraint else 0.0)
            summary[tier]["relevant_domain_count_support"].append(float(domain_count))
            weak_object_count = sum(1 for row in query_object_rows if row.get("relevance") == "1")
            summary[tier]["mean_confuser_objects_per_query"].append(float(weak_object_count))
            summary[tier]["confuser_object_count_support"].append(float(weak_object_count))
            if not 1 <= domain_count <= 2:
                errors.append(f"{bundle_id}: {query_id} {object_tier} relevant domains={domain_count}")
            if weak_object_count < 4:
                errors.append(f"{bundle_id}: {query_id} {object_tier} confuser objects={weak_object_count}")
            if not zone_constraint:
                errors.append(f"{bundle_id}: {query_id} {object_tier} missing zone_constraint")
            query_vector = query_vectors.get(query_id)
            if query_vector is not None:
                strong_scores = [
                    _cosine(query_vector, object_vectors[row["object_id"]])
                    for row in query_object_rows
                    if row.get("relevance") == "2" and row["object_id"] in object_vectors
                ]
                weak_scores = [
                    _cosine(query_vector, object_vectors[row["object_id"]])
                    for row in query_object_rows
                    if row.get("relevance") == "1" and row["object_id"] in object_vectors
                ]
                if strong_scores and weak_scores:
                    margin = max(strong_scores) - max(weak_scores)
                    summary[tier]["top1_top2_margin_mean"].append(float(margin))
                    rescue = 1.0 if margin < thresholds["object_margin_threshold"] else 0.0
                    summary[tier]["manifest_rescue_potential_mean"].append(rescue)
            if not strong_domains.issubset(active_domains):
                summary[tier]["topology_inconsistent_queries"] += 1
        elif tier == sanity_tier:
            summary[tier]["query_count"] += 1
            summary[tier]["mean_relevant_domains"].append(float(domain_count))

    reduced = {}
    for tier, payload in summary.items():
        reduced[tier] = {}
        for key, value in payload.items():
            if isinstance(value, list):
                reduced[tier][key] = round(float(sum(value) / len(value)), 6) if value else 0.0
            else:
                reduced[tier][key] = value

    routing_summary = reduced[routing_tier]
    object_summary = reduced[object_tier]
    if routing_summary["mean_relevant_domains"] < 2.0:
        errors.append(f"{bundle_id}: {routing_tier} mean_relevant_domains={routing_summary['mean_relevant_domains']}")
    if routing_summary["mean_confuser_domains"] < 2.0:
        errors.append(f"{bundle_id}: {routing_tier} mean_confuser_domains={routing_summary['mean_confuser_domains']}")
    if routing_summary["explicit_domain_mentions"] > 0:
        errors.append(f"{bundle_id}: {routing_tier} explicit_domain_mentions={routing_summary['explicit_domain_mentions']}")
    if routing_summary["topology_inconsistent_queries"] > 0:
        errors.append(f"{bundle_id}: {routing_tier} topology_inconsistent_queries={routing_summary['topology_inconsistent_queries']}")
    if routing_summary["zone_constraint_coverage"] < 1.0:
        errors.append(f"{bundle_id}: {routing_tier} zone_constraint_coverage={routing_summary['zone_constraint_coverage']}")
    if {int(value) for value in summary[routing_tier]["relevant_domain_count_support"]} != {2, 3, 4}:
        errors.append(f"{bundle_id}: {routing_tier} relevant_domain_count_support={sorted({int(value) for value in summary[routing_tier]['relevant_domain_count_support']})}")
    if object_summary["mean_confuser_objects_per_query"] < 4.0:
        errors.append(
            f"{bundle_id}: {object_tier} mean_confuser_objects_per_query={object_summary['mean_confuser_objects_per_query']}"
        )
    if object_summary["top1_top2_margin_mean"] > thresholds["object_margin_threshold"]:
        errors.append(
            f"{bundle_id}: {object_tier} top1_top2_margin_mean={object_summary['top1_top2_margin_mean']}"
        )
    if object_summary["zone_constraint_coverage"] < 1.0:
        errors.append(f"{bundle_id}: {object_tier} zone_constraint_coverage={object_summary['zone_constraint_coverage']}")
    if {int(value) for value in summary[object_tier]["relevant_domain_count_support"]} != {1}:
        errors.append(f"{bundle_id}: {object_tier} relevant_domain_count_support={sorted({int(value) for value in summary[object_tier]['relevant_domain_count_support']})}")
    if len({int(value) for value in summary[object_tier]["confuser_object_count_support"]}) <= 1:
        errors.append(f"{bundle_id}: {object_tier} confuser_object_count_support collapsed")
    return errors, reduced


def main() -> int:
    args = parse_args()
    manifest = load_dataset_manifest(args.config)
    object_rows = read_csv(output_path(manifest, "objects_csv"))
    object_domain_by_id = {row["object_id"]: row["domain_id"] for row in object_rows}
    object_zone_by_id = {row["object_id"]: row["zone_id"] for row in object_rows}

    if manifest["dataset_id"] not in {"smartcity_v3", "smartcity"}:
        errors: list[str] = []
        for bundle_id, bundle in manifest.get("topology", {}).get("query_bundles", {}).items():
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
                object_rows_for_query = qrels_object_by_query.get(query_id, [])
                domain_rows = qrels_domain_by_query.get(query_id, [])
                relevant_domains = {row["domain_id"] for row in domain_rows if row.get("is_relevant_domain", "1") == "1"}
                relevant_object_domains = {row["domain_id"] for row in object_rows_for_query}
                relevant_zones = {object_zone_by_id[row["object_id"]] for row in object_rows_for_query if row["object_id"] in object_zone_by_id}
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
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("OK")
        return 0

    object_vectors = _parse_embedding_rows(
        output_path(manifest, "object_embedding_index_csv"),
        output_path(manifest, "object_embeddings_npy"),
        "object_id",
    )
    query_vectors = _parse_embedding_rows(
        output_path(manifest, "query_embedding_index_csv"),
        output_path(manifest, "query_embeddings_npy"),
        "query_id",
    )
    thresholds = load_json_yaml(_resolve(manifest["rules"]["query_generation"]))
    routing_tier, object_tier, sanity_tier = _semantic_tiers(manifest)
    summary_payload: dict[str, dict[str, Any]] = {
        routing_tier: {
            "query_count": 0,
            "mean_relevant_domains": 0.0,
            "mean_confuser_domains": 0.0,
            "mean_candidates_per_relevant_domain": 0.0,
            "explicit_domain_mentions": 0,
            "topology_inconsistent_queries": 0,
            "zone_constraint_coverage": 0.0,
            "relevant_domain_count_support": 0.0,
            "confuser_domain_count_support": 0.0,
        },
        object_tier: {
            "query_count": 0,
            "mean_relevant_domains": 0.0,
            "mean_confuser_objects_per_query": 0.0,
            "manifest_rescue_potential_mean": 0.0,
            "top1_top2_margin_mean": 0.0,
            "topology_inconsistent_queries": 0,
            "zone_constraint_coverage": 0.0,
            "relevant_domain_count_support": 0.0,
            "confuser_object_count_support": 0.0,
        },
        sanity_tier: {
            "query_count": 0,
            "mean_relevant_domains": 0.0,
        },
        "bundles": {},
    }

    errors: list[str] = []
    per_tier_counts = Counter()
    for bundle_id, bundle in manifest.get("topology", {}).get("query_bundles", {}).items():
        bundle_errors, bundle_summary = _audit_bundle_v3(
            bundle_id,
            bundle,
            object_rows,
            manifest,
            object_vectors,
            query_vectors,
            object_domain_by_id,
            object_zone_by_id,
            thresholds,
        )
        errors.extend(bundle_errors)
        summary_payload["bundles"][bundle_id] = bundle_summary
        for tier in (routing_tier, object_tier, sanity_tier):
            per_tier_counts[tier] += 1
            for key, value in bundle_summary[tier].items():
                if key == "query_count":
                    summary_payload[tier][key] += value
                elif isinstance(value, (int, float)):
                    summary_payload[tier][key] += value

    for tier in (routing_tier, object_tier, sanity_tier):
        bundles_total = max(1, per_tier_counts[tier])
        for key, value in list(summary_payload[tier].items()):
            if key == "query_count":
                continue
            summary_payload[tier][key] = round(float(value) / bundles_total, 6)

    audit_path = _audit_output_path(manifest)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps(summary_payload, indent=2) + "\n", encoding="utf-8")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(str(audit_path.relative_to(repo_root())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
