"""Extract Smart Data Models subjects relevant to the HiRoute dataset pipeline."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import repo_root


LOGGER = logging.getLogger("extract_sdm_subjects")
RELEVANT_KEYWORDS = {
    "air",
    "arrival",
    "bus",
    "environment",
    "light",
    "mobility",
    "noise",
    "parking",
    "road",
    "street",
    "traffic",
    "transport",
    "weather",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("data/raw/smartdatamodels"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/interim/objects/sdm_subject_catalog.csv"),
    )
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def _looks_relevant(repo_name: str, schema_path: Path, repo_root_path: Path) -> bool:
    if repo_name == "SmartCities":
        return True
    relative = schema_path.parent.relative_to(repo_root_path).as_posix().lower()
    return any(keyword in relative for keyword in RELEVANT_KEYWORDS)


def _find_example(subject_root: Path) -> Path | None:
    example_candidates = []
    for pattern in ("example*.json", "examples/*.json", "example/*.json", "*example*.json", "*.normalized.json"):
        example_candidates.extend(sorted(subject_root.glob(pattern)))
    filtered = [candidate for candidate in example_candidates if candidate.name != "schema.json"]
    return filtered[0] if filtered else None


def _detect_entity_type(schema_path: Path, example_path: Path | None) -> str:
    if example_path is not None:
        try:
            payload = json.loads(example_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload.get("type"):
                return str(payload["type"])
        except Exception:
            LOGGER.debug("failed to parse example %s", example_path)

    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        title = schema.get("title") or schema.get("$id") or schema.get("description")
        if title:
            return str(title).split()[0]
    except Exception:
        LOGGER.debug("failed to parse schema %s", schema_path)
    return schema_path.parent.name


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    raw_root = repo_root() / args.raw_root
    rows: list[dict[str, str]] = []

    for repo_name in ("SmartCities", "SmartEnvironment", "dataModel.Environment", "data-models"):
        repo_path = raw_root / repo_name
        if not repo_path.exists():
            raise FileNotFoundError(f"missing repository: {repo_path}")
        for schema_path in sorted(repo_path.rglob("schema.json")):
            if not _looks_relevant(repo_name, schema_path, repo_path):
                continue
            subject_root = schema_path.parent
            example_path = _find_example(subject_root)
            readme_path = subject_root / "README.md"
            entity_type = _detect_entity_type(schema_path, example_path)
            relative_root = subject_root.relative_to(repo_path)
            domain_group = relative_root.parts[0] if relative_root.parts else subject_root.name
            rows.append(
                {
                    "source_repo": repo_name,
                    "subject_name": subject_root.name,
                    "schema_path": schema_path.relative_to(repo_root()).as_posix(),
                    "example_path": example_path.relative_to(repo_root()).as_posix() if example_path else "",
                    "entity_type": entity_type,
                    "domain_group": domain_group,
                    "readme_path": readme_path.relative_to(repo_root()).as_posix() if readme_path.exists() else "",
                }
            )

    output_path = repo_root() / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "source_repo",
        "subject_name",
        "schema_path",
        "example_path",
        "entity_type",
        "domain_group",
        "readme_path",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("wrote %s subject rows to %s", len(rows), output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
