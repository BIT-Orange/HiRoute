"""Build synthetic queries and object/domain qrels for HiRoute."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    return parser.parse_args()


def build_query_text(family: str, record: dict[str, str]) -> tuple[str, str, str]:
    service = record["service_class"].replace("_", " ")
    if family == "template":
        return (
            f"find {service} in {record['zone_id']} with {record['freshness_class']} freshness",
            "low",
            "easy",
        )
    if family == "paraphrase":
        return (
            f"need {service} readings around {record['zone_type']} in {record['domain_id']}",
            "medium",
            "medium",
        )
    return (
        f"show nearby {service} updates for busy areas",
        "high",
        "hard",
    )


def main() -> int:
    args = parse_args()
    config = load_json_yaml(ROOT / args.config)
    objects = read_csv(repo_root() / "data" / "processed" / "ndnsim" / "objects_master.csv")
    rng = random.Random(config["query_generation"]["seed"])
    families = (
        ["template"] * int(config["query_generation"]["queries_total"] * config["query_generation"]["template_ratio"])
        + ["paraphrase"] * int(config["query_generation"]["queries_total"] * config["query_generation"]["paraphrase_ratio"])
    )
    while len(families) < config["query_generation"]["queries_total"]:
        families.append("ambiguous")
    rng.shuffle(families)

    by_service: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for obj in objects:
        by_service[obj["service_class"]].append(obj)
        by_domain[obj["domain_id"]].append(obj)

    queries = []
    qrels_object = []
    qrels_domain = []

    for index, family in enumerate(families):
        anchor = objects[index % len(objects)]
        query_id = f"q-{index + 1:04d}"
        query_text_id = f"qt-{query_id}"
        query_text, ambiguity_level, difficulty = build_query_text(family, anchor)
        split = "dev" if index < int(config["query_generation"]["queries_total"] * config["query_generation"]["splits"]["dev"]) else "test"
        ingress_node_id = f"ingress-{(index % config['topology']['ingress_nodes']) + 1}"

        relevant = [row for row in by_service[anchor["service_class"]] if row["zone_type"] == anchor["zone_type"]]
        if family == "template":
            relevant = [row for row in relevant if row["domain_id"] == anchor["domain_id"] and row["zone_id"] == anchor["zone_id"]]
        elif family == "paraphrase":
            relevant = relevant[: max(3, min(6, len(relevant)))]
        else:
            other_domains = [row for row in by_service[anchor["service_class"]] if row["domain_id"] != anchor["domain_id"]]
            relevant = (relevant[:3] + other_domains[:4])[:7]

        domain_ids = sorted({row["domain_id"] for row in relevant})
        queries.append(
            {
                "query_id": query_id,
                "split": split,
                "ingress_node_id": ingress_node_id,
                "start_time_ms": index * 100,
                "query_text": query_text,
                "zone_constraint": anchor["zone_id"] if family == "template" else "",
                "zone_type_constraint": anchor["zone_type"],
                "service_constraint": anchor["service_class"],
                "freshness_constraint": anchor["freshness_class"] if family != "ambiguous" else "",
                "ambiguity_level": ambiguity_level,
                "difficulty": difficulty,
                "intended_domain_count": len(domain_ids),
                "query_text_id": query_text_id,
            }
        )

        for rel_index, record in enumerate(relevant):
            qrels_object.append(
                {
                    "query_id": query_id,
                    "object_id": record["object_id"],
                    "relevance": 2 if rel_index == 0 else 1,
                }
            )
        for domain_id in domain_ids:
            qrels_domain.append(
                {
                    "query_id": query_id,
                    "domain_id": domain_id,
                    "is_relevant_domain": 1,
                }
            )

    ndnsim_dir = repo_root() / "data" / "processed" / "ndnsim"
    eval_dir = repo_root() / "data" / "processed" / "eval"
    ndnsim_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    write_csv(ndnsim_dir / "queries_master.csv", QUERY_FIELDS, queries)
    write_csv(eval_dir / "qrels_object.csv", ["query_id", "object_id", "relevance"], qrels_object)
    write_csv(eval_dir / "qrels_domain.csv", ["query_id", "domain_id", "is_relevant_domain"], qrels_domain)
    stats = {
        "queries_total": len(queries),
        "template": families.count("template"),
        "paraphrase": families.count("paraphrase"),
        "ambiguous": families.count("ambiguous"),
    }
    (eval_dir / "query_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
