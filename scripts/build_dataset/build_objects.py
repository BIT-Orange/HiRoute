"""Build deterministic synthetic smart-city objects for HiRoute."""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, repo_root, write_csv


FIELDS = [
    "object_id",
    "domain_id",
    "zone_id",
    "zone_type",
    "service_class",
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

SERVICE_METADATA = {
    "temperature": ("celsius", "float"),
    "humidity": ("percent", "float"),
    "rainfall": ("mm", "float"),
    "air_quality_pm25": ("ugm3", "float"),
    "air_quality_co2": ("ppm", "float"),
    "traffic_speed": ("kmh", "float"),
    "parking_availability": ("spots", "integer"),
    "bus_arrival": ("minutes", "integer"),
    "street_light_state": ("state", "enum"),
    "noise_level": ("db", "float"),
}


def canonical_name(template_id: int, domain_id: str, zone_id: str, service_class: str, object_id: str) -> str:
    if template_id == 0:
        return f"/{domain_id}/{zone_id}/{service_class}/{object_id}"
    if template_id == 1:
        return f"/city/{domain_id}/services/{service_class}/zones/{zone_id}/objects/{object_id}"
    if template_id == 2:
        return f"/org/{domain_id}/zone/{zone_id}/telemetry/{service_class}/{object_id}"
    return f"/iot/{service_class}/{domain_id}/{zone_id}/{object_id}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--preview", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json_yaml(ROOT / args.config)
    rng = random.Random(config["seed"])

    objects = []
    texts = []
    services = config["service_classes"]
    freshness = list(config["freshness_classes"])
    zone_types = config["zone_types"]

    for domain_index in range(config["domains_total"]):
        domain_id = f"domain-{domain_index + 1:02d}"
        controller_node_id = f"controller-{domain_id}"
        for zone_index in range(config["zones_per_domain"]):
            zone_id = f"{domain_id}-zone-{zone_index + 1:02d}"
            zone_type = zone_types[(domain_index + zone_index) % len(zone_types)]
            for service_index, service_class in enumerate(services):
                for object_index in range(config["objects_per_service_per_zone"]):
                    object_id = f"obj-{domain_index + 1:02d}-{zone_index + 1:02d}-{service_index + 1:02d}-{object_index + 1:02d}"
                    object_text_id = f"text-{object_id}"
                    freshness_class = freshness[(object_index + service_index) % len(freshness)]
                    template_id = (domain_index + object_index + service_index) % config["naming_templates_per_domain"]
                    producer_node_id = f"producer-{domain_id}-{zone_index + 1:02d}-{(object_index % 3) + 1}"
                    unit, value_type = SERVICE_METADATA[service_class]
                    record = {
                        "object_id": object_id,
                        "domain_id": domain_id,
                        "zone_id": zone_id,
                        "zone_type": zone_type,
                        "service_class": service_class,
                        "freshness_class": freshness_class,
                        "time_bucket": ["morning", "afternoon", "evening"][object_index % 3],
                        "vendor_template_id": f"tpl-{template_id + 1}",
                        "canonical_name": canonical_name(template_id, domain_id, zone_id, service_class, object_id),
                        "producer_node_id": producer_node_id,
                        "controller_node_id": controller_node_id,
                        "payload_size_bytes": 128 + 16 * ((service_index + object_index) % 6),
                        "unit": unit,
                        "value_type": value_type,
                        "object_version": 1,
                        "object_text_id": object_text_id,
                    }
                    objects.append(record)
                    texts.append(
                        {
                            "object_text_id": object_text_id,
                            "object_id": object_id,
                            "description_text": f"{service_class.replace('_', ' ')} sensor in {zone_type} for {domain_id}.",
                            "keywords": [service_class, zone_type, domain_id, freshness_class],
                            "metadata_summary": f"{service_class} in {zone_id} with {freshness_class} freshness.",
                        }
                    )

    if args.preview:
        print(json.dumps(objects[:5], indent=2))
        return 0

    ndnsim_dir = repo_root() / "data" / "processed" / "ndnsim"
    ndnsim_dir.mkdir(parents=True, exist_ok=True)
    write_csv(ndnsim_dir / "objects_master.csv", FIELDS, objects)
    with (ndnsim_dir / "object_texts.jsonl").open("w", encoding="utf-8") as handle:
        for row in texts:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
    print(f"generated {len(objects)} objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
