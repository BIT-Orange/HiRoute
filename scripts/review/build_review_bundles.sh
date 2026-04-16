#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_ROOT="${1:-$REPO_ROOT/review_bundles}"

mkdir -p "$OUTPUT_ROOT"

printf 'WARNING: scripts/review/build_review_bundles.sh is legacy archive tooling only.\n' >&2
printf 'WARNING: use tools/run_mainline_review_stage.sh and tools/package_review_bundle.sh for active mainline review bundles.\n' >&2

copy_path() {
  local bundle_root="$1"
  local rel_path="$2"
  local src="$REPO_ROOT/$rel_path"
  local dst="$bundle_root/$rel_path"

  [[ -e "$src" ]] || return 0
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
}

write_git_metadata() {
  local bundle_root="$1"
  git -C "$REPO_ROOT" rev-parse HEAD > "$bundle_root/git_commit.txt" 2>/dev/null || true
  git -C "$REPO_ROOT" status --short > "$bundle_root/git_status.txt" 2>/dev/null || true
  git -C "$REPO_ROOT" log --oneline -n 30 > "$bundle_root/git_log_30.txt" 2>/dev/null || true
}

build_core_bundle() {
  local bundle_name="hiroute_review_core"
  local bundle_root="$OUTPUT_ROOT/$bundle_name"

  rm -rf "$bundle_root" "$OUTPUT_ROOT/$bundle_name.zip"
  mkdir -p "$bundle_root"

  for rel_path in \
    "configs" \
    "docs" \
    "scripts" \
    "tools" \
    "paper" \
    "README.md" \
    "Todo.md" \
    "Makefile" \
    "requirements.txt" \
    "HiRoute_IoTJ.tex" \
    "data/processed/eval/qrels_domain.csv" \
    "data/processed/eval/qrels_object.csv" \
    "data/processed/eval/query_stats.json" \
    "data/processed/eval/workload_audit_v3.json" \
    "data/processed/ndnsim/objects_master.csv" \
    "data/processed/ndnsim/object_texts.jsonl" \
    "data/processed/ndnsim/queries_master.csv" \
    "data/processed/ndnsim/hslsa_export.csv" \
    "data/processed/ndnsim/controller_local_index.csv" \
    "data/processed/ndnsim/cell_membership.csv" \
    "data/processed/ndnsim/object_embedding_index.csv" \
    "data/processed/ndnsim/query_embedding_index.csv" \
    "data/processed/ndnsim/summary_embedding_index.csv" \
    "data/processed/ndnsim/topology_mapping.csv" \
    "data/processed/ndnsim/topology_mapping_rf_1239_sprint.csv" \
    "data/processed/ndnsim/topology_mapping_rf_1239_sprint.report.json" \
    "data/processed/ndnsim/topology_mapping_rf_3967_exodus.csv" \
    "data/processed/ndnsim/topology_mapping_rf_3967_exodus.report.json" \
    "data/processed/ndnsim/topology_mapping_rf_3967_exodus_compact.csv" \
    "data/processed/ndnsim/topology_mapping_rf_3967_exodus_compact.report.json" \
    "data/processed/ndnsim/object_embeddings.npy" \
    "data/processed/ndnsim/query_embeddings.npy" \
    "data/processed/ndnsim/summary_embeddings.npy" \
    "data/interim/topologies/rf_1239_sprint.annotated.txt" \
    "data/interim/topologies/rf_1239_sprint.dot" \
    "data/interim/topologies/rf_3967_exodus.annotated.txt" \
    "data/interim/topologies/rf_3967_exodus.dot" \
    "data/interim/topologies/rf_3967_exodus_compact.annotated.txt" \
    "data/interim/topologies/rf_3967_exodus_compact.dot" \
    "data/raw/rocketfuel/1239/1239.latencies.intra" \
    "data/raw/rocketfuel/1239/1239.weights.intra" \
    "data/raw/rocketfuel/3967/3967.latencies.intra" \
    "data/raw/rocketfuel/3967/3967.weights.intra" \
    "data/raw/rocketfuel/raw_manifest.json" \
    "results/aggregate" \
    "results/figures" \
    "ns-3/src/ndnSIM/apps" \
    "ns-3/src/ndnSIM/examples" \
    "ns-3/src/ndnSIM/helper" \
    "ns-3/src/ndnSIM/model" \
    "ns-3/src/ndnSIM/utils" \
    "ns-3/src/ndnSIM/wscript"; do
    copy_path "$bundle_root" "$rel_path"
  done

  write_git_metadata "$bundle_root"
  (cd "$OUTPUT_ROOT" && zip -rq "$bundle_name.zip" "$bundle_name")
}

build_runs_bundle() {
  local bundle_name="hiroute_review_runs"
  local bundle_root="$OUTPUT_ROOT/$bundle_name"

  rm -rf "$bundle_root" "$OUTPUT_ROOT/$bundle_name.zip"
  mkdir -p "$bundle_root"

  for rel_path in \
    "runs/registry" \
    "results/aggregate" \
    "results/figures"; do
    copy_path "$bundle_root" "$rel_path"
  done

  local file
  while IFS= read -r file; do
    local rel_path="${file#$REPO_ROOT/}"
    copy_path "$bundle_root" "$rel_path"
  done < <(
    find "$REPO_ROOT/runs/completed" -type f \( \
      -name "manifest.yaml" -o \
      -name "stdout.log" -o \
      -name "stderr.log" -o \
      -name "query_log.csv" -o \
      -name "probe_log.csv" -o \
      -name "search_trace.csv" -o \
      -name "state_log.csv" -o \
      -name "failure_event_log.csv" \
    \) | sort
  )

  write_git_metadata "$bundle_root"
  (cd "$OUTPUT_ROOT" && zip -rq "$bundle_name.zip" "$bundle_name")
}

build_metrics_bundle() {
  local bundle_name="hiroute_review_metrics"
  local bundle_root="$OUTPUT_ROOT/$bundle_name"

  rm -rf "$bundle_root" "$OUTPUT_ROOT/$bundle_name.zip"
  mkdir -p "$bundle_root"

  for rel_path in \
    "results/aggregate" \
    "results/figures"; do
    copy_path "$bundle_root" "$rel_path"
  done

  local file
  while IFS= read -r file; do
    local rel_path="${file#$REPO_ROOT/}"
    copy_path "$bundle_root" "$rel_path"
  done < <(
    find "$REPO_ROOT" \
      -path "$OUTPUT_ROOT" -prune -o \
      -path "$REPO_ROOT/.git" -prune -o \
      -type f \( \
        -name "query_log.csv" -o \
        -name "probe_log.csv" -o \
        -name "search_trace.csv" -o \
        -name "state_log.csv" -o \
        -name "failure_event_log.csv" -o \
        -name "*main_success_overhead*.csv" -o \
        -name "*failure_breakdown*.csv" -o \
        -name "*candidate*shrinkage*.csv" -o \
        -name "*deadline*summary*.csv" -o \
        -name "*state*scaling*.csv" -o \
        -name "*ablation*.csv" -o \
        -name "*robustness*.csv" \
      \) -print | sort
  )

  write_git_metadata "$bundle_root"
  (cd "$OUTPUT_ROOT" && zip -rq "$bundle_name.zip" "$bundle_name")
}

build_core_bundle
build_runs_bundle
build_metrics_bundle

printf 'Built review bundles in %s\n' "$OUTPUT_ROOT"
find "$OUTPUT_ROOT" -maxdepth 1 -type f -name '*.zip' -print | sort
