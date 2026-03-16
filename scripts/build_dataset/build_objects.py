"""Build deterministic smart-city objects from the service ontology."""

from __future__ import annotations

import argparse
import logging
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, load_rule_config, output_path, write_jsonl
from tools.workflow_support import read_csv, write_csv


LOGGER = logging.getLogger("build_objects")
FIELDS = [
    "object_id",
    "domain_id",
    "zone_id",
    "zone_type",
    "service_class",
    "semantic_facet",
    "freshness_class",
    "time_bucket",
    "vendor_template_id",
    "canonical_name",
    "producer_node_id",
    "controller_node_id",
    "payload_size_bytes",
    "unit",
    "value_type",
    "object_version",
    "object_text_id",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def canonical_name(template: str, record: dict[str, str]) -> str:
    return template.format(**record)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.config)
    rules = load_rule_config(manifest, "object_generation")
    ontology_rows = read_csv(output_path(manifest, "service_ontology_csv"))
    rng = random.Random(rules["seed"])

    payload_min = int(rules["payload_size_bytes"]["min"])
    payload_max = int(rules["payload_size_bytes"]["max"])
    templates = list(rules["naming_templates"])
    freshness_classes = list(rules["freshness_classes"].keys())
    time_buckets = list(rules["time_buckets"])
    semantic_facets = rules.get("semantic_facets", {})
    domain_profiles = rules["domain_profiles"]
    profile_order = list(rules["domain_profile_order"])
    zone_types = list(rules["zone_types"])
    ontology_by_service: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ontology_rows:
        ontology_by_service[row["service_class"]].append(row)

    objects: list[dict[str, object]] = []
    texts: list[dict[str, object]] = []

    for domain_index in range(int(rules["domains_total"])):
        domain_id = f"domain-{domain_index + 1:02d}"
        controller_node_id = f"controller-slot-{domain_id}"
        profile_name = profile_order[domain_index % len(profile_order)]
        service_weights = domain_profiles[profile_name]["service_weights"]

        for zone_index in range(int(rules["zones_per_domain"])):
            zone_id = f"{domain_id}-zone-{zone_index + 1:02d}"
            zone_type = zone_types[(domain_index + zone_index) % len(zone_types)]
            zone_bias = rules["zone_type_service_bias"].get(zone_type, {})

            for service_class, service_ontology_rows in sorted(ontology_by_service.items()):
                domain_weight = float(service_weights.get(service_class, 1.0))
                local_weight = float(zone_bias.get(service_class, 1.0))
                base_count = int(rules["base_objects_per_service_per_zone"])
                object_count = round(base_count * domain_weight * local_weight)
                object_count = max(1, min(int(rules["max_objects_per_service_per_zone"]), object_count))

                for object_index in range(object_count):
                    ontology_row = service_ontology_rows[(domain_index + zone_index + object_index) % len(service_ontology_rows)]
                    object_id = (
                        f"obj-{domain_index + 1:02d}-{zone_index + 1:02d}-"
                        f"{service_class}-{object_index + 1:02d}"
                    )
                    object_text_id = f"text-{object_id}"
                    template_index = (domain_index + zone_index + object_index) % len(templates)
                    template = templates[template_index]
                    facet_choices = semantic_facets.get(service_class, [service_class])
                    semantic_facet = facet_choices[(domain_index + zone_index + object_index) % len(facet_choices)]
                    record = {
                        "object_id": object_id,
                        "domain_id": domain_id,
                        "zone_id": zone_id,
                        "zone_type": zone_type,
                        "service_class": service_class,
                        "semantic_facet": semantic_facet,
                        "freshness_class": freshness_classes[(zone_index + object_index) % len(freshness_classes)],
                        "time_bucket": time_buckets[(object_index + zone_index) % len(time_buckets)],
                        "vendor_template_id": f"tpl-{template_index + 1:02d}",
                        "producer_node_id": f"producer-slot-{domain_id}-{zone_index + 1:02d}-{(object_index % 3) + 1}",
                        "controller_node_id": controller_node_id,
                        "payload_size_bytes": rng.randint(payload_min, payload_max),
                        "unit": ontology_row["unit"],
                        "value_type": ontology_row["value_type"],
                        "object_version": 1,
                        "object_text_id": object_text_id,
                    }
                    record["canonical_name"] = canonical_name(template, record)
                    objects.append(record)
                    texts.append(
                        {
                            "object_text_id": object_text_id,
                            "object_id": object_id,
                            "description_text": (
                                f"{ontology_row['source_subject']} publishes {service_class.replace('_', ' ')} "
                                f"for {zone_type} in {domain_id} during the {record['time_bucket']} "
                                f"with emphasis on {semantic_facet.replace('_', ' ')}."
                            ),
                            "keywords": [
                                service_class,
                                semantic_facet,
                                zone_type,
                                domain_id,
                                record["freshness_class"],
                                ontology_row["source_subject"],
                            ],
                            "metadata_summary": (
                                f"{service_class} object in {zone_id}, profile={profile_name}, "
                                f"facet={semantic_facet}, freshness={record['freshness_class']}, "
                                f"property={ontology_row['primary_property']}."
                            ),
                        }
                    )

    if args.preview:
        preview_rows = objects[:5]
        for row in preview_rows:
            print(row)
        return 0

    write_csv(output_path(manifest, "objects_csv"), FIELDS, objects)
    write_jsonl(output_path(manifest, "object_texts_jsonl"), texts)
    LOGGER.info("generated %s objects", len(objects))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
