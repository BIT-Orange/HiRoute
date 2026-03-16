"""Shared helpers for smartcity_v3 workload generation."""

from __future__ import annotations

from typing import Iterable


def humanize_token(value: str) -> str:
    return value.replace("_", " ").replace("-", " ").strip()


def join_ids(values: Iterable[str]) -> str:
    items = sorted({value for value in values if value})
    return ";".join(items)


def parse_joined_ids(value: str) -> list[str]:
    if not value:
      return []
    return [item for item in value.split(";") if item]


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
        if tier == "routing_hard_v3":
            return f"{freshness_phrase} {intent_phrase} {service_phrase} near {zone_type_phrase}"
        if tier == "object_hard_v3":
            return f"{freshness_phrase} {intent_phrase} {service_phrase} for {zone_type_phrase}"
        return f"{freshness_phrase} {service_phrase} in {zone_type_phrase}"
    if tier == "routing_hard_v3":
        return (
            f"need {service_phrase} updates for {intent_phrase} conditions around "
            f"{zone_type_phrase} with {freshness_phrase} freshness"
        )
    if tier == "object_hard_v3":
        return (
            f"need the most relevant {service_phrase} readings for {intent_phrase} around "
            f"{zone_type_phrase} with {freshness_phrase} freshness"
        )
    return f"need {service_phrase} for {zone_type_phrase} with {freshness_phrase} freshness"
