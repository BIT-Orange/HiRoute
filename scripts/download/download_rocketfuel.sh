#!/bin/zsh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RAW_DIR="$ROOT_DIR/data/raw/rocketfuel"
CACHE_DIR="$RAW_DIR/cache"
MANIFEST_PATH="$RAW_DIR/raw_manifest.json"
WEIGHTS_ARCHIVE="$CACHE_DIR/weights-dist.tar.gz"
OFFICIAL_WEIGHTS_URL="https://research.cs.washington.edu/networking/rocketfuel/maps/weights-dist.tar.gz"
FALLBACK_REPO_URL="https://github.com/cawka/ndnSIM-sample-topologies.git"

mkdir -p "$RAW_DIR/3967" "$RAW_DIR/1239" "$CACHE_DIR"

download_with_curl() {
  local url="$1"
  local output="$2"
  curl -fsSL --retry 3 --retry-delay 2 "$url" -o "$output"
}

extract_from_archive() {
  local archive="$1"
  local file_name="$2"
  local destination="$3"
  local archive_member

  archive_member="$(tar -tzf "$archive" | grep -E "(^|/)$file_name$" | head -n 1 || true)"
  if [[ -z "$archive_member" ]]; then
    echo "missing $file_name inside $archive" >&2
    return 1
  fi

  tar -xzf "$archive" -C "$destination" "$archive_member"
  mv "$destination/$archive_member" "$destination/$file_name"

  local parent_dir
  parent_dir="$(dirname "$destination/$archive_member")"
  [[ "$parent_dir" == "$destination" ]] || rm -rf "$parent_dir"
}

fallback_clone() {
  local tmp_dir
  tmp_dir="$(mktemp -d /tmp/hiroute-rf-fallback.XXXXXX)"
  git clone --depth 1 "$FALLBACK_REPO_URL" "$tmp_dir/ndnSIM-sample-topologies"
  find "$tmp_dir/ndnSIM-sample-topologies" -maxdepth 3 -type f | sort > "$RAW_DIR/fallback_inventory.txt"
  rm -rf "$tmp_dir"
}

if [[ ! -f "$WEIGHTS_ARCHIVE" ]]; then
  if ! download_with_curl "$OFFICIAL_WEIGHTS_URL" "$WEIGHTS_ARCHIVE"; then
    rm -f "$WEIGHTS_ARCHIVE"
    fallback_clone
    echo "official Rocketfuel archive download failed; fallback inventory saved to $RAW_DIR/fallback_inventory.txt" >&2
    echo "chosen IMW2002 weights/latencies archive is still required for AS3967 and AS1239" >&2
    exit 1
  fi
fi

extract_from_archive "$WEIGHTS_ARCHIVE" "3967.weights.intra" "$RAW_DIR/3967"
extract_from_archive "$WEIGHTS_ARCHIVE" "3967.latencies.intra" "$RAW_DIR/3967"
extract_from_archive "$WEIGHTS_ARCHIVE" "1239.weights.intra" "$RAW_DIR/1239"
extract_from_archive "$WEIGHTS_ARCHIVE" "1239.latencies.intra" "$RAW_DIR/1239"

ROOT_DIR="$ROOT_DIR" python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
raw_dir = root / "data" / "raw" / "rocketfuel"
manifest = {
    "source": "official",
    "official_weights_url": "https://research.cs.washington.edu/networking/rocketfuel/maps/weights-dist.tar.gz",
    "fallback_repo_url": "https://github.com/cawka/ndnSIM-sample-topologies.git",
    "downloaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    "artifacts": {
        "rf_3967_exodus": {
            "weights": "data/raw/rocketfuel/3967/3967.weights.intra",
            "latencies": "data/raw/rocketfuel/3967/3967.latencies.intra"
        },
        "rf_1239_sprint": {
            "weights": "data/raw/rocketfuel/1239/1239.weights.intra",
            "latencies": "data/raw/rocketfuel/1239/1239.latencies.intra"
        }
    }
}
(raw_dir / "raw_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(raw_dir / "raw_manifest.json")
PY
