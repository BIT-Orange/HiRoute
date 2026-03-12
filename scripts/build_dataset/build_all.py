"""Run the full formal smartcity_v1 dataset build pipeline."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.dataset_support import load_dataset_manifest, output_path
from tools.workflow_support import append_csv, load_json_yaml, repo_root


REGISTRY_FIELDS = [
    "dataset_id",
    "dataset_version",
    "built_at",
    "objects_csv",
    "queries_csv",
    "qrels_object_csv",
    "qrels_domain_csv",
    "object_embedding_index_csv",
    "query_embedding_index_csv",
    "summary_embedding_index_csv",
    "hslsa_csv",
    "controller_local_index_csv",
    "cell_membership_csv",
    "topology_mapping_csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    parser.add_argument("--topology-config", type=Path)
    return parser.parse_args()


def _run(script: str, args: list[str]) -> None:
    subprocess.run([sys.executable, script, *args], cwd=repo_root(), check=True)


def _replace_registry_row(registry_path: Path, row: dict[str, str]) -> None:
    existing = []
    if registry_path.exists():
        with registry_path.open("r", newline="", encoding="utf-8") as handle:
            existing = list(csv.DictReader(handle))
    existing = [item for item in existing if item["dataset_id"] != row["dataset_id"]]
    registry_path.write_text(",".join(REGISTRY_FIELDS) + "\n", encoding="utf-8")
    for item in existing + [row]:
        append_csv(registry_path, REGISTRY_FIELDS, item)


def main() -> int:
    args = parse_args()
    manifest = load_dataset_manifest(args.config)
    topology_config = load_json_yaml(
        ROOT / (args.topology_config or Path(manifest["topology"]["default_config"]))
    )

    _run("scripts/preprocess/extract_sdm_subjects.py", [])
    _run("scripts/preprocess/build_service_ontology.py", [])
    topology_config_arg = str(args.topology_config or manifest["topology"]["default_config"])
    _run("scripts/build_dataset/build_topology_mapping.py", ["--topology-config", topology_config_arg])
    _run("scripts/build_dataset/build_objects.py", ["--config", str(args.config)])
    _run(
        "scripts/build_dataset/build_queries_and_qrels.py",
        [
            "--config",
            str(args.config),
            "--topology-mapping",
            topology_config["mapping_output_path"],
        ],
    )
    _run(
        "scripts/build_dataset/embed_texts.py",
        ["--config", str(args.config), "--backend", "sentence-transformers"],
    )
    _run(
        "scripts/build_dataset/build_hierarchy_and_hslsa.py",
        ["--dataset-config", str(args.config), "--hierarchy-config", str(manifest["rules"]["hierarchy"])],
    )

    row = {
        "dataset_id": manifest["dataset_id"],
        "dataset_version": manifest["version"],
        "built_at": manifest["version"],
        "objects_csv": manifest["outputs"]["objects_csv"],
        "queries_csv": manifest["outputs"]["queries_csv"],
        "qrels_object_csv": manifest["outputs"]["qrels_object_csv"],
        "qrels_domain_csv": manifest["outputs"]["qrels_domain_csv"],
        "object_embedding_index_csv": manifest["outputs"]["object_embedding_index_csv"],
        "query_embedding_index_csv": manifest["outputs"]["query_embedding_index_csv"],
        "summary_embedding_index_csv": manifest["outputs"]["summary_embedding_index_csv"],
        "hslsa_csv": manifest["outputs"]["hslsa_csv"],
        "controller_local_index_csv": manifest["outputs"]["controller_local_index_csv"],
        "cell_membership_csv": manifest["outputs"]["cell_membership_csv"],
        "topology_mapping_csv": topology_config["mapping_output_path"],
    }
    _replace_registry_row(repo_root() / "data" / "registry" / "dataset_versions.csv", row)
    print(manifest["dataset_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
