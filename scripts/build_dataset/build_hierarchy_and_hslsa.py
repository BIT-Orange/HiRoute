"""Build the constrained HiRoute hierarchy and HS-LSA export."""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, load_rule_config, output_path
from tools.workflow_support import read_csv, write_csv


LOGGER = logging.getLogger("build_hierarchy_and_hslsa")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--hierarchy-config", type=Path)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _load_object_vectors(manifest: dict[str, object]) -> dict[str, np.ndarray]:
    embeddings = np.load(output_path(manifest, "object_embeddings_npy"))
    index_rows = read_csv(output_path(manifest, "object_embedding_index_csv"))
    return {
        row["object_id"]: embeddings[int(row["embedding_row"])]
        for row in index_rows
    }


def _balanced_clusters(vectors: np.ndarray, clusters_total: int, seed: int) -> np.ndarray:
    if clusters_total <= 1 or len(vectors) <= 1:
        return np.zeros(len(vectors), dtype=int)

    model = KMeans(n_clusters=clusters_total, random_state=seed, n_init="auto")
    labels = model.fit_predict(vectors)
    target_floor = len(vectors) // clusters_total
    target_ceil = target_floor + (1 if len(vectors) % clusters_total else 0)

    while True:
        counts = {cluster: int(np.sum(labels == cluster)) for cluster in range(clusters_total)}
        oversized = [cluster for cluster, count in counts.items() if count > target_ceil]
        undersized = [cluster for cluster, count in counts.items() if count < target_floor]
        if not oversized or not undersized:
            return labels

        changed = False
        for cluster in oversized:
            member_indices = np.where(labels == cluster)[0]
            centroid = model.cluster_centers_[cluster]
            distances = np.linalg.norm(vectors[member_indices] - centroid, axis=1)
            for member_index in member_indices[np.argsort(-distances)]:
                target_cluster = min(
                    undersized,
                    key=lambda candidate: np.linalg.norm(vectors[member_index] - model.cluster_centers_[candidate]),
                )
                labels[member_index] = target_cluster
                changed = True
                break
        if not changed:
            return labels


def _centroid_and_radius(vectors: np.ndarray) -> tuple[np.ndarray, float]:
    centroid = vectors.mean(axis=0).astype(np.float32)
    if len(vectors) == 1:
        return centroid, 0.0
    radius = float(np.max(np.linalg.norm(vectors - centroid, axis=1)))
    return centroid, radius


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    manifest = load_dataset_manifest(args.dataset_config)
    hierarchy = (
        load_rule_config(manifest, "hierarchy")
        if args.hierarchy_config is None
        else load_dataset_manifest(args.hierarchy_config)
    )
    objects = read_csv(output_path(manifest, "objects_csv"))
    vectors_by_object = _load_object_vectors(manifest)
    summary_embeddings: list[np.ndarray] = []
    summary_index_rows = []
    hslsa_rows = []
    controller_rows = []
    membership_rows = []
    version = f"{manifest['dataset_id']}::{hierarchy['hierarchy_id']}"
    export_budget = max(int(value) for value in hierarchy["export_budgets"])
    level1_partition_keys = list(hierarchy.get("level1_partition_keys", ["zone_id", "service_class"]))
    minimum_objects_per_microcluster = int(hierarchy.get("minimum_objects_per_microcluster", 2))

    domain_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    level1_groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    for row in objects:
        domain_groups[row["domain_id"]].append(row)
        level1_groups[(row["domain_id"], *(row[key] for key in level1_partition_keys))].append(row)

    def add_summary(level: int, domain_id: str, cell_id: str, parent_id: str, rows: list[dict[str, str]]) -> None:
        vectors = np.vstack([vectors_by_object[row["object_id"]] for row in rows])
        centroid, radius = _centroid_and_radius(vectors)
        centroid_row = len(summary_embeddings)
        summary_embeddings.append(centroid)
        summary_index_rows.append(
            {
                "centroid_row": centroid_row,
                "domain_id": domain_id,
                "level": level,
                "cell_id": cell_id,
            }
        )
        hslsa_rows.append(
            {
                "domain_id": domain_id,
                "level": level,
                "cell_id": cell_id,
                "parent_id": parent_id,
                "zone_bitmap": "|".join(sorted({row["zone_id"] for row in rows})),
                "zone_type_bitmap": "|".join(sorted({row["zone_type"] for row in rows})),
                "service_bitmap": "|".join(sorted({row["service_class"] for row in rows})),
                "freshness_bitmap": "|".join(sorted({row["freshness_class"] for row in rows})),
                "centroid_row": centroid_row,
                "radius": round(radius, 6),
                "object_count": len(rows),
                "controller_prefix": f"/hiroute/{domain_id}/controller",
                "version": version,
                "ttl_ms": hierarchy["ttl_ms"],
                "export_budget": export_budget,
            }
        )

    for domain_id, rows in sorted(domain_groups.items()):
        add_summary(0, domain_id, f"{domain_id}-root", "", rows)

    microclusters_total = int(hierarchy["semantic_microclusters_per_predicate_cell"])
    for level1_key, rows in sorted(level1_groups.items()):
        domain_id = level1_key[0]
        level1_cell = "-".join(level1_key)
        add_summary(1, domain_id, level1_cell, f"{domain_id}-root", rows)

        ordered_rows = sorted(rows, key=lambda row: row["object_id"])
        vectors = np.vstack([vectors_by_object[row["object_id"]] for row in ordered_rows])
        max_clusters_from_size = max(1, len(ordered_rows) // max(1, minimum_objects_per_microcluster))
        cluster_count = min(microclusters_total, max_clusters_from_size)
        labels = _balanced_clusters(vectors, cluster_count, int(hierarchy["seed"]))

        grouped_members: dict[int, list[dict[str, str]]] = defaultdict(list)
        for row, label in zip(ordered_rows, labels):
            grouped_members[int(label)].append(row)

        for cluster_index, cluster_rows in sorted(grouped_members.items()):
            cell_id = f"{level1_cell}-mc-{cluster_index + 1}"
            add_summary(2, domain_id, cell_id, level1_cell, cluster_rows)
            cluster_vectors = np.vstack([vectors_by_object[row["object_id"]] for row in cluster_rows])
            centroid, _ = _centroid_and_radius(cluster_vectors)
            ranked_rows = sorted(
                cluster_rows,
                key=lambda row: float(np.linalg.norm(vectors_by_object[row["object_id"]] - centroid)),
            )
            for rank_hint, row in enumerate(ranked_rows, start=1):
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

    np.save(output_path(manifest, "summary_embeddings_npy"), np.vstack(summary_embeddings).astype(np.float32))
    write_csv(output_path(manifest, "summary_embedding_index_csv"), ["centroid_row", "domain_id", "level", "cell_id"], summary_index_rows)
    write_csv(
        output_path(manifest, "hslsa_csv"),
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
    write_csv(output_path(manifest, "controller_local_index_csv"), ["domain_id", "cell_id", "object_id", "local_rank_hint"], controller_rows)
    write_csv(output_path(manifest, "cell_membership_csv"), ["object_id", "domain_id", "level0_cell", "level1_cell", "level2_cell"], membership_rows)
    LOGGER.info("generated %s HS-LSA summaries", len(hslsa_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
