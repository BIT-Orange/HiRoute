"""Build deterministic topology-to-domain mappings for HiRoute."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_json_yaml(ROOT / args.config)
    objects = read_csv(repo_root() / "data" / "processed" / "ndnsim" / "objects_master.csv")
    counts = Counter(row["domain_id"] for row in objects)
    zones_by_domain: dict[str, list[str]] = {}
    for row in objects:
        zones_by_domain.setdefault(row["domain_id"], [])
        if row["zone_id"] not in zones_by_domain[row["domain_id"]]:
            zones_by_domain[row["domain_id"]].append(row["zone_id"])

    rows = []
    node_id = 1
    for domain_id in sorted(counts):
        zones = zones_by_domain[domain_id]
        rows.append(
            {
                "node_id": f"node-{node_id:03d}",
                "role": "controller",
                "domain_id": domain_id,
                "zone_id": zones[0],
                "controller_prefix": f"/{domain_id}/controller",
                "producer_count": 0,
            }
        )
        node_id += 1

        for producer_index in range(3):
            rows.append(
                {
                    "node_id": f"node-{node_id:03d}",
                    "role": "producer",
                    "domain_id": domain_id,
                    "zone_id": zones[producer_index % len(zones)],
                    "controller_prefix": f"/{domain_id}/controller",
                    "producer_count": max(1, counts[domain_id] // 3),
                }
            )
            node_id += 1

        for relay_index in range(config["topology"]["relays_per_domain"]):
            rows.append(
                {
                    "node_id": f"node-{node_id:03d}",
                    "role": "relay",
                    "domain_id": domain_id,
                    "zone_id": zones[relay_index % len(zones)],
                    "controller_prefix": f"/{domain_id}/controller",
                    "producer_count": 0,
                }
            )
            node_id += 1

    for ingress_index in range(config["topology"]["ingress_nodes"]):
        domain_id = sorted(counts)[ingress_index % len(counts)]
        zone_id = zones_by_domain[domain_id][ingress_index % len(zones_by_domain[domain_id])]
        rows.append(
            {
                "node_id": f"node-{node_id:03d}",
                "role": "ingress",
                "domain_id": domain_id,
                "zone_id": zone_id,
                "controller_prefix": f"/{domain_id}/controller",
                "producer_count": 0,
            }
        )
        node_id += 1

    ndnsim_dir = repo_root() / "data" / "processed" / "ndnsim"
    write_csv(
        ndnsim_dir / "topology_mapping.csv",
        ["node_id", "role", "domain_id", "zone_id", "controller_prefix", "producer_count"],
        rows,
    )
    print(f"generated {len(rows)} topology rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
