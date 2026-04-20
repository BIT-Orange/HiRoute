"""Validate the formal dataset artifacts."""

from __future__ import annotations

import argparse
import csv
import subprocess
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
    "object_embeddings_csv": ["object_id", "object_text_id", "embedding_row", "embedding_vector"],
    "query_embeddings_csv": ["query_id", "query_text_id", "embedding_row", "embedding_vector"],
    "object_embedding_index_csv": ["object_id", "object_text_id", "embedding_row"],
    "query_embedding_index_csv": ["query_id", "query_text_id", "embedding_row"],
    "summary_embeddings_csv": ["centroid_row", "domain_id", "level", "cell_id", "embedding_vector"],
    "summary_embedding_index_csv": ["centroid_row", "domain_id", "level", "cell_id"],
    "hslsa_csv": ["domain_id", "level", "cell_id", "controller_prefix", "centroid_row"],
    "controller_local_index_csv": ["domain_id", "cell_id", "object_id", "local_rank_hint"],
    "cell_membership_csv": ["object_id", "domain_id", "level0_cell", "level1_cell", "level2_cell"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/datasets/smartcity_v2.yaml"))
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


def _validate_controller_local_index(path: Path) -> None:
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [
            column for column in REQUIRED_COLUMNS["controller_local_index_csv"] if column not in fieldnames
        ]
        if missing:
            raise ValueError(f"{path} missing columns: {', '.join(missing)}")
        rows = list(reader)
        if not rows:
            raise ValueError(f"{path} has no data rows")
        if "ancestor_frontier_ids" not in fieldnames:
            return
        for index, row in enumerate(rows, start=2):
            value = row.get("ancestor_frontier_ids", "")
            if not value:
                raise ValueError(f"{path}:{index} has empty ancestor_frontier_ids")
            tokens = [token for token in value.split(";") if token]
            if not tokens:
                raise ValueError(f"{path}:{index} has invalid ancestor_frontier_ids")
            if tokens[-1] != row.get("cell_id", ""):
                raise ValueError(
                    f"{path}:{index} ancestor_frontier_ids must end with the concrete cell_id"
                )
            if len(tokens) != len(set(tokens)):
                raise ValueError(f"{path}:{index} ancestor_frontier_ids contains duplicates")


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else repo_root() / path


def main() -> int:
    args = parse_args()
    manifest = load_dataset_manifest(args.config)
    topology = load_json_yaml(repo_root() / args.topology_config)

    for key, columns in REQUIRED_COLUMNS.items():
        if key == "controller_local_index_csv":
            _validate_controller_local_index(output_path(manifest, key))
            continue
        _validate_csv(output_path(manifest, key), columns)
    if manifest["dataset_id"] == "smartcity_v2":
        _validate_csv(
            output_path(manifest, "objects_csv"),
            ["semantic_facet"],
        )
        _validate_csv(
            output_path(manifest, "queries_csv"),
            ["query_family", "workload_tier", "intent_facet", "ground_truth_count"],
        )
        _validate_csv(output_path(manifest, "qrels_object_csv"), ["domain_id"])
        _validate_csv(output_path(manifest, "hslsa_csv"), ["semantic_tag_bitmap"])
    if manifest["dataset_id"] in {"smartcity_v3", "smartcity"}:
        _validate_csv(
            output_path(manifest, "objects_csv"),
            [
                "semantic_facet",
                "semantic_intent_family",
                "semantic_intent_variant",
                "confuser_group_id",
                "difficulty_tag",
            ],
        )
        _validate_csv(
            output_path(manifest, "queries_csv"),
            [
                "query_family",
                "workload_tier",
                "intent_facet",
                "ground_truth_count",
                "manifest_difficulty",
                "target_relevant_domains",
                "target_confuser_domains",
                "explicit_domain_mention",
                "explicit_zone_mention",
                "semantic_intent_family",
            ],
        )
        _validate_csv(output_path(manifest, "qrels_object_csv"), ["domain_id"])
        _validate_csv(
            output_path(manifest, "qrels_domain_csv"),
            ["relevance_strength", "dominant_intent_match"],
        )
        _validate_csv(output_path(manifest, "hslsa_csv"), ["semantic_tag_bitmap"])
    _validate_csv(repo_root() / topology["mapping_output_path"], ["node_id", "role", "domain_id", "controller_prefix"])

    object_embeddings = np.load(output_path(manifest, "object_embeddings_npy"))
    query_embeddings = np.load(output_path(manifest, "query_embeddings_npy"))
    summary_embeddings = np.load(output_path(manifest, "summary_embeddings_npy"))

    if len(object_embeddings) != len(list(csv.DictReader(output_path(manifest, "object_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("object embedding index count mismatch")
    if len(object_embeddings) != len(list(csv.DictReader(output_path(manifest, "object_embeddings_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("object embedding csv count mismatch")
    if len(query_embeddings) != len(list(csv.DictReader(output_path(manifest, "query_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("query embedding index count mismatch")
    if len(query_embeddings) != len(list(csv.DictReader(output_path(manifest, "query_embeddings_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("query embedding csv count mismatch")
    if len(summary_embeddings) != len(list(csv.DictReader(output_path(manifest, "summary_embedding_index_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("summary embedding index count mismatch")
    if len(summary_embeddings) != len(list(csv.DictReader(output_path(manifest, "summary_embeddings_csv").open("r", newline="", encoding="utf-8")))):
        raise ValueError("summary embedding csv count mismatch")

    for bundle_id, bundle in manifest.get("topology", {}).get("query_bundles", {}).items():
        _validate_csv(_resolve(bundle["queries_csv"]), ["query_id", "split", "workload_tier", "intent_facet"])
        _validate_csv(_resolve(bundle["qrels_object_csv"]), ["query_id", "object_id", "domain_id", "relevance"])
        qrels_domain_fields = ["query_id", "domain_id", "is_relevant_domain"]
        if manifest["dataset_id"] in {"smartcity_v3", "smartcity"}:
            qrels_domain_fields.extend(["relevance_strength", "dominant_intent_match"])
        _validate_csv(_resolve(bundle["qrels_domain_csv"]), qrels_domain_fields)
        _validate_csv(_resolve(bundle["query_embedding_index_csv"]), ["query_id", "query_text_id", "embedding_row"])

    audit_result = subprocess.run(
        [sys.executable, "scripts/build_dataset/audit_query_workloads.py", "--config", str(args.config)],
        cwd=repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if audit_result.returncode != 0:
        raise ValueError(audit_result.stdout or audit_result.stderr)

    if manifest["dataset_id"] in {"smartcity_v3", "smartcity"}:
        audit_filename = "workload_audit_mainline.json" if manifest["dataset_id"] == "smartcity" else "workload_audit_v3.json"
        audit_path = repo_root() / "data" / "processed" / "eval" / audit_filename
        if not audit_path.exists():
            raise ValueError(f"{audit_filename} was not generated")

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
