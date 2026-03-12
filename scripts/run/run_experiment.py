"""Execute a HiRoute experiment run and emit reproducible run artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.make_run_id import make_run_id
from tools.validate_run import validate_context
from tools.workflow_support import (
    GENERATED_TRACKED_PREFIXES,
    append_csv,
    dump_json_yaml,
    env_snapshot_text,
    git_branch,
    git_dirty,
    git_head,
    git_snapshot_text,
    isoformat_z,
    load_json_yaml,
    read_csv,
    repo_root,
    utc_now,
    write_csv,
)


RUNS_FIELDS = [
    "run_id",
    "experiment_id",
    "scheme",
    "dataset_id",
    "topology_id",
    "seed",
    "git_commit",
    "start_time",
    "end_time",
    "duration_sec",
    "status",
    "run_dir",
]

FAILED_FIELDS = [
    "run_id",
    "experiment_id",
    "scheme",
    "seed",
    "git_commit",
    "error_stage",
    "error_message",
    "run_dir",
    "timestamp",
]

QUERY_LOG_FIELDS = [
    "query_id",
    "scheme",
    "seed",
    "topology_id",
    "dataset_id",
    "start_time_ms",
    "end_time_ms",
    "latency_ms",
    "success_at_1",
    "manifest_hit_at_3",
    "manifest_hit_at_5",
    "ndcg_at_5",
    "final_object_id",
    "final_domain_id",
    "final_cell_id",
    "num_remote_probes",
    "discovery_tx_bytes",
    "discovery_rx_bytes",
    "fetch_tx_bytes",
    "fetch_rx_bytes",
    "failure_type",
]

PROBE_LOG_FIELDS = [
    "query_id",
    "scheme",
    "seed",
    "probe_index",
    "target_domain_id",
    "target_cell_id",
    "probe_latency_ms",
    "accepted",
]

SEARCH_TRACE_FIELDS = [
    "query_id",
    "scheme",
    "stage",
    "candidate_count",
    "selected_count",
    "frontier_size",
    "timestamp_ms",
]

STATE_LOG_FIELDS = [
    "timestamp_ms",
    "scheme",
    "domain_id",
    "num_exported_summaries",
    "exported_summary_bytes",
    "summary_updates_sent",
    "objects_in_domain",
    "domains_total",
    "budget",
]

FAILURE_EVENT_FIELDS = [
    "event_id",
    "scheme",
    "event_type",
    "target_type",
    "target_id",
    "inject_time_ms",
    "recover_time_ms",
]

FAILURE_TYPES = ["success", "predicate_miss", "wrong_domain", "wrong_object", "fetch_timeout", "no_reply"]
SEARCH_STAGES = [
    "all_domains",
    "predicate_filtered_domains",
    "level0_cells",
    "level1_cells",
    "refined_cells",
    "probed_cells",
    "manifest_candidates",
]


def _resolve(path_str: str) -> Path:
    path = Path(path_str)
    return path if path.is_absolute() else repo_root() / path


def _copy_snapshots(experiment: dict[str, Any], scheme: str, config_snapshot_dir: Path) -> None:
    config_snapshot_dir.mkdir(parents=True, exist_ok=True)
    config_map = {
        "experiment_config": experiment["_experiment_path"],
        "baseline_config": experiment["configs"]["baselines"][scheme],
        "hierarchy_config": experiment["configs"]["hierarchy"],
        "dataset_config": experiment["configs"]["dataset"],
        "topology_config": experiment["configs"]["topology"],
    }
    for _, source in config_map.items():
        source_path = _resolve(str(source))
        shutil.copy2(source_path, config_snapshot_dir / source_path.name)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_dataset_context(experiment: dict[str, Any]) -> dict[str, Any]:
    inputs = experiment["inputs"]
    objects = read_csv(_resolve(inputs["objects_csv"]))
    queries = read_csv(_resolve(inputs["queries_csv"]))
    qrels_object = read_csv(_resolve(inputs["qrels_object_csv"]))
    qrels_domain = read_csv(_resolve(inputs["qrels_domain_csv"]))
    topology = read_csv(_resolve(inputs["topology_mapping_csv"]))
    hslsa = read_csv(_resolve(inputs["hslsa_csv"]))

    object_by_id = {row["object_id"]: row for row in objects}
    relevant_objects: dict[str, list[dict[str, str]]] = {}
    relevant_domains: dict[str, list[str]] = {}

    for row in qrels_object:
        if int(row["relevance"]) <= 0:
            continue
        relevant_objects.setdefault(row["query_id"], []).append(row)
    for row in qrels_domain:
        if row["is_relevant_domain"] != "1":
            continue
        relevant_domains.setdefault(row["query_id"], []).append(row["domain_id"])

    return {
        "objects": objects,
        "queries": queries,
        "qrels_object": relevant_objects,
        "qrels_domain": relevant_domains,
        "object_by_id": object_by_id,
        "topology": topology,
        "hslsa": hslsa,
    }


def _scheme_profile(experiment: dict[str, Any], scheme: str) -> dict[str, float]:
    baseline_config = load_json_yaml(_resolve(experiment["configs"]["baselines"][scheme]))
    defaults = {
        "success_bias": 0.6,
        "manifest_bias": 0.65,
        "ndcg_bias": 0.55,
        "probe_bias": 3.0,
        "discovery_byte_bias": 500.0,
        "fetch_byte_bias": 120.0,
        "latency_bias": 75.0,
    }
    defaults.update(baseline_config.get("mock_profile", {}))
    return defaults


def _generate_mock_outputs(
    experiment: dict[str, Any],
    scheme: str,
    seed: int,
    run_dir: Path,
    dataset_context: dict[str, Any],
) -> None:
    profile = _scheme_profile(experiment, scheme)
    rng = random.Random(f"{experiment['experiment_id']}::{scheme}::{seed}")
    queries = dataset_context["queries"]
    topology_id = experiment["topology_id"]
    dataset_id = experiment["dataset_id"]
    domain_total = len({row["domain_id"] for row in dataset_context["objects"]})
    max_budget = max(experiment.get("budgets", [16]))

    query_rows = []
    probe_rows = []
    search_rows = []
    failure_rows = []

    domains = [row["domain_id"] for row in dataset_context["topology"] if row["role"] == "controller"]
    if not domains:
        domains = sorted({row["domain_id"] for row in dataset_context["objects"]})

    for index, query in enumerate(queries):
        relevant_objects = dataset_context["qrels_object"].get(query["query_id"], [])
        relevant_domains = dataset_context["qrels_domain"].get(query["query_id"], [])
        difficulty_penalty = 0.08 if query["difficulty"] == "hard" else 0.03
        ambiguity_penalty = {"low": 0.01, "medium": 0.07, "high": 0.15}[query["ambiguity_level"]]
        success_probability = max(
            0.05,
            min(0.99, profile["success_bias"] - difficulty_penalty - ambiguity_penalty + rng.uniform(-0.05, 0.05)),
        )
        success = rng.random() <= success_probability

        if success and relevant_objects:
            final_object_id = rng.choice(relevant_objects)["object_id"]
            final_domain_id = dataset_context["object_by_id"][final_object_id]["domain_id"]
            failure_type = "success"
        else:
            failure_type = rng.choices(
                FAILURE_TYPES[1:],
                weights=[0.15, 0.3, 0.3, 0.15, 0.1],
                k=1,
            )[0]
            if failure_type == "wrong_domain":
                non_relevant = [domain for domain in domains if domain not in relevant_domains] or domains
                final_domain_id = rng.choice(non_relevant)
                final_object_id = ""
            elif failure_type == "wrong_object" and relevant_domains:
                final_domain_id = rng.choice(relevant_domains)
                wrong_candidates = [
                    row["object_id"]
                    for row in dataset_context["objects"]
                    if row["domain_id"] == final_domain_id
                    and row["object_id"] not in {item["object_id"] for item in relevant_objects}
                ]
                final_object_id = rng.choice(wrong_candidates) if wrong_candidates else ""
            else:
                final_domain_id = rng.choice(domains) if domains else ""
                final_object_id = ""

        final_cell_id = f"{final_domain_id}-cell-{(index % 4) + 1}" if final_domain_id else ""
        start_time_ms = int(query["start_time_ms"])
        latency_ms = round(profile["latency_bias"] + rng.uniform(5.0, 45.0) + ambiguity_penalty * 120.0, 3)
        end_time_ms = round(start_time_ms + latency_ms, 3)
        manifest_hit_5 = 1 if success or (relevant_objects and rng.random() < profile["manifest_bias"]) else 0
        manifest_hit_3 = 1 if manifest_hit_5 and rng.random() < 0.7 else 0
        ndcg_at_5 = round(min(1.0, profile["ndcg_bias"] + rng.uniform(-0.12, 0.12)), 3) if manifest_hit_5 else 0.0
        num_remote_probes = max(0, int(round(profile["probe_bias"] + rng.uniform(-1.0, 2.0))))
        discovery_tx_bytes = int(profile["discovery_byte_bias"] + num_remote_probes * 48 + rng.uniform(0, 96))
        discovery_rx_bytes = int(profile["discovery_byte_bias"] * 0.6 + num_remote_probes * 36 + rng.uniform(0, 96))
        fetch_tx_bytes = int(profile["fetch_byte_bias"] + rng.uniform(0, 24))
        fetch_rx_bytes = int(profile["fetch_byte_bias"] * 2 + rng.uniform(0, 48))

        query_rows.append(
            {
                "query_id": query["query_id"],
                "scheme": scheme,
                "seed": seed,
                "topology_id": topology_id,
                "dataset_id": dataset_id,
                "start_time_ms": start_time_ms,
                "end_time_ms": end_time_ms,
                "latency_ms": latency_ms,
                "success_at_1": 1 if success else 0,
                "manifest_hit_at_3": manifest_hit_3,
                "manifest_hit_at_5": manifest_hit_5,
                "ndcg_at_5": ndcg_at_5,
                "final_object_id": final_object_id,
                "final_domain_id": final_domain_id,
                "final_cell_id": final_cell_id,
                "num_remote_probes": num_remote_probes,
                "discovery_tx_bytes": discovery_tx_bytes,
                "discovery_rx_bytes": discovery_rx_bytes,
                "fetch_tx_bytes": fetch_tx_bytes,
                "fetch_rx_bytes": fetch_rx_bytes,
                "failure_type": failure_type,
            }
        )

        for probe_index in range(num_remote_probes):
            probe_rows.append(
                {
                    "query_id": query["query_id"],
                    "scheme": scheme,
                    "seed": seed,
                    "probe_index": probe_index + 1,
                    "target_domain_id": rng.choice(domains) if domains else "",
                    "target_cell_id": f"cell-{(probe_index % 4) + 1}",
                    "probe_latency_ms": round(8 + rng.uniform(0, 12), 3),
                    "accepted": 1 if probe_index == num_remote_probes - 1 and success else 0,
                }
            )

        base_candidates = domain_total
        candidate_path = [
            base_candidates,
            max(1, int(base_candidates * 0.75)),
            max(1, int(base_candidates * 0.5)),
            max(1, int(base_candidates * 0.25)),
            max(1, int(base_candidates * 0.12)),
            max(1, int(num_remote_probes or 1)),
            5 if manifest_hit_5 else 3,
        ]
        for stage_index, stage in enumerate(SEARCH_STAGES):
            candidate_count = candidate_path[stage_index]
            search_rows.append(
                {
                    "query_id": query["query_id"],
                    "scheme": scheme,
                    "stage": stage,
                    "candidate_count": candidate_count,
                    "selected_count": max(1, candidate_count // 2),
                    "frontier_size": max(1, candidate_count // 3),
                    "timestamp_ms": round(start_time_ms + stage_index * (latency_ms / len(SEARCH_STAGES)), 3),
                }
            )

        if failure_type != "success" and failure_type in {"fetch_timeout", "no_reply"}:
            failure_rows.append(
                {
                    "event_id": f"{query['query_id']}-evt-1",
                    "scheme": scheme,
                    "event_type": "controller_down" if failure_type == "no_reply" else "summary_stale",
                    "target_type": "controller" if failure_type == "no_reply" else "summary",
                    "target_id": final_domain_id or "unknown",
                    "inject_time_ms": start_time_ms,
                    "recover_time_ms": end_time_ms,
                }
            )

    object_counts = Counter(row["domain_id"] for row in dataset_context["objects"])
    state_rows = []
    for domain_id in sorted(object_counts):
        state_rows.append(
            {
                "timestamp_ms": 0,
                "scheme": scheme,
                "domain_id": domain_id,
                "num_exported_summaries": len([row for row in dataset_context["hslsa"] if row["domain_id"] == domain_id]),
                "exported_summary_bytes": object_counts[domain_id] * 32,
                "summary_updates_sent": 1,
                "objects_in_domain": object_counts[domain_id],
                "domains_total": domain_total,
                "budget": max_budget,
            }
        )

    write_csv(run_dir / "query_log.csv", QUERY_LOG_FIELDS, query_rows)
    write_csv(run_dir / "probe_log.csv", PROBE_LOG_FIELDS, probe_rows)
    write_csv(run_dir / "search_trace.csv", SEARCH_TRACE_FIELDS, search_rows)
    write_csv(run_dir / "state_log.csv", STATE_LOG_FIELDS, state_rows)
    write_csv(run_dir / "failure_event_log.csv", FAILURE_EVENT_FIELDS, failure_rows)


def _parse_controller_domain(controller_prefix: str) -> str:
    parts = [part for part in controller_prefix.split("/") if part]
    return parts[1] if len(parts) >= 2 else ""


def _copy_raw_if_needed(path: Path) -> Path:
    raw_path = path.with_suffix(path.suffix + ".raw")
    if not raw_path.exists():
        shutil.copy2(path, raw_path)
    return raw_path


def _normalize_ndnsim_query_log(
    run_dir: Path,
    experiment: dict[str, Any],
    scheme: str,
    seed: int,
) -> None:
    query_log_path = run_dir / "query_log.csv"
    if not query_log_path.exists():
        return

    rows = read_csv(query_log_path)
    if not rows:
        write_csv(query_log_path, QUERY_LOG_FIELDS, [])
        return
    if "manifest_hit_at_5" in rows[0]:
        return

    _copy_raw_if_needed(query_log_path)
    object_by_id = {
        row["object_id"]: row
        for row in read_csv(_resolve(experiment["inputs"]["objects_csv"]))
    }
    normalized = []
    for row in rows:
        object_id = row.get("fetched_object_id", "")
        object_row = object_by_id.get(object_id, {})
        latency_ms = float(row.get("latency_ms") or 0.0)
        start_time_ms = float(row.get("start_time_ms") or 0.0)
        discovery_bytes = float(row.get("discovery_bytes") or 0.0)
        normalized.append(
            {
                "query_id": row["query_id"],
                "scheme": scheme,
                "seed": seed,
                "topology_id": experiment["topology_id"],
                "dataset_id": experiment["dataset_id"],
                "start_time_ms": start_time_ms,
                "end_time_ms": round(start_time_ms + latency_ms, 3),
                "latency_ms": latency_ms,
                "success_at_1": int(row.get("success_at_1", 0)),
                "manifest_hit_at_3": int(row.get("manifest_hit_at_r", 0)),
                "manifest_hit_at_5": int(row.get("manifest_hit_at_r", 0)),
                "ndcg_at_5": float(row.get("ndcg_at_r") or 0.0),
                "final_object_id": object_id,
                "final_domain_id": object_row.get("domain_id", ""),
                "final_cell_id": object_row.get("zone_id", ""),
                "num_remote_probes": int(row.get("remote_probes") or 0),
                "discovery_tx_bytes": int(discovery_bytes),
                "discovery_rx_bytes": 0,
                "fetch_tx_bytes": 0,
                "fetch_rx_bytes": int(object_row.get("payload_size_bytes") or 0),
                "failure_type": "success"
                if str(row.get("success_at_1", "0")) == "1"
                else row.get("failure_type", "unknown"),
            }
        )
    write_csv(query_log_path, QUERY_LOG_FIELDS, normalized)


def _normalize_ndnsim_probe_log(run_dir: Path, scheme: str, seed: int) -> None:
    probe_log_path = run_dir / "probe_log.csv"
    if not probe_log_path.exists():
        return

    rows = read_csv(probe_log_path)
    if not rows:
        write_csv(probe_log_path, PROBE_LOG_FIELDS, [])
        return
    if "target_domain_id" in rows[0]:
        return

    _copy_raw_if_needed(probe_log_path)
    normalized = []
    for row in rows:
        normalized.append(
            {
                "query_id": row["query_id"],
                "scheme": scheme,
                "seed": seed,
                "probe_index": row.get("probe_index", "0"),
                "target_domain_id": _parse_controller_domain(row.get("controller_prefix", "")),
                "target_cell_id": row.get("cell_id", ""),
                "probe_latency_ms": 0,
                "accepted": 1 if str(row.get("reply_entries", "0")) != "0" else 0,
            }
        )
    write_csv(probe_log_path, PROBE_LOG_FIELDS, normalized)


def _normalize_ndnsim_search_trace(run_dir: Path, scheme: str) -> None:
    search_trace_path = run_dir / "search_trace.csv"
    if not search_trace_path.exists():
        return

    rows = read_csv(search_trace_path)
    if not rows:
        write_csv(search_trace_path, SEARCH_TRACE_FIELDS, [])
        return
    if "stage" in rows[0]:
        return

    _copy_raw_if_needed(search_trace_path)
    normalized = []
    for row in rows:
        rank = int(row.get("rank") or 0)
        normalized.append(
            {
                "query_id": row["query_id"],
                "scheme": scheme,
                "stage": f"candidate_rank_{rank}",
                "candidate_count": rank + 1,
                "selected_count": 1,
                "frontier_size": 1,
                "timestamp_ms": rank,
            }
        )
    write_csv(search_trace_path, SEARCH_TRACE_FIELDS, normalized)


def _normalize_ndnsim_outputs(
    experiment: dict[str, Any],
    scheme: str,
    seed: int,
    run_dir: Path,
) -> None:
    _normalize_ndnsim_query_log(run_dir, experiment, scheme, seed)
    _normalize_ndnsim_probe_log(run_dir, scheme, seed)
    _normalize_ndnsim_search_trace(run_dir, scheme)


def _prepare_runtime_query_csv(experiment: dict[str, Any], run_dir: Path) -> Path:
    query_csv_path = _resolve(experiment["inputs"]["queries_csv"])
    topology_mapping_path = _resolve(experiment["inputs"]["topology_mapping_csv"])
    query_rows = read_csv(query_csv_path)
    topology_rows = read_csv(topology_mapping_path)
    ingress_nodes = [row["node_id"] for row in topology_rows if row["role"] == "ingress"]
    if not query_rows or not ingress_nodes:
        return query_csv_path

    query_ingress_nodes = {row["ingress_node_id"] for row in query_rows}
    if query_ingress_nodes.issubset(set(ingress_nodes)):
        return query_csv_path

    remapped_rows = []
    for index, row in enumerate(query_rows):
        remapped = dict(row)
        remapped["ingress_node_id"] = ingress_nodes[index % len(ingress_nodes)]
        remapped_rows.append(remapped)

    runtime_query_csv = run_dir / "queries_runtime.csv"
    write_csv(runtime_query_csv, list(query_rows[0].keys()), remapped_rows)
    experiment["_runtime_query_csv"] = str(runtime_query_csv.relative_to(repo_root()))
    return runtime_query_csv


def _run_external(command: list[str], cwd: Path) -> tuple[int, str, str]:
    result = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def _scenario_binary_path(ns3_root: Path, scenario: str) -> Path | None:
    examples_dir = ns3_root / "build" / "src" / "ndnSIM" / "examples"
    matches = sorted(examples_dir.glob(f"ns3.*-{scenario}-debug"))
    return matches[0] if matches else None


def _ndnsim_command(
    experiment: dict[str, Any],
    scheme: str,
    run_dir: Path,
    binary: Path,
) -> tuple[Path, list[str]]:
    runner = experiment.get("runner", {})
    ns3_root = _resolve(runner.get("ns3_root", "ns-3"))
    topology_config = load_json_yaml(_resolve(experiment["configs"]["topology"]))
    params = runner.get("params", {})

    runtime_query_csv = _prepare_runtime_query_csv(experiment, run_dir)
    command = [
        str(binary),
        f"--topology={_resolve(topology_config['annotated_topology_path'])}",
        f"--topologyMapping={_resolve(experiment['inputs']['topology_mapping_csv'])}",
        f"--objectsCsv={_resolve(experiment['inputs']['objects_csv'])}",
        f"--queryCsv={runtime_query_csv}",
        f"--queryEmbeddingIndexCsv={_resolve(experiment['inputs']['query_embedding_index_csv'])}",
        f"--qrelsObjectCsv={_resolve(experiment['inputs']['qrels_object_csv'])}",
        f"--summaryCsv={_resolve(experiment['inputs']['hslsa_csv'])}",
        f"--controllerLocalIndexCsv={_resolve(experiment['inputs']['controller_local_index_csv'])}",
        f"--runDir={run_dir}",
        f"--topologyId={experiment['topology_id']}",
        f"--scheme={scheme}",
    ]
    for flag in [
        "stopSeconds",
        "failureTime",
        "recoveryTime",
        "staleDropProbability",
        "manifestSize",
        "probeBudget",
        "queryLimitPerIngress",
    ]:
        if flag in params:
            command.append(f"--{flag}={params[flag]}")
    return ns3_root, command


def _run_ndnsim(
    experiment: dict[str, Any],
    scheme: str,
    run_dir: Path,
) -> tuple[int, str, str]:
    runner = experiment.get("runner", {})
    ns3_root = _resolve(runner.get("ns3_root", "ns-3"))
    binary = _scenario_binary_path(ns3_root, experiment["scenario"])
    build_always = bool(runner.get("build_before_run", False))
    if build_always or binary is None or not binary.exists():
        build_code, build_stdout, build_stderr = _run_external(["./waf", "build"], ns3_root)
        if build_code != 0:
            return build_code, build_stdout, build_stderr
        binary = _scenario_binary_path(ns3_root, experiment["scenario"])
        if binary is None or not binary.exists():
            return 1, build_stdout, build_stderr + "\nmissing ndnSIM scenario binary after build"
    _, command = _ndnsim_command(experiment, scheme, run_dir, binary)
    return _run_external(command, ns3_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", required=True, type=Path)
    parser.add_argument("--scheme", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--mode", choices=["dry", "official"], default="official")
    parser.add_argument("--timestamp")
    parser.add_argument("--topology-id")
    parser.add_argument("--variant")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    experiment_path = args.experiment if args.experiment.is_absolute() else repo_root() / args.experiment
    experiment, errors = validate_context(
        experiment_path,
        args.scheme,
        args.seed,
        args.mode,
        args.topology_id,
        args.variant,
    )
    experiment["_experiment_path"] = str(experiment_path)

    run_id = make_run_id(
        experiment,
        args.scheme,
        args.seed,
        args.timestamp,
        experiment["topology_id"],
        experiment.get("_runner_variant"),
    )
    run_root = repo_root() / "runs" / ("pending" if args.mode == "dry" else "completed")
    run_dir = run_root / run_id
    git_commit = git_head()
    timestamp = isoformat_z()

    if errors:
        if args.mode == "official":
            append_csv(
                repo_root() / "runs" / "registry" / "failed_runs.csv",
                FAILED_FIELDS,
                {
                    "run_id": run_id,
                    "experiment_id": experiment.get("experiment_id", "unknown"),
                    "scheme": args.scheme,
                    "seed": args.seed,
                    "git_commit": git_commit,
                    "error_stage": "pre_run_validation",
                    "error_message": " | ".join(errors),
                    "run_dir": str(run_dir.relative_to(repo_root())),
                    "timestamp": timestamp,
                },
            )
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if run_dir.exists():
        print(f"ERROR: run directory already exists: {run_dir}")
        return 1

    run_dir.mkdir(parents=True, exist_ok=False)
    config_snapshot_dir = run_dir / "config_snapshot"
    _copy_snapshots(experiment, args.scheme, config_snapshot_dir)

    (run_dir / "git_snapshot.txt").write_text(git_snapshot_text(), encoding="utf-8")
    (run_dir / "env_snapshot.txt").write_text(env_snapshot_text(), encoding="utf-8")
    (run_dir / "notes.md").write_text("# Experiment Notes\n\n- hypothesis:\n- expected outcome:\n- surprises:\n", encoding="utf-8")

    start_time = utc_now()
    status = "completed"
    exit_code = 0
    stdout_text = ""
    stderr_text = ""

    runner = experiment.get("runner", {"type": "mock"})
    if runner.get("type", "mock") == "mock":
        dataset_context = _load_dataset_context(experiment)
        _generate_mock_outputs(experiment, args.scheme, args.seed, run_dir, dataset_context)
    elif runner.get("type") == "ndnsim":
        exit_code, stdout_text, stderr_text = _run_ndnsim(experiment, args.scheme, run_dir)
        status = "completed" if exit_code == 0 else "failed"
        if status == "completed":
            try:
                _normalize_ndnsim_outputs(experiment, args.scheme, args.seed, run_dir)
            except Exception as exc:  # pragma: no cover - surfaced in run stderr/manifest
                status = "failed"
                exit_code = 1
                stderr_text = (stderr_text + "\n" if stderr_text else "") + (
                    f"normalize_ndnsim_outputs failed: {exc}"
                )
    else:
        command = runner.get("command", [])
        working_dir = _resolve(runner.get("cwd", "."))
        exit_code, stdout_text, stderr_text = _run_external(command, working_dir)
        status = "completed" if exit_code == 0 else "failed"

    end_time = utc_now()
    duration_sec = round((end_time - start_time).total_seconds(), 3)
    (run_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")

    manifest = {
        "run_id": run_id,
        "experiment_id": experiment["experiment_id"],
        "scheme": args.scheme,
        "dataset_id": experiment["dataset_id"],
        "topology_id": experiment["topology_id"],
        "scenario": experiment["scenario"],
        "seed": args.seed,
        "code": {
            "git_commit": git_commit,
            "git_branch": git_branch(),
            "git_dirty": git_dirty(GENERATED_TRACKED_PREFIXES),
        },
        "configs": {
            "experiment_config": str(Path(experiment["_experiment_path"]).relative_to(repo_root())),
            "baseline_config": experiment["configs"]["baselines"][args.scheme],
            "hierarchy_config": experiment["configs"]["hierarchy"],
            "dataset_config": experiment["configs"]["dataset"],
            "topology_config": experiment["configs"]["topology"],
        },
        "inputs": experiment["inputs"],
        "outputs": {
            "query_log": "query_log.csv",
            "probe_log": "probe_log.csv",
            "search_trace": "search_trace.csv",
            "state_log": "state_log.csv",
            "failure_event_log": "failure_event_log.csv",
        },
        "status": status,
        "exit_code": exit_code,
        "start_time": isoformat_z(start_time),
        "end_time": isoformat_z(end_time),
        "duration_sec": duration_sec,
    }
    if experiment.get("_runtime_query_csv"):
        manifest["inputs"]["queries_csv_runtime"] = experiment["_runtime_query_csv"]
    if experiment.get("_runner_variant"):
        manifest["scenario_variant"] = experiment["_runner_variant"]
    dump_json_yaml(run_dir / "manifest.yaml", manifest)

    if status == "completed" and args.mode == "official":
        append_csv(
            repo_root() / "runs" / "registry" / "runs.csv",
            RUNS_FIELDS,
            {
                "run_id": run_id,
                "experiment_id": experiment["experiment_id"],
                "scheme": args.scheme,
                "dataset_id": experiment["dataset_id"],
                "topology_id": experiment["topology_id"],
                "seed": args.seed,
                "git_commit": git_commit,
                "start_time": isoformat_z(start_time),
                "end_time": isoformat_z(end_time),
                "duration_sec": duration_sec,
                "status": status,
                "run_dir": str(run_dir.relative_to(repo_root())),
            },
        )
        print(run_id)
        return 0
    if status == "completed":
        print(run_id)
        return 0

    if args.mode == "official":
        append_csv(
            repo_root() / "runs" / "registry" / "failed_runs.csv",
            FAILED_FIELDS,
            {
                "run_id": run_id,
                "experiment_id": experiment["experiment_id"],
                "scheme": args.scheme,
                "seed": args.seed,
                "git_commit": git_commit,
                "error_stage": "runner",
                "error_message": stderr_text.strip() or "external command failed",
                "run_dir": str(run_dir.relative_to(repo_root())),
                "timestamp": isoformat_z(end_time),
            },
        )
    print(run_id)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
