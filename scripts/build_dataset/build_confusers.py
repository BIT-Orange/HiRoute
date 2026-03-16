"""Shared helpers for smartcity_v3 object/confuser generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def humanize_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def deterministic_cycle(weights: dict[str, float], total: int = 100) -> list[str]:
    ordered = []
    items = list(weights.items())
    for label, weight in items:
        ordered.extend([label] * max(1, int(round(weight * total))))
    while len(ordered) < total:
        ordered.extend(label for label, _ in items)
    return ordered[:total]


def pick_difficulty(index: int, weights: dict[str, float]) -> str:
    cycle = deterministic_cycle(weights)
    return cycle[index % len(cycle)]


def family_variant(family: str, index: int, variants_per_family: int = 3) -> str:
    variant = (index % max(1, variants_per_family)) + 1
    return f"{family}_variant_{variant:02d}"


def object_role_from_id(object_id: str) -> str:
    if object_id.endswith("-snm01") or object_id.endswith("-snm02") or object_id.endswith("-snm03"):
        return "semantic_near_miss"
    if object_id.endswith("-cnm01") or object_id.endswith("-cnm02") or object_id.endswith("-cnm03"):
        return "constraint_near_miss"
    if object_id.endswith("-ncf01") or object_id.endswith("-ncf02") or object_id.endswith("-ncf03"):
        return "naming_confuser"
    return "target"


def append_suffix(object_id: str, suffix: str, index: int) -> str:
    return f"{object_id}-{suffix}{index:02d}"


def bundle_output_path(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    return path if path.is_absolute() else root / path
