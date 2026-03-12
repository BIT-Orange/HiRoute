"""Validate the formal smartcity_v1 dataset artifacts."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, output_path
from tools.workflow_support import load_json_yaml, repo_root


REQUIRED_COLUMNS = {
    "objects_csv": ["object_id", "domain_id", "zone_id", "service_class", "canonical_name"],
    "queries_csv": ["query_id", "query_text", "service_constraint", "ambiguity_level"],
    "qrels_object_csv": ["query_id", "object_id", "relevance"],
    "qrels_domain_csv": ["query_id", "domain_id", "is_relevant_domain"],
    "object_embedding_index_csv": ["object_id", "object_text_id", "embedding_row"],
    "query_embedding_index_csv": ["query_id", "query_text_id", "embedding_row"],
    "summary_embedding_index_csv": ["centroid_row", "domain_id", "level", "cell_id"],
    "hslsa_csv": ["domain_id", "level", "cell_id", "controller_prefix", "centroid_row"],
    "controller_local_index_csv": ["domain_id", "cell_id", "object_id", "local_rank_hint"],
    "cell_membership_csv": ["object_id", "domain_id", "level0_cell", "level1_cell", "level2_cell"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/datasets/smartcity_v1.yaml"))
    parser.add_argument("--topology-config", type=Path, default=Path("configs/topologies/rocketfuel_3967_exodus.yaml"))
    return parser.parse_args()


def _validate_csv(path: Path, columns: list[str]) -> None:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in columns if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{path} missing columns: {', '.join(missing)}")
        if next(reader, None) is None:
            raise ValueError(f"{path} has no data rows")


def main() -> int:
    args = parse_args()
    manifest = load_dataset_manifest(args.config)
    topology = load_json_yaml(repo_root() / args.topology_config)

    for key, columns in REQUIRED_COLUMNS.items():
        _validate_csv(output_path(manifest, key), columns)
    _validate_csv(repo_root() / topology["mapping_output_path"], ["node_id", "role", "domain_id", "controller_prefix"])

    object_embeddings = np.load(output_path(manifest, "object_embeddings_npy"))
    query_embeddings = np.load(output_path(manifest, "query_embeddings_npy"))
    summary_embeddings = np.load(output_path(manifest, "summary_embeddings_npy"))

    if len(object_embeddings) != len(list(csv.DictReader(output_path(manifest, "object_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("object embedding index count mismatch")
    if len(query_embeddings) != len(list(csv.DictReader(output_path(manifest, "query_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("query embedding index count mismatch")
    if len(summary_embeddings) != len(list(csv.DictReader(output_path(manifest, "summary_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("summary embedding index count mismatch")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
