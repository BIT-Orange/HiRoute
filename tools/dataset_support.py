"""Helpers for dataset-manifest driven build scripts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.workflow_support import load_json_yaml, repo_root


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_root() / path


def load_dataset_manifest(path: str | Path) -> dict[str, Any]:
    return load_json_yaml(resolve_repo_path(path))


def load_rule_config(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    return load_json_yaml(resolve_repo_path(manifest["rules"][key]))


def output_path(manifest: dict[str, Any], key: str) -> Path:
    return resolve_repo_path(manifest["outputs"][key])


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with resolve_repo_path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    target = resolve_repo_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True) + "\n")
