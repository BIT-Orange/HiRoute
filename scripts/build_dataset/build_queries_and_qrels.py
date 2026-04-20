"""Generate query workloads and graded qrels for HiRoute."""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np

from scripts.build_dataset.build_workload_tiers import (
    humanize_token,
    join_ids,
    parse_zone_constraint,
    pick_style,
    render_query_text,
    stable_rotate,
    zone_constraint_value,
    zone_slot_token,
)
from tools.dataset_support import load_dataset_manifest, load_rule_config, output_path, read_jsonl
from tools.workflow_support import load_json_yaml, read_csv, write_csv


LOGGER = logging.getLogger("build_queries_and_qrels")
QUERY_FIELDS = [
    "query_id",
    "split",
    "ingress_node_id",
    "start_time_ms",
    "query_text",
    "zone_constraint",
    "zone_type_constraint",
    "service_constraint",
    "freshness_constraint",
    "ambiguity_level",
    "difficulty",
    "intended_domain_count",
    "ground_truth_count",
    "query_family",
    "workload_tier",
    "intent_facet",
    "query_text_id",
]

QUERY_FIELDS_V3 = [
    "query_id",
    "split",
    "ingress_node_id",
    "start_time_ms",
    "query_text",
    "zone_constraint",
    "zone_type_constraint",
    "service_constraint",
    "freshness_constraint",
    "ambiguity_level",
    "difficulty",
    "intended_domain_count",
    "ground_truth_count",
    "query_family",
    "workload_tier",
    "intent_facet",
    "query_text_id",
    "manifest_difficulty",
    "target_relevant_domains",
    "target_confuser_domains",
    "explicit_domain_mention",
    "explicit_zone_mention",
    "semantic_intent_family",
]

LEGACY_QUERY_FIELDS = [
    "query_id",
    "split",
    "ingress_node_id",
    "start_time_ms",
    "query_text",
    "zone_constraint",
    "zone_type_constraint",
    "service_constraint",
    "freshness_constraint",
    "ambiguity_level",
    "difficulty",
    "intended_domain_count",
    "query_text_id",
]

FAMILY_TO_LABEL = {
    "precise_template": ("low", "easy"),
    "paraphrase": ("medium", "medium"),
    "ambiguous": ("high", "hard"),
}

TIER_TO_LABEL = {
    "constraint_dominant": ("low", "easy"),
    "routing_hard": ("medium", "medium"),
    "object_hard": ("high", "hard"),
}

TIER_TO_LABEL_V3 = {
    "routing_hard_v3": ("high", "hard"),
    "object_hard_v3": ("high", "hard"),
    "sanity_appendix_v3": ("low", "easy"),
    "routing_main": ("high", "hard"),
    "object_main": ("high", "hard"),
    "sanity_appendix": ("low", "easy"),
}

QRELS_DOMAIN_FIELDS_V3 = [
    "query_id",
    "domain_id",
    "is_relevant_domain",
    "relevance_strength",
    "dominant_intent_match",
]

OBJECT_ROLE_RE = re.compile(r"-(snm|cnm|ncf)\d+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--topology-mapping", type=Path)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _family_counts(total: int, ratios: dict[str, float]) -> list[str]:
    families: list[str] = []
    for family, ratio in ratios.items():
        families.extend([family] * int(total * ratio))
    ordered = list(ratios)
    index = 0
    while len(families) < total:
        families.append(ordered[index % len(ordered)])
        index += 1
    return families[:total]


def _legacy_query_text(family: str, service_phrase: str, anchor: dict[str, str], drop_zone: bool, drop_freshness: bool) -> str:
    if family == "precise_template":
        return f"find {service_phrase} in {anchor['zone_id']} with {anchor['freshness_class']} freshness"
    if family == "paraphrase":
        if drop_zone:
            return f"need {service_phrase} updates around {anchor['zone_type']}"
        return f"need {service_phrase} readings near {anchor['zone_type']} in {anchor['domain_id']}"
    if drop_zone and drop_freshness:
        return f"show nearby {service_phrase} for busy areas"
    return f"show {service_phrase} updates in areas like {anchor['zone_type']}"


def _write_stats(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _run_legacy(manifest: dict[str, Any], topology_mapping_path: Path, rules: dict[str, Any]) -> int:
    objects = read_csv(output_path(manifest, "objects_csv"))
    object_texts = {row["object_id"]: row for row in read_jsonl(output_path(manifest, "object_texts_jsonl"))}
    topology_rows = read_csv(topology_mapping_path) if topology_mapping_path.exists() else []
    rng = random.Random(rules["seed"])

    service_synonyms = rules["service_synonyms"]
    ingress_nodes = [row["node_id"] for row in topology_rows if row["role"] == "ingress"]
    if not ingress_nodes:
        ingress_count = 8
        ingress_nodes = [f"ingress-slot-{index + 1}" for index in range(ingress_count)]

    by_service: dict[str, list[dict[str, str]]] = defaultdict(list)
    for obj in objects:
        by_service[obj["service_class"]].append(obj)
    anchor_pool = list(objects)
    rng.shuffle(anchor_pool)

    families = _family_counts(int(rules["queries_total"]), rules["families"])
    rng.shuffle(families)

    queries = []
    qrels_object = []
    qrels_domain = []

    for index, family in enumerate(families):
        anchor = anchor_pool[index % len(anchor_pool)]
        service_phrase = rng.choice(service_synonyms[anchor["service_class"]])
        drop_zone = rng.random() < float(rules["zone_drop_probability"].get(family, 0.0))
        drop_freshness = rng.random() < float(rules["freshness_drop_probability"].get(family, 0.0))
        query_id = f"q-{index + 1:04d}"
        query_text_id = f"qt-{query_id}"
        ambiguity_level, difficulty = FAMILY_TO_LABEL[family]
        max_domains = int(rules["max_domain_targets"][family])
        max_objects = int(rules["max_object_targets"][family])

        candidates = [
            row
            for row in by_service[anchor["service_class"]]
            if (drop_zone or row["zone_type"] == anchor["zone_type"])
            and (drop_freshness or row["freshness_class"] == anchor["freshness_class"])
        ]
        if family == "precise_template":
            candidates = [
                row for row in candidates if row["domain_id"] == anchor["domain_id"] and row["zone_id"] == anchor["zone_id"]
            ]
        elif family == "ambiguous":
            candidates.extend(
                row
                for row in by_service[anchor["service_class"]]
                if row["domain_id"] != anchor["domain_id"] and row not in candidates
            )

        domain_counts: dict[str, int] = defaultdict(int)
        relevant_objects = []
        for row in candidates:
            if domain_counts[row["domain_id"]] >= max(1, max_objects // max_domains):
                continue
            if len(domain_counts) >= max_domains and row["domain_id"] not in domain_counts:
                continue
            domain_counts[row["domain_id"]] += 1
            relevant_objects.append(row)
            if len(relevant_objects) >= max_objects:
                break

        if not relevant_objects:
            relevant_objects = [anchor]
            domain_counts = defaultdict(int, {anchor["domain_id"]: 1})

        split = "dev" if index < int(len(families) * float(rules["splits"]["dev"])) else "test"
        queries.append(
            {
                "query_id": query_id,
                "split": split,
                "ingress_node_id": ingress_nodes[index % len(ingress_nodes)],
                "start_time_ms": index * 100,
                "query_text": _legacy_query_text(family, service_phrase, anchor, drop_zone, drop_freshness),
                "zone_constraint": "" if drop_zone else anchor["zone_id"],
                "zone_type_constraint": anchor["zone_type"],
                "service_constraint": anchor["service_class"],
                "freshness_constraint": "" if drop_freshness else anchor["freshness_class"],
                "ambiguity_level": ambiguity_level,
                "difficulty": difficulty,
                "intended_domain_count": len(domain_counts),
                "query_text_id": query_text_id,
            }
        )

        for rel_index, record in enumerate(relevant_objects):
            qrels_object.append(
                {
                    "query_id": query_id,
                    "object_id": record["object_id"],
                    "relevance": 2 if rel_index < 2 else 1,
                }
            )
        for domain_id in sorted(domain_counts):
            qrels_domain.append(
                {
                    "query_id": query_id,
                    "domain_id": domain_id,
                    "is_relevant_domain": 1,
                }
            )

        _ = object_texts.get(anchor["object_id"])

    write_csv(output_path(manifest, "queries_csv"), LEGACY_QUERY_FIELDS, queries)
    write_csv(output_path(manifest, "qrels_object_csv"), ["query_id", "object_id", "relevance"], qrels_object)
    write_csv(output_path(manifest, "qrels_domain_csv"), ["query_id", "domain_id", "is_relevant_domain"], qrels_domain)
    stats = {
        "queries_total": len(queries),
        "family_distribution": {family: families.count(family) for family in sorted(set(families))},
        "mean_relevant_objects": round(len(qrels_object) / len(queries), 3),
        "mean_relevant_domains": round(len(qrels_domain) / len(queries), 3),
    }
    _write_stats(output_path(manifest, "qrels_domain_csv").parent / "query_stats.json", stats)
    LOGGER.info("generated %s legacy queries", len(queries))
    return 0


def _build_lookup(rows: list[dict[str, str]], keys: tuple[str, ...]) -> dict[tuple[str, ...], list[dict[str, str]]]:
    grouped: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in keys)].append(row)
    return grouped


def _stable_limit(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if limit <= 0:
        return []
    return sorted(rows, key=lambda row: row["object_id"])[:limit]


def _choose_domains(domain_map: dict[str, list[dict[str, str]]], domain_min: int, domain_max: int, slot: int) -> list[str]:
    domains = sorted(domain_map)
    if not domains:
        return []
    target = min(domain_max, len(domains))
    target = max(domain_min, target)
    offset = slot % len(domains)
    rotated = domains[offset:] + domains[:offset]
    return rotated[:target]


def _query_text(tier: str,
                family: str,
                service_phrase: str,
                intent_phrase: str,
                zone_type: str,
                freshness: str,
                zone_constraint: str,
                domain_id: str) -> str:
    if tier == "constraint_dominant":
        if family == "precise_template":
            return (
                f"find {intent_phrase} {service_phrase} in {zone_constraint} of {domain_id} "
                f"with {freshness} freshness"
            )
        return f"need {intent_phrase} {service_phrase} around {zone_type} in {domain_id} with {freshness} freshness"
    if tier == "routing_hard":
        if family == "paraphrase":
            return f"need {intent_phrase} {service_phrase} around {zone_type} with {freshness} freshness"
        return f"show {intent_phrase} {service_phrase} updates near {zone_type} under {freshness} conditions"
    if family == "paraphrase":
        return f"need {intent_phrase} {service_phrase} around {zone_type}"
    return f"show {intent_phrase} {service_phrase} options for areas like {zone_type}"


def _bundle_output(bundle: dict[str, Any], key: str) -> Path:
    return Path(bundle[key]) if Path(bundle[key]).is_absolute() else ROOT / bundle[key]


def _object_role(object_id: str) -> str:
    match = OBJECT_ROLE_RE.search(object_id)
    if match is None:
        return "target"
    token = match.group(1)
    return {
        "snm": "semantic_near_miss",
        "cnm": "constraint_near_miss",
        "ncf": "naming_confuser",
    }.get(token, "target")


def _parse_embedding_rows(index_path: Path, vector_path: Path, id_key: str) -> dict[str, np.ndarray]:
    rows = read_csv(index_path)
    vectors = np.load(vector_path)
    return {row[id_key]: vectors[int(row["embedding_row"])] for row in rows}


def _cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _choose_count(minimum: int, maximum: int, slot: int) -> int:
    if maximum <= minimum:
        return minimum
    return minimum + (slot % (maximum - minimum + 1))


def _stable_pick(rows: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: row["object_id"])[:limit]


def _stable_sample(values: list[str], count: int, slot: int) -> list[str]:
    if count <= 0:
        return []
    rotated = stable_rotate(values, slot)
    return rotated[: min(count, len(rotated))]


def _stable_row_sample(rows: list[dict[str, str]], count: int, slot: int) -> list[dict[str, str]]:
    if count <= 0:
        return []
    ordered = sorted(rows, key=lambda row: row["object_id"])
    if not ordered:
        return []
    offset = slot % len(ordered)
    rotated = ordered[offset:] + ordered[:offset]
    return rotated[: min(count, len(rotated))]


def _semantic_dataset_tiers(manifest: dict[str, Any]) -> tuple[str, str, str]:
    if manifest.get("dataset_id") == "smartcity":
        return ("routing_main", "object_main", "sanity_appendix")
    return ("routing_hard_v3", "object_hard_v3", "sanity_appendix_v3")


def _relevant_domain_rows(selected_domains: list[str], confuser_domains: list[str]) -> list[dict[str, str]]:
    rows = []
    for domain_id in selected_domains:
        rows.append(
            {
                "domain_id": domain_id,
                "is_relevant_domain": 1,
                "relevance_strength": "strong",
                "dominant_intent_match": 1,
            }
        )
    for domain_id in confuser_domains:
        rows.append(
            {
                "domain_id": domain_id,
                "is_relevant_domain": 0,
                "relevance_strength": "weak",
                "dominant_intent_match": 0,
            }
        )
    return rows


def _generate_v3_queries(manifest: dict[str, Any], rules: dict[str, Any]) -> int:
    objects = read_csv(output_path(manifest, "objects_csv"))
    topology_bundles = manifest.get("topology", {}).get("query_bundles", {})
    if not topology_bundles:
        raise ValueError("smartcity_v3 requires topology.query_bundles")

    routing_tier, object_tier, sanity_tier = _semantic_dataset_tiers(manifest)
    service_synonyms = rules["service_synonyms"]
    style_weights = rules["text_styles"]
    rng = random.Random(rules["seed"])

    global_queries: list[dict[str, Any]] = []
    global_qrels_object: list[dict[str, Any]] = []
    global_qrels_domain: list[dict[str, Any]] = []
    bundle_stats: dict[str, Any] = {}

    for bundle_id, bundle in topology_bundles.items():
        topology = load_json_yaml(ROOT / bundle["topology_config"])
        topology_rows = read_csv(ROOT / topology["mapping_output_path"])
        active_domains = sorted({row["domain_id"] for row in topology_rows if row["domain_id"]})
        ingress_nodes = [row["node_id"] for row in topology_rows if row["role"] == "ingress"]
        if not ingress_nodes:
            raise ValueError(f"{bundle_id} has no ingress nodes in topology mapping")

        active_objects = [row for row in objects if row["domain_id"] in set(active_domains)]
        if not active_objects:
            raise ValueError(f"{bundle_id} has no active objects")

        by_route_base_slot_target: dict[tuple[str, str, str], dict[str, dict[str, list[dict[str, str]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        by_route_base_slot_all: dict[tuple[str, str, str], dict[str, dict[str, list[dict[str, str]]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        by_route_service_domain: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        by_object_key: dict[tuple[str, str, str, str], dict[str, list[dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
        by_domain_service_zone_fresh: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
        by_domain_service_zone: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
        by_confuser_group: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)

        for row in active_objects:
            role = _object_role(row["object_id"])
            row = dict(row)
            row["_role"] = role
            family = row.get("semantic_intent_family", row.get("semantic_facet", row["service_class"]))
            zone_token = zone_slot_token(row["zone_id"])
            if row.get("difficulty_tag") == "routing_hard" and role == "target":
                by_route_base_slot_target[(row["service_class"], row["zone_type"], row["freshness_class"])][zone_token][row["domain_id"]].append(row)
            if row.get("difficulty_tag") == "routing_hard":
                by_route_base_slot_all[(row["service_class"], row["zone_type"], row["freshness_class"])][zone_token][row["domain_id"]].append(row)
                by_route_service_domain[row["service_class"]][row["domain_id"]].append(row)
            if row.get("difficulty_tag") == "object_hard":
                by_domain_service_zone_fresh[(row["domain_id"], row["service_class"], row["zone_type"], row["freshness_class"])].append(row)
                by_domain_service_zone[(row["domain_id"], row["service_class"], row["zone_type"])].append(row)
                by_confuser_group[(row["domain_id"], row["confuser_group_id"])].append(row)
                if role == "target":
                    by_object_key[(row["service_class"], row["zone_type"], row["freshness_class"], family)][row["domain_id"]].append(row)

        routing_candidates = []
        for base_key, target_slots in sorted(by_route_base_slot_target.items()):
            slot_pool = sorted(target_slots)
            if not slot_pool:
                continue
            all_slots = by_route_base_slot_all[base_key]
            broad_by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
            for zone_rows in all_slots.values():
                for domain_id, rows in zone_rows.items():
                    broad_by_domain[domain_id].extend(rows)
            service_broad_by_domain = {
                domain_id: sorted(rows, key=lambda row: row["object_id"])
                for domain_id, rows in by_route_service_domain[base_key[0]].items()
            }
            for token_count in range(1, min(4, len(slot_pool)) + 1):
                for zone_tokens in combinations(slot_pool, token_count):
                    strong_by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
                    strong_by_token_domain: dict[str, dict[str, list[dict[str, str]]]] = defaultdict(
                        lambda: defaultdict(list)
                    )
                    for zone_token in zone_tokens:
                        for domain_id, rows in target_slots[zone_token].items():
                            strong_by_token_domain[zone_token][domain_id].extend(rows)
                            strong_by_domain[domain_id].extend(rows)
                    strong_domains = sorted(strong_by_domain)
                    confuser_domains = sorted(set(service_broad_by_domain) - set(strong_domains))
                    if not 2 <= len(strong_domains) <= 4 or len(confuser_domains) < 2:
                        continue
                    anchor_rows = [row for domain_id in strong_domains for row in strong_by_domain[domain_id]]
                    anchor_rows = sorted(anchor_rows, key=lambda row: row["object_id"])
                    anchor_family = (
                        anchor_rows[0].get("semantic_intent_family", anchor_rows[0].get("semantic_facet", ""))
                        if anchor_rows else ""
                    )
                    routing_candidates.append(
                        {
                            "base_key": base_key,
                            "zone_tokens": list(zone_tokens),
                            "strong_by_domain": {
                                domain_id: sorted(rows, key=lambda row: row["object_id"])
                                for domain_id, rows in strong_by_domain.items()
                            },
                            "strong_by_token_domain": {
                                zone_token: {
                                    domain_id: sorted(rows, key=lambda row: row["object_id"])
                                    for domain_id, rows in domain_payload.items()
                                }
                                for zone_token, domain_payload in strong_by_token_domain.items()
                            },
                            "broad_by_domain": {
                                domain_id: sorted(rows, key=lambda row: row["object_id"])
                                for domain_id, rows in broad_by_domain.items()
                            },
                            "service_broad_by_domain": service_broad_by_domain,
                            "confuser_domains": confuser_domains,
                            "anchor_family": anchor_family,
                        }
                    )

        object_candidates = []
        for key, strong_by_domain in sorted(by_object_key.items()):
            eligible_domains = {}
            for domain_id, targets in strong_by_domain.items():
                candidate_pool = [
                    row
                    for row in by_domain_service_zone_fresh[(domain_id, key[0], key[1], key[2])]
                    if row.get("difficulty_tag") == "object_hard"
                ]
                semantic_confusers = [row for row in candidate_pool if row["_role"] == "semantic_near_miss"]
                constraint_like = [
                    row for row in candidate_pool if row["_role"] in {"constraint_near_miss", "naming_confuser"}
                ]
                if len(candidate_pool) >= 6 and len(semantic_confusers) >= 3 and len(constraint_like) >= 2:
                    groups: dict[str, dict[str, list[dict[str, str]]]] = {}
                    for target in targets:
                        group_rows = by_confuser_group[(domain_id, target["confuser_group_id"])]
                        target_group = [row for row in group_rows if row["_role"] == "target"]
                        semantic_group = [row for row in group_rows if row["_role"] == "semantic_near_miss"]
                        constraint_group = [row for row in group_rows if row["_role"] == "constraint_near_miss"]
                        naming_group = [row for row in group_rows if row["_role"] == "naming_confuser"]
                        weak_pool = sorted(
                            [
                                row
                                for row in candidate_pool
                                if row["object_id"] != target["object_id"]
                            ],
                            key=lambda row: (
                                0 if row.get("confuser_group_id") == target["confuser_group_id"] else 1,
                                0
                                if row.get("semantic_intent_family", row.get("semantic_facet", ""))
                                == key[3]
                                else 1,
                                0
                                if row["_role"] == "naming_confuser"
                                else 1
                                if row["_role"] == "target"
                                else 2
                                if row["_role"] == "semantic_near_miss"
                                else 3,
                                row["object_id"],
                            ),
                        )
                        if (
                            target_group
                            and semantic_group
                            and (constraint_group or naming_group)
                            and len(weak_pool) >= 6
                        ):
                            groups[target["confuser_group_id"]] = {
                                "targets": sorted(target_group, key=lambda row: row["object_id"]),
                                "semantic_confusers": sorted(semantic_group, key=lambda row: row["object_id"]),
                                "constraint_confusers": sorted(constraint_group, key=lambda row: row["object_id"]),
                                "naming_confusers": sorted(naming_group, key=lambda row: row["object_id"]),
                                "weak_pool": weak_pool,
                            }
                    if not groups:
                        continue
                    eligible_domains[domain_id] = {
                        "targets": sorted(targets, key=lambda row: row["object_id"]),
                        "candidate_pool": candidate_pool,
                        "semantic_confusers": semantic_confusers,
                        "constraint_like": constraint_like,
                        "groups": groups,
                    }
            if len(eligible_domains) >= 1:
                object_candidates.append((key, eligible_domains))

        sanity_candidates = []
        for base_key, target_slots in sorted(by_route_base_slot_target.items()):
            for zone_token, strong_by_domain in sorted(target_slots.items()):
                if not 1 <= len(strong_by_domain) <= 2:
                    continue
                anchor_rows = [
                    row for domain_id in sorted(strong_by_domain) for row in sorted(strong_by_domain[domain_id], key=lambda row: row["object_id"])
                ]
                family = (
                    anchor_rows[0].get("semantic_intent_family", anchor_rows[0].get("semantic_facet", ""))
                    if anchor_rows else ""
                )
                sanity_candidates.append(((*base_key, family), strong_by_domain))

        routing_candidates_by_count: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for candidate in routing_candidates:
            routing_candidates_by_count[len(candidate["strong_by_domain"])].append(candidate)

        if (
            not routing_candidates
            or not object_candidates
            or not sanity_candidates
            or any(not routing_candidates_by_count[count] for count in (2, 3, 4))
        ):
            raise ValueError(f"{bundle_id} does not have enough v3 candidates for all workload tiers")

        bundle_queries: list[dict[str, Any]] = []
        bundle_qrels_object: list[dict[str, Any]] = []
        bundle_qrels_domain: list[dict[str, Any]] = []
        start_time_ms = 0

        def next_query_id(tier: str) -> str:
            return f"q-{bundle_id}-{tier}-{len(bundle_queries) + 1:04d}"

        for tier, tier_rules in rules["workload_tiers"].items():
            total_queries = int(tier_rules["dev"]) + int(tier_rules["test"])
            for tier_index in range(total_queries):
                split = "dev" if tier_index < int(tier_rules["dev"]) else "test"
                style = pick_style(style_weights, tier_index)
                ambiguity_level, base_difficulty = TIER_TO_LABEL_V3[tier]
                selected_zone_tokens: list[str] = []

                if tier == routing_tier:
                    strong_count = _choose_count(
                        int(tier_rules["relevant_domains_range"][0]),
                        int(tier_rules["relevant_domains_range"][1]),
                        tier_index,
                    )
                    candidate_pool = routing_candidates_by_count[strong_count]
                    candidate = candidate_pool[(tier_index // max(1, len(routing_candidates_by_count))) % len(candidate_pool)]
                    service_class, zone_type, freshness_class = candidate["base_key"]
                    family = candidate["anchor_family"]
                    weak_count = _choose_count(
                        int(tier_rules["confuser_domains_range"][0]),
                        int(tier_rules["confuser_domains_range"][1]),
                        tier_index,
                    )
                    selected_domains = sorted(candidate["strong_by_domain"])
                    selected_confusers = _stable_sample(candidate["confuser_domains"], weak_count, tier_index + 3)
                    relevant_objects = []
                    weak_objects = []
                    selected_zone_tokens = list(candidate["zone_tokens"])
                    relevant_object_ids: set[str] = set()
                    for token_slot, zone_token in enumerate(selected_zone_tokens):
                        token_payload = candidate["strong_by_token_domain"][zone_token]
                        for domain_slot, domain_id in enumerate(selected_domains):
                            if domain_id not in token_payload:
                                continue
                            chosen = _stable_row_sample(token_payload[domain_id], 1, tier_index + token_slot + domain_slot)
                            relevant_objects.extend(chosen)
                            relevant_object_ids.update(row["object_id"] for row in chosen)
                    for domain_slot, domain_id in enumerate(selected_domains):
                        same_domain_pool = [
                            row
                            for row in candidate["broad_by_domain"][domain_id]
                            if row["object_id"] not in relevant_object_ids
                        ]
                        weak_objects.extend(_stable_row_sample(same_domain_pool, 1, tier_index + domain_slot + 1))
                    for domain_slot, domain_id in enumerate(selected_confusers):
                        weak_objects.extend(
                            _stable_row_sample(
                                candidate["service_broad_by_domain"][domain_id],
                                1,
                                tier_index + len(selected_domains) + domain_slot,
                            )
                        )
                    manifest_difficulty = "hard" if len(selected_confusers) >= 4 or len(selected_domains) >= 3 else "medium"
                elif tier == object_tier:
                    key, eligible_domains = object_candidates[tier_index % len(object_candidates)]
                    service_class, zone_type, freshness_class, family = key
                    relevant_count = _choose_count(
                        int(tier_rules["relevant_domains_range"][0]),
                        int(tier_rules["relevant_domains_range"][1]),
                        tier_index,
                    )
                    confuser_domain_count = _choose_count(
                        int(tier_rules["confuser_domains_range"][0]),
                        int(tier_rules["confuser_domains_range"][1]),
                        tier_index,
                    )
                    selected_domains = _stable_sample(list(eligible_domains), relevant_count, tier_index)
                    selected_confusers = _stable_sample([], confuser_domain_count, tier_index + 5)
                    relevant_objects = []
                    weak_objects = []
                    weak_object_floor = int(tier_rules.get("confuser_objects_per_query_min", 6))
                    for domain_slot, domain_id in enumerate(selected_domains):
                        payload = eligible_domains[domain_id]
                        group_ids = sorted(payload["groups"])
                        group_id = group_ids[(tier_index + domain_slot) % len(group_ids)]
                        group_payload = payload["groups"][group_id]
                        chosen_target = _stable_row_sample(group_payload["targets"], 1, tier_index + domain_slot)
                        relevant_objects.extend(chosen_target)
                        selected_zone_tokens.extend(zone_slot_token(row["zone_id"]) for row in chosen_target)
                        weak_limit = min(
                            len(group_payload["weak_pool"]),
                            weak_object_floor + (tier_index % 3),
                        )
                        weak_window = group_payload["weak_pool"][: min(len(group_payload["weak_pool"]), weak_limit + 2)]
                        weak_offset_span = max(1, len(weak_window) - weak_limit + 1)
                        weak_offset = (tier_index + domain_slot) % weak_offset_span
                        weak_objects.extend(weak_window[weak_offset : weak_offset + weak_limit])
                    mix = tier_rules["manifest_difficulty_mix"]
                    manifest_difficulty = pick_style(mix, tier_index)
                else:
                    key, strong_by_domain = sanity_candidates[tier_index % len(sanity_candidates)]
                    service_class, zone_type, freshness_class, family = key
                    relevant_count = _choose_count(
                        int(tier_rules["relevant_domains_range"][0]),
                        int(tier_rules["relevant_domains_range"][1]),
                        tier_index,
                    )
                    selected_domains = sorted(strong_by_domain)[:relevant_count]
                    selected_confusers = []
                    relevant_objects = []
                    weak_objects = []
                    for domain_id in selected_domains:
                        relevant_objects.extend(_stable_pick(strong_by_domain[domain_id], 1))
                    manifest_difficulty = "easy"

                if not relevant_objects:
                    continue

                ranked_by_object: dict[str, tuple[int, dict[str, str]]] = {}
                for record in weak_objects:
                    ranked_by_object[record["object_id"]] = (1, record)
                for record in relevant_objects:
                    ranked_by_object[record["object_id"]] = (2, record)
                relevant_objects = [
                    record
                    for relevance, record in (
                        ranked_by_object[object_id] for object_id in sorted(ranked_by_object)
                    )
                    if relevance == 2
                ]
                weak_objects = [
                    record
                    for relevance, record in (
                        ranked_by_object[object_id] for object_id in sorted(ranked_by_object)
                    )
                    if relevance == 1
                ]

                query_id = next_query_id(tier)
                query_text_id = f"qt-{query_id}"
                service_phrase = rng.choice(service_synonyms[service_class])
                intent_phrase = humanize_token(family)
                query_text = render_query_text(
                    style,
                    service_phrase,
                    intent_phrase,
                    humanize_token(zone_type),
                    humanize_token(freshness_class),
                    tier,
                )

                query_row = {
                    "query_id": query_id,
                    "split": split,
                    "ingress_node_id": ingress_nodes[(len(bundle_queries)) % len(ingress_nodes)],
                    "start_time_ms": start_time_ms,
                    "query_text": query_text,
                    "zone_constraint": (
                        zone_constraint_value(selected_zone_tokens) if tier_rules["require_zone_constraint"] else ""
                    ),
                    "zone_type_constraint": zone_type,
                    "service_constraint": service_class,
                    "freshness_constraint": freshness_class if tier_rules["require_freshness_constraint"] else "",
                    "ambiguity_level": ambiguity_level,
                    "difficulty": manifest_difficulty if tier == object_tier else base_difficulty,
                    "intended_domain_count": len(selected_domains),
                    "ground_truth_count": len(relevant_objects),
                    "query_family": style,
                    "workload_tier": tier,
                    "intent_facet": "" if tier == routing_tier else family,
                    "query_text_id": query_text_id,
                    "manifest_difficulty": manifest_difficulty,
                    "target_relevant_domains": join_ids(selected_domains),
                    "target_confuser_domains": join_ids(selected_confusers),
                    "explicit_domain_mention": 0,
                    "explicit_zone_mention": 0,
                    "semantic_intent_family": family,
                }
                bundle_queries.append(query_row)
                global_queries.append(query_row)

                for record in relevant_objects:
                    qrels_object_row = {
                        "query_id": query_id,
                        "object_id": record["object_id"],
                        "domain_id": record["domain_id"],
                        "relevance": 2,
                    }
                    bundle_qrels_object.append(qrels_object_row)
                    global_qrels_object.append(qrels_object_row)
                for record in weak_objects:
                    qrels_object_row = {
                        "query_id": query_id,
                        "object_id": record["object_id"],
                        "domain_id": record["domain_id"],
                        "relevance": 1,
                    }
                    bundle_qrels_object.append(qrels_object_row)
                    global_qrels_object.append(qrels_object_row)

                domain_rows = _relevant_domain_rows(selected_domains, selected_confusers)
                for domain_row in domain_rows:
                    payload = {"query_id": query_id, **domain_row}
                    bundle_qrels_domain.append(payload)
                    global_qrels_domain.append(payload)
                start_time_ms += 100

        write_csv(_bundle_output(bundle, "queries_csv"), QUERY_FIELDS_V3, bundle_queries)
        write_csv(
            _bundle_output(bundle, "qrels_object_csv"),
            ["query_id", "object_id", "domain_id", "relevance"],
            bundle_qrels_object,
        )
        write_csv(_bundle_output(bundle, "qrels_domain_csv"), QRELS_DOMAIN_FIELDS_V3, bundle_qrels_domain)
        bundle_stats[bundle_id] = {
            "queries_total": len(bundle_queries),
            "test_counts": Counter(row["workload_tier"] for row in bundle_queries if row["split"] == "test"),
            "dev_counts": Counter(row["workload_tier"] for row in bundle_queries if row["split"] == "dev"),
            "mean_relevant_objects": round(
                sum(1 for row in bundle_qrels_object if row["relevance"] == 2) / max(1, len(bundle_queries)),
                3,
            ),
            "mean_relevant_domains": round(
                sum(1 for row in bundle_qrels_domain if row["is_relevant_domain"] == 1) / max(1, len(bundle_queries)),
                3,
            ),
        }

    write_csv(output_path(manifest, "queries_csv"), QUERY_FIELDS_V3, global_queries)
    write_csv(
        output_path(manifest, "qrels_object_csv"),
        ["query_id", "object_id", "domain_id", "relevance"],
        global_qrels_object,
    )
    write_csv(output_path(manifest, "qrels_domain_csv"), QRELS_DOMAIN_FIELDS_V3, global_qrels_domain)
    stats = {
        "queries_total": len(global_queries),
        "bundle_stats": {
            bundle_id: {
                "queries_total": payload["queries_total"],
                "test_counts": dict(payload["test_counts"]),
                "dev_counts": dict(payload["dev_counts"]),
                "mean_relevant_objects": payload["mean_relevant_objects"],
                "mean_relevant_domains": payload["mean_relevant_domains"],
            }
            for bundle_id, payload in bundle_stats.items()
        },
    }
    _write_stats(output_path(manifest, "qrels_domain_csv").parent / "query_stats.json", stats)
    LOGGER.info("generated %s semantic queries", len(global_queries))
    return 0


def _generate_v2_queries(manifest: dict[str, Any], rules: dict[str, Any]) -> int:
    objects = read_csv(output_path(manifest, "objects_csv"))
    topology_bundles = manifest.get("topology", {}).get("query_bundles", {})
    if not topology_bundles:
        raise ValueError("smartcity_v2 requires topology.query_bundles")

    service_synonyms = rules["service_synonyms"]
    intent_phrases = rules["intent_phrases"]
    tier_difficulty = rules["tier_difficulty"]
    rng = random.Random(rules["seed"])

    global_queries: list[dict[str, Any]] = []
    global_qrels_object: list[dict[str, Any]] = []
    global_qrels_domain: list[dict[str, Any]] = []
    bundle_stats: dict[str, Any] = {}

    for bundle_id, bundle in topology_bundles.items():
        topology = load_json_yaml(ROOT / bundle["topology_config"])
        topology_rows = read_csv(ROOT / topology["mapping_output_path"])
        active_domains = sorted({row["domain_id"] for row in topology_rows if row["domain_id"]})
        ingress_nodes = [row["node_id"] for row in topology_rows if row["role"] == "ingress"]
        active_objects = [row for row in objects if row["domain_id"] in set(active_domains)]
        if not ingress_nodes:
            raise ValueError(f"{bundle_id} has no ingress nodes in topology mapping")

        by_zone = _build_lookup(active_objects, ("domain_id", "zone_id", "service_class", "freshness_class", "semantic_facet"))
        routing_groups = _build_lookup(active_objects, ("service_class", "zone_type", "freshness_class", "semantic_facet"))
        object_groups = _build_lookup(active_objects, ("service_class", "zone_type", "semantic_facet"))

        bundle_queries: list[dict[str, Any]] = []
        bundle_qrels_object: list[dict[str, Any]] = []
        bundle_qrels_domain: list[dict[str, Any]] = []
        start_time_ms = 0

        constraint_candidates = [
            (key, rows)
            for key, rows in sorted(by_zone.items())
            if rows
        ]
        routing_candidates = []
        for key, rows in sorted(routing_groups.items()):
            per_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                per_domain[row["domain_id"]].append(row)
            domain_count = len(per_domain)
            if 1 <= domain_count <= 3:
                routing_candidates.append((key, per_domain))
        object_candidates = []
        for key, rows in sorted(object_groups.items()):
            per_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
            for row in rows:
                per_domain[row["domain_id"]].append(row)
            eligible = {domain_id: items for domain_id, items in per_domain.items() if len(items) >= 2}
            domain_count = len(eligible)
            if 2 <= domain_count <= 4:
                object_candidates.append((key, eligible))

        if not constraint_candidates or not routing_candidates or not object_candidates:
            raise ValueError(f"{bundle_id} does not have enough candidates for all workload tiers")

        for tier, tier_rules in rules["workload_tiers"].items():
            total_queries = int(tier_rules["dev"]) + int(tier_rules["test"])
            families = _family_counts(total_queries, tier_rules["families"])
            if tier == "constraint_dominant":
                candidates = constraint_candidates
            elif tier == "routing_hard":
                candidates = routing_candidates
            else:
                candidates = object_candidates

            for tier_index, family in enumerate(families):
                if tier == "constraint_dominant":
                    key, rows = candidates[tier_index % len(candidates)]
                    domain_id, zone_id, service_class, freshness_class, intent_facet = key
                    zone_type = rows[0]["zone_type"]
                    per_domain = {domain_id: rows}
                    selected_domains = [domain_id]
                    per_domain_limit = int(tier_rules["relevant_objects_per_domain"]["max"])
                    relevant_objects = _stable_limit(rows, per_domain_limit)
                    zone_constraint = zone_id
                    freshness_constraint = freshness_class
                elif tier == "routing_hard":
                    key, per_domain = candidates[tier_index % len(candidates)]
                    service_class, zone_type, freshness_class, intent_facet = key
                    selected_domains = _choose_domains(
                        per_domain,
                        int(tier_rules["relevant_domains"]["min"]),
                        int(tier_rules["relevant_domains"]["max"]),
                        tier_index,
                    )
                    per_domain_limit = int(tier_rules["relevant_objects_per_domain"]["max"])
                    relevant_objects = []
                    for domain_id in selected_domains:
                        relevant_objects.extend(_stable_limit(per_domain[domain_id], per_domain_limit))
                    zone_constraint = ""
                    freshness_constraint = freshness_class if tier_rules["require_freshness_constraint"] else ""
                else:
                    key, per_domain = candidates[tier_index % len(candidates)]
                    service_class, zone_type, intent_facet = key
                    selected_domains = _choose_domains(
                        per_domain,
                        int(tier_rules["relevant_domains"]["min"]),
                        int(tier_rules["relevant_domains"]["max"]),
                        tier_index,
                    )
                    per_domain_limit = int(tier_rules["relevant_objects_per_domain"]["max"])
                    relevant_objects = []
                    for domain_id in selected_domains:
                        relevant_objects.extend(_stable_limit(per_domain[domain_id], per_domain_limit))
                    zone_constraint = ""
                    freshness_constraint = ""

                if not relevant_objects:
                    continue

                query_number = len(bundle_queries) + 1
                query_id = f"q-{bundle_id}-{tier}-{query_number:04d}"
                query_text_id = f"qt-{query_id}"
                service_phrase = rng.choice(service_synonyms[service_class])
                intent_phrase = rng.choice(intent_phrases.get(intent_facet, [intent_facet.replace("_", " ")]))
                split = "dev" if tier_index < int(tier_rules["dev"]) else "test"
                ambiguity_level, _ = TIER_TO_LABEL[tier]
                query_text = _query_text(
                    tier,
                    family,
                    service_phrase,
                    intent_phrase,
                    zone_type,
                    freshness_constraint or "recent",
                    zone_constraint,
                    selected_domains[0],
                )

                query_row = {
                    "query_id": query_id,
                    "split": split,
                    "ingress_node_id": ingress_nodes[(query_number - 1) % len(ingress_nodes)],
                    "start_time_ms": start_time_ms,
                    "query_text": query_text,
                    "zone_constraint": zone_constraint if tier_rules["require_zone_constraint"] else "",
                    "zone_type_constraint": zone_type,
                    "service_constraint": service_class,
                    "freshness_constraint": freshness_constraint,
                    "ambiguity_level": ambiguity_level,
                    "difficulty": tier_difficulty[tier],
                    "intended_domain_count": len(selected_domains),
                    "ground_truth_count": len(relevant_objects),
                    "query_family": family,
                    "workload_tier": tier,
                    "intent_facet": intent_facet,
                    "query_text_id": query_text_id,
                }
                bundle_queries.append(query_row)
                global_queries.append(query_row)

                for rel_index, record in enumerate(relevant_objects):
                    qrels_row = {
                        "query_id": query_id,
                        "object_id": record["object_id"],
                        "domain_id": record["domain_id"],
                        "relevance": 2 if rel_index < len(selected_domains) else 1,
                    }
                    bundle_qrels_object.append(qrels_row)
                    global_qrels_object.append(qrels_row)
                for domain_id in selected_domains:
                    qrels_domain_row = {
                        "query_id": query_id,
                        "domain_id": domain_id,
                        "is_relevant_domain": 1,
                    }
                    bundle_qrels_domain.append(qrels_domain_row)
                    global_qrels_domain.append(qrels_domain_row)
                start_time_ms += 100

        write_csv(_bundle_output(bundle, "queries_csv"), QUERY_FIELDS, bundle_queries)
        write_csv(_bundle_output(bundle, "qrels_object_csv"), ["query_id", "object_id", "domain_id", "relevance"], bundle_qrels_object)
        write_csv(_bundle_output(bundle, "qrels_domain_csv"), ["query_id", "domain_id", "is_relevant_domain"], bundle_qrels_domain)
        bundle_stats[bundle_id] = {
            "queries_total": len(bundle_queries),
            "test_counts": Counter(row["workload_tier"] for row in bundle_queries if row["split"] == "test"),
            "dev_counts": Counter(row["workload_tier"] for row in bundle_queries if row["split"] == "dev"),
            "mean_relevant_objects": round(len(bundle_qrels_object) / max(1, len(bundle_queries)), 3),
            "mean_relevant_domains": round(len(bundle_qrels_domain) / max(1, len(bundle_queries)), 3),
        }

    write_csv(output_path(manifest, "queries_csv"), QUERY_FIELDS, global_queries)
    write_csv(output_path(manifest, "qrels_object_csv"), ["query_id", "object_id", "domain_id", "relevance"], global_qrels_object)
    write_csv(output_path(manifest, "qrels_domain_csv"), ["query_id", "domain_id", "is_relevant_domain"], global_qrels_domain)
    stats = {
        "queries_total": len(global_queries),
        "bundle_stats": {
            bundle_id: {
                "queries_total": payload["queries_total"],
                "test_counts": dict(payload["test_counts"]),
                "dev_counts": dict(payload["dev_counts"]),
                "mean_relevant_objects": payload["mean_relevant_objects"],
                "mean_relevant_domains": payload["mean_relevant_domains"],
            }
            for bundle_id, payload in bundle_stats.items()
        },
    }
    _write_stats(output_path(manifest, "qrels_domain_csv").parent / "query_stats.json", stats)
    LOGGER.info("generated %s v2 queries", len(global_queries))
    return 0


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.config)
    rules = load_rule_config(manifest, "query_generation")
    topology_mapping_path = args.topology_mapping or output_path(manifest, "topology_mapping_csv")
    if manifest["dataset_id"] in {"smartcity_v3", "smartcity"}:
        return _generate_v3_queries(manifest, rules)
    if manifest["dataset_id"] == "smartcity_v2" or manifest.get("topology", {}).get("query_bundles"):
        return _generate_v2_queries(manifest, rules)
    return _run_legacy(manifest, topology_mapping_path, rules)


if __name__ == "__main__":
    raise SystemExit(main())
