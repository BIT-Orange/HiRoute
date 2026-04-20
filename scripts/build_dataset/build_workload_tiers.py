"""Shared helpers for smartcity workload generation."""

from __future__ import annotations

import re
from typing import Iterable


ZONE_SLOT_RE = re.compile(r"(zone-\d+)$")


def humanize_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def join_ids(values: Iterable[str]) -> str:
    items = sorted({value for value in values if value})
    return ";".join(items)


def parse_joined_ids(value: str) -> list[str]:
    if not value:
        return []
    return [item for item in value.split(";") if item]


def stable_rotate(values: Iterable[str], slot: int) -> list[str]:
    ordered = sorted({value for value in values if value})
    if not ordered:
        return []
    offset = slot % len(ordered)
    return ordered[offset:] + ordered[:offset]


def zone_slot_token(zone_id: str) -> str:
    match = ZONE_SLOT_RE.search(zone_id or "")
    return match.group(1) if match else (zone_id or "")


def zone_constraint_value(tokens: Iterable[str]) -> str:
    ordered = stable_rotate(tokens, 0)
    return ";".join(ordered)


def parse_zone_constraint(value: str) -> list[str]:
    return [token for token in value.split(";") if token]


def pick_style(style_weights: dict[str, float], index: int) -> str:
    ordered: list[str] = []
    for style, weight in style_weights.items():
        ordered.extend([style] * max(1, int(round(weight * 100))))
    while len(ordered) < 100:
        ordered.extend(style_weights.keys())
    return ordered[index % len(ordered)]


def render_query_text(
    style: str,
    service_phrase: str,
    intent_phrase: str,
    zone_type_phrase: str,
    freshness_phrase: str,
    tier: str,
) -> str:
    if style == "semantic_brief":
        if tier in {"routing_hard_v3", "routing_main"}:
            return f"{freshness_phrase} {intent_phrase} {service_phrase} near {zone_type_phrase}"
        if tier == "object_main":
            return f"{freshness_phrase} {service_phrase} for {zone_type_phrase}"
        if tier == "object_hard_v3":
            return f"{freshness_phrase} {intent_phrase} {service_phrase} for {zone_type_phrase}"
        return f"{freshness_phrase} {service_phrase} in {zone_type_phrase}"
    if tier in {"routing_hard_v3", "routing_main"}:
        return (
            f"need {service_phrase} updates for {intent_phrase} conditions around "
            f"{zone_type_phrase} with {freshness_phrase} freshness"
        )
    if tier == "object_main":
        return f"need {service_phrase} options around {zone_type_phrase} with {freshness_phrase} freshness"
    if tier == "object_hard_v3":
        return (
            f"need the most relevant {service_phrase} readings for {intent_phrase} around "
            f"{zone_type_phrase} with {freshness_phrase} freshness"
        )
    return f"need {service_phrase} for {zone_type_phrase} with {freshness_phrase} freshness"
