"""Run the full smartcity_v1 dataset build pipeline."""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import append_csv, load_json_yaml, repo_root


REGISTRY_FIELDS = [
    "dataset_id",
    "dataset_version",
    "built_at",
    "objects_csv",
    "queries_csv",
    "qrels_object_csv",
    "qrels_domain_csv",
    "hslsa_csv",
    "topology_mapping_csv",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/datasets/smartcity_v1.yaml", type=Path)
    return parser.parse_args()


def _run(script: str, args: list[str]) -> None:
    command = ["python3", script, *args]
    subprocess.run(command, cwd=repo_root(), check=True)


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
    config = load_json_yaml(ROOT / args.config)
    _run("scripts/build_dataset/build_objects.py", ["--config", str(args.config)])
    _run("scripts/build_dataset/build_queries_and_qrels.py", ["--config", str(args.config)])
    _run(
        "scripts/build_dataset/build_hierarchy_and_hslsa.py",
        ["--dataset-config", str(args.config), "--hierarchy-config", "configs/hierarchy/hiroute_hkm_v1.yaml"],
    )
    _run("scripts/build_dataset/build_topology_mapping.py", ["--config", str(args.config)])

    row = {
        "dataset_id": config["dataset_id"],
        "dataset_version": config["version"],
        "built_at": config["version"],
        "objects_csv": "data/processed/ndnsim/objects_master.csv",
        "queries_csv": "data/processed/ndnsim/queries_master.csv",
        "qrels_object_csv": "data/processed/eval/qrels_object.csv",
        "qrels_domain_csv": "data/processed/eval/qrels_domain.csv",
        "hslsa_csv": "data/processed/ndnsim/hslsa_export.csv",
        "topology_mapping_csv": "data/processed/ndnsim/topology_mapping.csv",
    }
    _replace_registry_row(repo_root() / "data" / "registry" / "dataset_versions.csv", row)
    print(config["dataset_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
