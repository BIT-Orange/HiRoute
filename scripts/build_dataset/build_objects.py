"""Build deterministic smart-city objects from the service ontology."""

from __future__ import annotations

import argparse
import logging
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_dataset.build_confusers import (
    append_suffix,
    family_variant,
    humanize_token,
    pick_difficulty,
)
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

V3_EXTRA_FIELDS = [
    "semantic_intent_family",
    "semantic_intent_variant",
    "confuser_group_id",
    "difficulty_tag",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def canonical_name(template: str, record: dict[str, str]) -> str:
    return template.format(**record)


def _describe_text(
    ontology_row: dict[str, str],
    record: dict[str, object],
    profile_name: str,
    confuser_kind: str | None = None,
    anchor_family: str | None = None,
    anchor_variant: str | None = None,
) -> dict[str, object]:
    family = humanize_token(str(record.get("semantic_intent_family", record.get("semantic_facet", ""))))
    variant = humanize_token(str(record.get("semantic_intent_variant", family)))
    confuser_note = ""
    if confuser_kind == "semantic_near_miss":
        confuser_note = (
            "It is a semantic near miss that overlaps the target constraints but follows a different intent. "
            f"Operators frequently compare it against {humanize_token(anchor_family or '')}."
        )
    elif confuser_kind == "constraint_near_miss":
        confuser_note = (
            "It is a constraint near miss that keeps similar semantics while drifting on freshness or locality. "
            f"It is often reviewed beside {humanize_token(anchor_family or '')}."
        )
    elif confuser_kind == "naming_confuser":
        confuser_note = (
            "It is a naming confuser that keeps the same semantics under a different naming template. "
            f"Its semantic anchor remains {humanize_token(anchor_family or '')} {humanize_token(anchor_variant or '')}."
        )
    return {
        "object_text_id": record["object_text_id"],
        "object_id": record["object_id"],
        "description_text": (
            f"{ontology_row['source_subject']} publishes {record['service_class'].replace('_', ' ')} "
            f"for {record['zone_type'].replace('_', ' ')} in {record['domain_id']} with intent "
            f"{family} and variant {variant}. {confuser_note}".strip()
        ),
        "keywords": [
            record["service_class"],
            str(record.get("semantic_facet", "")),
            str(record.get("semantic_intent_family", "")),
            str(record.get("semantic_intent_variant", "")),
            record["zone_type"],
            record["domain_id"],
            record["freshness_class"],
            ontology_row["source_subject"],
        ],
        "metadata_summary": (
            f"{record['service_class']} object in {record['zone_id']}, profile={profile_name}, "
            f"intent={record.get('semantic_intent_family', '')}, variant={record.get('semantic_intent_variant', '')}, "
            f"freshness={record['freshness_class']}, property={ontology_row['primary_property']}."
        ),
    }


def _generate_legacy_objects(
    rules: dict[str, object],
    ontology_rows: list[dict[str, str]],
    rng: random.Random,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
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
    return objects, texts, FIELDS


def _generate_v3_objects(
    rules: dict[str, object],
    ontology_rows: list[dict[str, str]],
    rng: random.Random,
) -> tuple[list[dict[str, object]], list[dict[str, object]], list[str]]:
    payload_min = int(rules["payload_size_bytes"]["min"])
    payload_max = int(rules["payload_size_bytes"]["max"])
    templates = list(rules["naming_templates"])
    freshness_classes = list(rules["freshness_classes"].keys())
    time_buckets = list(rules["time_buckets"])
    domain_profiles = rules["domain_profiles"]
    profile_order = list(rules["domain_profile_order"])
    zone_types = list(rules["zone_types"])
    families_by_service = rules["semantic_intent_families"]
    confuser_policy = rules["confuser_policy"]
    difficulty_mixture = rules["difficulty_mixture"]
    variants_per_family = int(rules.get("variants_per_family", 3))

    ontology_by_service: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in ontology_rows:
        ontology_by_service[row["service_class"]].append(row)

    objects: list[dict[str, object]] = []
    texts: list[dict[str, object]] = []
    generation_index = 0

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
                target_count = round(base_count * domain_weight * local_weight)
                target_count = max(1, min(int(rules["max_objects_per_service_per_zone"]), target_count))
                families = families_by_service.get(service_class, [service_class])

                for object_index in range(target_count):
                    family = families[(domain_index + zone_index + object_index) % len(families)]
                    variant = family_variant(family, domain_index + zone_index + object_index, variants_per_family)
                    ontology_row = service_ontology_rows[(domain_index + zone_index + object_index) % len(service_ontology_rows)]
                    object_id = (
                        f"obj-{domain_index + 1:02d}-{zone_index + 1:02d}-"
                        f"{service_class}-{object_index + 1:02d}"
                    )
                    object_text_id = f"text-{object_id}"
                    template_index = (domain_index + zone_index + object_index) % len(templates)
                    template = templates[template_index]
                    difficulty_tag = pick_difficulty(generation_index, difficulty_mixture)
                    confuser_group_id = f"cg-{object_id}"
                    record = {
                        "object_id": object_id,
                        "domain_id": domain_id,
                        "zone_id": zone_id,
                        "zone_type": zone_type,
                        "service_class": service_class,
                        "semantic_facet": family,
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
                        "semantic_intent_family": family,
                        "semantic_intent_variant": variant,
                        "confuser_group_id": confuser_group_id,
                        "difficulty_tag": difficulty_tag,
                    }
                    record["canonical_name"] = canonical_name(template, record)
                    objects.append(record)
                    texts.append(_describe_text(ontology_row, record, profile_name))

                    semantic_miss_total = int(confuser_policy["semantic_near_miss_per_target"])
                    constraint_miss_total = int(confuser_policy["constraint_near_miss_per_target"])
                    naming_total = int(confuser_policy["naming_confuser_per_target"])

                    for confuser_index in range(semantic_miss_total):
                        miss_family = families[(domain_index + zone_index + object_index + confuser_index + 1) % len(families)]
                        confuser = dict(record)
                        confuser["object_id"] = append_suffix(object_id, "snm", confuser_index + 1)
                        confuser["object_text_id"] = f"text-{confuser['object_id']}"
                        confuser["semantic_facet"] = miss_family
                        confuser["semantic_intent_family"] = miss_family
                        confuser["semantic_intent_variant"] = family_variant(miss_family, confuser_index, variants_per_family)
                        confuser["vendor_template_id"] = f"tpl-{template_index + 1:02d}"
                        confuser["canonical_name"] = canonical_name(template, confuser)
                        objects.append(confuser)
                        texts.append(
                            _describe_text(
                                ontology_row,
                                confuser,
                                profile_name,
                                "semantic_near_miss",
                                family,
                                variant,
                            )
                        )

                    for confuser_index in range(constraint_miss_total):
                        confuser = dict(record)
                        confuser["object_id"] = append_suffix(object_id, "cnm", confuser_index + 1)
                        confuser["object_text_id"] = f"text-{confuser['object_id']}"
                        freshness_index = freshness_classes.index(record["freshness_class"])
                        confuser["freshness_class"] = freshness_classes[(freshness_index + confuser_index + 1) % len(freshness_classes)]
                        confuser["semantic_intent_variant"] = variant
                        confuser["canonical_name"] = canonical_name(template, confuser)
                        objects.append(confuser)
                        texts.append(
                            _describe_text(
                                ontology_row,
                                confuser,
                                profile_name,
                                "constraint_near_miss",
                                family,
                                variant,
                            )
                        )

                    for confuser_index in range(naming_total):
                        confuser = dict(record)
                        confuser["object_id"] = append_suffix(object_id, "ncf", confuser_index + 1)
                        confuser["object_text_id"] = f"text-{confuser['object_id']}"
                        alt_template_index = (template_index + confuser_index + 1) % len(templates)
                        alt_template = templates[alt_template_index]
                        confuser["vendor_template_id"] = f"tpl-{alt_template_index + 1:02d}"
                        confuser["semantic_intent_variant"] = variant
                        confuser["canonical_name"] = canonical_name(alt_template, confuser)
                        objects.append(confuser)
                        texts.append(
                            _describe_text(
                                ontology_row,
                                confuser,
                                profile_name,
                                "naming_confuser",
                                family,
                                variant,
                            )
                        )
                    generation_index += 1

    fieldnames = FIELDS + V3_EXTRA_FIELDS
    return objects, texts, fieldnames


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.config)
    rules = load_rule_config(manifest, "object_generation")
    ontology_rows = read_csv(output_path(manifest, "service_ontology_csv"))
    rng = random.Random(rules["seed"])

    if "semantic_intent_families" in rules:
        objects, texts, fieldnames = _generate_v3_objects(rules, ontology_rows, rng)
    else:
        objects, texts, fieldnames = _generate_legacy_objects(rules, ontology_rows, rng)

    if args.preview:
        preview_rows = objects[:5]
        for row in preview_rows:
            print(row)
        return 0

    write_csv(output_path(manifest, "objects_csv"), fieldnames, objects)
    write_jsonl(output_path(manifest, "object_texts_jsonl"), texts)
    if "semantic_intent_families" in rules:
        counts = Counter(
            (
                row["service_class"],
                row.get("semantic_intent_family", ""),
                row.get("difficulty_tag", ""),
            )
            for row in objects
        )
        for key, value in sorted(counts.items()):
            LOGGER.info(
                "service=%s family=%s difficulty=%s count=%s",
                key[0],
                key[1],
                key[2],
                value,
            )
    LOGGER.info("generated %s objects", len(objects))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
