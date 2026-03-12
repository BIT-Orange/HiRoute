"""Generate query workloads and graded qrels for HiRoute."""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, load_rule_config, output_path, read_jsonl
from tools.workflow_support import read_csv, write_csv


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
    "query_text_id",
]

FAMILY_TO_LABEL = {
    "precise_template": ("low", "easy"),
    "paraphrase": ("medium", "medium"),
    "ambiguous": ("high", "hard"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--topology-mapping", type=Path)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _family_counts(total: int, ratios: dict[str, float]) -> list[str]:
    families = []
    for family, ratio in ratios.items():
        families.extend([family] * int(total * ratio))
    ordered = list(ratios)
    index = 0
    while len(families) < total:
        families.append(ordered[index % len(ordered)])
        index += 1
    return families[:total]


def _query_text(family: str, service_phrase: str, anchor: dict[str, str], drop_zone: bool, drop_freshness: bool) -> str:
    if family == "precise_template":
        return f"find {service_phrase} in {anchor['zone_id']} with {anchor['freshness_class']} freshness"
    if family == "paraphrase":
        if drop_zone:
            return f"need {service_phrase} updates around {anchor['zone_type']}"
        return f"need {service_phrase} readings near {anchor['zone_type']} in {anchor['domain_id']}"
    if drop_zone and drop_freshness:
        return f"show nearby {service_phrase} for busy areas"
    return f"show {service_phrase} updates in areas like {anchor['zone_type']}"


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.config)
    rules = load_rule_config(manifest, "query_generation")
    objects = read_csv(output_path(manifest, "objects_csv"))
    object_texts = {row["object_id"]: row for row in read_jsonl(output_path(manifest, "object_texts_jsonl"))}
    topology_mapping_path = args.topology_mapping or output_path(manifest, "topology_mapping_csv")
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

    families = _family_counts(int(rules["queries_total"]), rules["families"])
    rng.shuffle(families)

    queries = []
    qrels_object = []
    qrels_domain = []

    for index, family in enumerate(families):
        anchor = objects[index % len(objects)]
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
                "query_text": _query_text(family, service_phrase, anchor, drop_zone, drop_freshness),
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

    write_csv(output_path(manifest, "queries_csv"), QUERY_FIELDS, queries)
    write_csv(output_path(manifest, "qrels_object_csv"), ["query_id", "object_id", "relevance"], qrels_object)
    write_csv(output_path(manifest, "qrels_domain_csv"), ["query_id", "domain_id", "is_relevant_domain"], qrels_domain)

    stats = {
        "queries_total": len(queries),
        "family_distribution": {family: families.count(family) for family in sorted(set(families))},
        "mean_relevant_objects": round(len(qrels_object) / len(queries), 3),
        "mean_relevant_domains": round(len(qrels_domain) / len(queries), 3),
    }
    stats_path = output_path(manifest, "qrels_domain_csv").parent / "query_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("generated %s queries", len(queries))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
