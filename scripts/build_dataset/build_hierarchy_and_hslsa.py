"""Build deterministic hierarchy and HS-LSA exports for HiRoute."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--hierarchy-config", default="configs/hierarchy/hiroute_hkm_v1.yaml", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_config = load_json_yaml(ROOT / args.dataset_config)
    hierarchy_config = load_json_yaml(ROOT / args.hierarchy_config)
    objects = read_csv(repo_root() / "data" / "processed" / "ndnsim" / "objects_master.csv")

    hslsa_rows = []
    controller_rows = []
    membership_rows = []
    centroid_row = 0
    version = f"{dataset_config['dataset_id']}::{hierarchy_config['hierarchy_id']}"

    domain_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    level1_groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in objects:
        domain_groups[row["domain_id"]].append(row)
        level1_groups[(row["domain_id"], row["zone_id"], row["service_class"], row["freshness_class"])].append(row)

    for domain_id, rows in sorted(domain_groups.items()):
        hslsa_rows.append(
            {
                "domain_id": domain_id,
                "level": 0,
                "cell_id": f"{domain_id}-root",
                "parent_id": "",
                "zone_bitmap": "|".join(sorted({row["zone_id"] for row in rows})),
                "zone_type_bitmap": "|".join(sorted({row["zone_type"] for row in rows})),
                "service_bitmap": "|".join(sorted({row["service_class"] for row in rows})),
                "freshness_bitmap": "|".join(sorted({row["freshness_class"] for row in rows})),
                "centroid_row": centroid_row,
                "radius": 1.0,
                "object_count": len(rows),
                "controller_prefix": f"/{domain_id}/controller",
                "version": version,
                "ttl_ms": hierarchy_config["ttl_ms"],
                "export_budget": max(hierarchy_config["export_budgets"]),
            }
        )
        centroid_row += 1

    for (domain_id, zone_id, service_class, freshness_class), rows in sorted(level1_groups.items()):
        level1_cell = f"{domain_id}-{zone_id}-{service_class}-{freshness_class}"
        hslsa_rows.append(
            {
                "domain_id": domain_id,
                "level": 1,
                "cell_id": level1_cell,
                "parent_id": f"{domain_id}-root",
                "zone_bitmap": zone_id,
                "zone_type_bitmap": rows[0]["zone_type"],
                "service_bitmap": service_class,
                "freshness_bitmap": freshness_class,
                "centroid_row": centroid_row,
                "radius": 0.45,
                "object_count": len(rows),
                "controller_prefix": f"/{domain_id}/controller",
                "version": version,
                "ttl_ms": hierarchy_config["ttl_ms"],
                "export_budget": max(hierarchy_config["export_budgets"]),
            }
        )
        centroid_row += 1

        microcluster_count = min(hierarchy_config["semantic_microclusters_per_predicate_cell"], max(1, len(rows)))
        for cluster_index in range(microcluster_count):
            cluster_rows = rows[cluster_index::microcluster_count]
            cell_id = f"{level1_cell}-mc-{cluster_index + 1}"
            hslsa_rows.append(
                {
                    "domain_id": domain_id,
                    "level": 2,
                    "cell_id": cell_id,
                    "parent_id": level1_cell,
                    "zone_bitmap": zone_id,
                    "zone_type_bitmap": rows[0]["zone_type"],
                    "service_bitmap": service_class,
                    "freshness_bitmap": freshness_class,
                    "centroid_row": centroid_row,
                    "radius": 0.18 + cluster_index * 0.03,
                    "object_count": len(cluster_rows),
                    "controller_prefix": f"/{domain_id}/controller",
                    "version": version,
                    "ttl_ms": hierarchy_config["ttl_ms"],
                    "export_budget": max(hierarchy_config["export_budgets"]),
                }
            )
            centroid_row += 1

            for rank_hint, row in enumerate(cluster_rows, start=1):
                controller_rows.append(
                    {
                        "domain_id": domain_id,
                        "cell_id": cell_id,
                        "object_id": row["object_id"],
                        "local_rank_hint": rank_hint,
                    }
                )
                membership_rows.append(
                    {
                        "object_id": row["object_id"],
                        "domain_id": domain_id,
                        "level0_cell": f"{domain_id}-root",
                        "level1_cell": level1_cell,
                        "level2_cell": cell_id,
                    }
                )

    ndnsim_dir = repo_root() / "data" / "processed" / "ndnsim"
    write_csv(
        ndnsim_dir / "hslsa_export.csv",
        [
            "domain_id",
            "level",
            "cell_id",
            "parent_id",
            "zone_bitmap",
            "zone_type_bitmap",
            "service_bitmap",
            "freshness_bitmap",
            "centroid_row",
            "radius",
            "object_count",
            "controller_prefix",
            "version",
            "ttl_ms",
            "export_budget",
        ],
        hslsa_rows,
    )
    write_csv(
        ndnsim_dir / "controller_local_index.csv",
        ["domain_id", "cell_id", "object_id", "local_rank_hint"],
        controller_rows,
    )
    write_csv(
        ndnsim_dir / "cell_membership.csv",
        ["object_id", "domain_id", "level0_cell", "level1_cell", "level2_cell"],
        membership_rows,
    )
    print(f"generated {len(hslsa_rows)} HS-LSA rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
