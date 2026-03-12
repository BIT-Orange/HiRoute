"""Utility helpers for the HiRoute research workflow."""

from __future__ import annotations

import csv
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return REPO_ROOT


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    return utc_now().strftime("%Y%m%d_%H%M%S")


def isoformat_z(value: datetime | None = None) -> str:
    value = value or utc_now()
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sanitize_token(value: str) -> str:
    chars = []
    for char in value:
        if char.isalnum():
            chars.append(char.lower())
        else:
            chars.append("_")
    cleaned = "".join(chars)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_")


def load_json_yaml(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json_yaml(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def ensure_csv(path: Path, fieldnames: list[str]) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()


def append_csv(path: Path, fieldnames: list[str], row: dict[str, Any]) -> None:
    ensure_csv(path, fieldnames)
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writerow(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def git(args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        check=False,
        capture_output=capture_output,
        text=True,
    )


def git_head() -> str:
    result = git(["rev-parse", "--short", "HEAD"])
    if result.returncode != 0:
        return "uncommitted"
    return result.stdout.strip()


def git_branch() -> str:
    result = git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip()


def git_dirty() -> bool:
    result = git(["status", "--porcelain"])
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def git_snapshot_text() -> str:
    status = git(["status", "--short", "--branch"]).stdout
    head = git(["log", "-1", "--oneline"]).stdout
    return status + ("\n" if status and not status.endswith("\n") else "") + head


def env_snapshot_text() -> str:
    lines = [
        f"timestamp={isoformat_z()}",
        f"python={sys.version.split()[0]}",
        f"platform={platform.platform()}",
        f"machine={platform.machine()}",
        f"system={platform.system()}",
        f"cwd={REPO_ROOT}",
    ]
    return "\n".join(lines) + "\n"
