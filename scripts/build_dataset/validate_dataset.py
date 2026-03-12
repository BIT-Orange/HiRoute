"""Validate the generated smartcity_v1 dataset artifacts."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import repo_root


REQUIRED = {
    "data/processed/ndnsim/objects_master.csv": [
        "object_id",
        "domain_id",
        "zone_id",
        "service_class",
        "canonical_name",
    ],
    "data/processed/ndnsim/queries_master.csv": [
        "query_id",
        "query_text",
        "service_constraint",
        "ambiguity_level",
    ],
    "data/processed/eval/qrels_object.csv": [
        "query_id",
        "object_id",
        "relevance",
    ],
    "data/processed/eval/qrels_domain.csv": [
        "query_id",
        "domain_id",
        "is_relevant_domain",
    ],
    "data/processed/ndnsim/hslsa_export.csv": [
        "domain_id",
        "level",
        "cell_id",
        "controller_prefix",
    ],
    "data/processed/ndnsim/topology_mapping.csv": [
        "node_id",
        "role",
        "domain_id",
        "controller_prefix",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo_root())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for relative_path, columns in REQUIRED.items():
        path = args.root / relative_path
        if not path.exists():
            print(f"ERROR: missing {relative_path}")
            return 1
        with path.open("r", newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            missing = [column for column in columns if column not in (reader.fieldnames or [])]
            if missing:
                print(f"ERROR: {relative_path} is missing columns: {', '.join(missing)}")
                return 1
            first_row = next(reader, None)
            if first_row is None:
                print(f"ERROR: {relative_path} has no data rows")
                return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
