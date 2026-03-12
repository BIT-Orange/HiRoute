"""Build an editable service ontology from Smart Data Models subject metadata."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


LOGGER = logging.getLogger("build_service_ontology")
FIELDS = [
    "service_class",
    "source_subject",
    "entity_type",
    "primary_property",
    "unit",
    "value_type",
    "template_group",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/interim/objects/sdm_subject_catalog.csv"),
    )
    parser.add_argument(
        "--rules",
        type=Path,
        default=Path("configs/datasets/service_ontology_rules.yaml"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/objects/service_ontology.csv"),
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _matches(rule: dict[str, object], row: dict[str, str]) -> bool:
    haystack = " ".join(
        [
            row["subject_name"],
            row["entity_type"],
            row["schema_path"],
            row.get("example_path", ""),
            row["domain_group"],
        ]
    ).lower()
    return any(keyword.lower() in haystack for keyword in rule["match_any"])


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    rules = load_json_yaml(repo_root() / args.rules)["service_classes"]
    catalog = read_csv(repo_root() / args.catalog)

    rows: list[dict[str, str]] = []
    seen = set()
    for service_class, rule in rules.items():
        matches = [row for row in catalog if _matches(rule, row)]
        if not matches:
            raise ValueError(f"service class '{service_class}' has no Smart Data Models match")
        for match in matches:
            key = (service_class, match["subject_name"], match["entity_type"])
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "service_class": service_class,
                    "source_subject": match["subject_name"],
                    "entity_type": match["entity_type"],
                    "primary_property": str(rule["primary_property"]),
                    "unit": str(rule["unit"]),
                    "value_type": str(rule["value_type"]),
                    "template_group": str(rule["template_group"]),
                }
            )

    output_path = repo_root() / args.output
    write_csv(output_path, FIELDS, rows)
    LOGGER.info("wrote %s ontology rows to %s", len(rows), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
