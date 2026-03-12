#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAW_DIR="$ROOT_DIR/data/raw/smartdatamodels"
MANIFEST_PATH="$RAW_DIR/raw_manifest.json"

SMART_CITIES_URL="https://github.com/smart-data-models/SmartCities.git"
SMART_ENVIRONMENT_URL="https://github.com/smart-data-models/SmartEnvironment.git"
DATA_MODELS_URL="https://github.com/smart-data-models/data-models.git"
DATA_MODEL_ENVIRONMENT_URL="https://github.com/smart-data-models/dataModel.Environment.git"

mkdir -p "$RAW_DIR"

clone_if_missing() {
  local url="$1"
  local target="$2"
  if [[ ! -d "$target/.git" ]]; then
    git clone --depth 1 "$url" "$target"
  fi
}

clone_if_missing "$SMART_CITIES_URL" "$RAW_DIR/SmartCities"
clone_if_missing "$SMART_ENVIRONMENT_URL" "$RAW_DIR/SmartEnvironment"
clone_if_missing "$DATA_MODELS_URL" "$RAW_DIR/data-models"
clone_if_missing "$DATA_MODEL_ENVIRONMENT_URL" "$RAW_DIR/dataModel.Environment"

git -C "$RAW_DIR/SmartCities" submodule update --init --depth 1
git -C "$RAW_DIR/SmartEnvironment" submodule update --init --depth 1

ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
raw_dir = root / "data" / "raw" / "smartdatamodels"

def git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()

manifest = {
    "downloaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "repositories": {
        "SmartCities": {
            "url": "https://github.com/smart-data-models/SmartCities.git",
            "path": "data/raw/smartdatamodels/SmartCities",
            "commit": git_head(raw_dir / "SmartCities"),
        },
        "SmartEnvironment": {
            "url": "https://github.com/smart-data-models/SmartEnvironment.git",
            "path": "data/raw/smartdatamodels/SmartEnvironment",
            "commit": git_head(raw_dir / "SmartEnvironment"),
        },
        "data-models": {
            "url": "https://github.com/smart-data-models/data-models.git",
            "path": "data/raw/smartdatamodels/data-models",
            "commit": git_head(raw_dir / "data-models"),
        },
        "dataModel.Environment": {
            "url": "https://github.com/smart-data-models/dataModel.Environment.git",
            "path": "data/raw/smartdatamodels/dataModel.Environment",
            "commit": git_head(raw_dir / "dataModel.Environment"),
        },
    },
}
(raw_dir / "raw_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(raw_dir / "raw_manifest.json")
PY
