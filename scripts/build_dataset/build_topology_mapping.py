"""Build Rocketfuel-derived topology-to-domain mappings for HiRoute."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, repo_root, write_csv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topology-config",
        default="configs/topologies/rocketfuel_3967_exodus.yaml",
        type=Path,
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def parse_annotated_topology(path: Path) -> tuple[list[str], dict[str, set[str]]]:
    nodes: list[str] = []
    adjacency: dict[str, set[str]] = defaultdict(set)
    section = ""

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "router":
                section = "router"
                continue
            if line == "link":
                section = "link"
                continue

            parts = line.split()
            if section == "router":
                node_name = parts[0]
                nodes.append(node_name)
                adjacency.setdefault(node_name, set())
            elif section == "link":
                src, dst = parts[0], parts[1]
                adjacency[src].add(dst)
                adjacency[dst].add(src)

    return sorted(nodes), adjacency


def bfs_distances(adjacency: dict[str, set[str]], start: str) -> dict[str, int]:
    distances = {start: 0}
    queue: deque[str] = deque([start])

    while queue:
        current = queue.popleft()
        for neighbor in sorted(adjacency[current]):
            if neighbor in distances:
                continue
            distances[neighbor] = distances[current] + 1
            queue.append(neighbor)

    return distances


def select_seeds(nodes: list[str], adjacency: dict[str, set[str]], k: int) -> list[str]:
    ranked_nodes = sorted(nodes, key=lambda node: (-len(adjacency[node]), node))
    if not ranked_nodes:
        return []

    seeds = [ranked_nodes[0]]
    distance_cache = {seeds[0]: bfs_distances(adjacency, seeds[0])}

    while len(seeds) < min(k, len(ranked_nodes)):
        best_node = None
        best_score = None
        for node in ranked_nodes:
            if node in seeds:
                continue
            min_distance = min(distance_cache[seed].get(node, 10**9) for seed in seeds)
            score = (min_distance, len(adjacency[node]), node)
            if best_score is None or score > best_score:
                best_score = score
                best_node = node
        if best_node is None:
            break
        seeds.append(best_node)
        distance_cache[best_node] = bfs_distances(adjacency, best_node)

    return seeds


def assign_domains(
    nodes: list[str],
    adjacency: dict[str, set[str]],
    seeds: list[str],
) -> tuple[dict[str, str], dict[str, str]]:
    assignments: dict[str, str] = {}
    seed_to_domain: dict[str, str] = {}
    queue: deque[str] = deque()

    for index, seed in enumerate(seeds, start=1):
        domain_id = f"domain-{index:02d}"
        assignments[seed] = domain_id
        seed_to_domain[seed] = domain_id
        queue.append(seed)

    while queue:
        current = queue.popleft()
        current_domain = assignments[current]
        for neighbor in sorted(adjacency[current]):
            if neighbor in assignments:
                continue
            assignments[neighbor] = current_domain
            queue.append(neighbor)

    for node in nodes:
        assignments.setdefault(node, seed_to_domain[seeds[0]])

    return assignments, seed_to_domain


def rebalance_domains(
    adjacency: dict[str, set[str]],
    assignments: dict[str, str],
    seed_to_domain: dict[str, str],
    minimum_domain_size: int,
) -> dict[str, str]:
    domain_to_seed = {domain_id: seed for seed, domain_id in seed_to_domain.items()}

    while True:
        grouped_nodes: dict[str, list[str]] = defaultdict(list)
        for node_name, domain_id in assignments.items():
            grouped_nodes[domain_id].append(node_name)

        small_domains = [
            domain_id
            for domain_id, domain_nodes in sorted(grouped_nodes.items())
            if len(domain_nodes) < minimum_domain_size
        ]
        if not small_domains:
            return assignments

        changed = False
        for domain_id in small_domains:
            grouped_nodes = defaultdict(list)
            for node_name, assigned_domain in assignments.items():
                grouped_nodes[assigned_domain].append(node_name)

            if len(grouped_nodes[domain_id]) >= minimum_domain_size:
                continue

            domain_nodes = set(grouped_nodes[domain_id])
            boundary_candidates: list[tuple[tuple[int, int, str, str], str]] = []

            for node_name in sorted(domain_nodes):
                for neighbor in sorted(adjacency[node_name]):
                    source_domain = assignments[neighbor]
                    if source_domain == domain_id:
                        continue
                    if len(grouped_nodes[source_domain]) <= minimum_domain_size:
                        continue
                    if neighbor == domain_to_seed.get(source_domain):
                        continue

                    shared_links = sum(1 for peer in adjacency[neighbor] if assignments.get(peer) == domain_id)
                    score = (shared_links, -len(adjacency[neighbor]), source_domain, neighbor)
                    boundary_candidates.append((score, neighbor))

            if boundary_candidates:
                _, selected_node = max(boundary_candidates)
                assignments[selected_node] = domain_id
                changed = True
                continue

            fallback_candidates = [
                node_name
                for source_domain, domain_nodes in grouped_nodes.items()
                if source_domain != domain_id and len(domain_nodes) > minimum_domain_size
                for node_name in domain_nodes
                if node_name != domain_to_seed.get(source_domain)
            ]
            if fallback_candidates:
                selected_node = sorted(
                    fallback_candidates,
                    key=lambda node_name: (-len(adjacency[node_name]), assignments[node_name], node_name),
                )[0]
                assignments[selected_node] = domain_id
                changed = True

        if not changed:
            return assignments


def select_role_nodes(
    domain_nodes: list[str],
    adjacency: dict[str, set[str]],
    controller_node: str,
    producers_per_domain: int,
    ingress_candidates_per_domain: int,
) -> tuple[set[str], set[str]]:
    degrees = {node: len(adjacency[node]) for node in domain_nodes}
    producer_quota = min(max(1, producers_per_domain), max(1, len(domain_nodes) - 1))
    producers = [
        node
        for node in sorted(domain_nodes, key=lambda node: (-degrees[node], node))
        if node != controller_node
    ][:producer_quota]

    controller_distances = bfs_distances(adjacency, controller_node)
    ingress_quota = min(max(1, ingress_candidates_per_domain), max(1, len(domain_nodes) - 1 - len(producers)))
    ingress = [
        node
        for node in sorted(
            domain_nodes,
            key=lambda node: (-controller_distances.get(node, -1), -degrees[node], node),
        )
        if node != controller_node and node not in producers
    ][:ingress_quota]

    if not ingress:
        ingress = [node for node in domain_nodes if node != controller_node and node not in producers][:1]
    if not ingress:
        ingress = [node for node in domain_nodes if node != controller_node][:1]

    return set(producers), set(ingress)


def build_report(rows: list[dict[str, str]]) -> dict[str, object]:
    role_counts = Counter(row["role"] for row in rows)
    domain_summary: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        domain_summary[row["domain_id"]][row["role"]] += 1

    return {
        "rows_total": len(rows),
        "role_counts": dict(role_counts),
        "domains": {domain_id: dict(counts) for domain_id, counts in sorted(domain_summary.items())},
    }


def main() -> int:
    args = parse_args()
    topology_config = load_json_yaml(ROOT / args.topology_config)
    annotated_path = repo_root() / topology_config["annotated_topology_path"]
    if not annotated_path.exists():
        raise FileNotFoundError(f"annotated topology is missing: {annotated_path}")

    nodes, adjacency = parse_annotated_topology(annotated_path)
    domain_count = int(topology_config["domain_partition_policy"]["domains_total"])
    zones_per_domain = int(topology_config.get("zones_per_domain", 1))
    producers_per_domain = int(topology_config["producer_assignment_policy"]["producers_per_domain"])
    ingress_candidates_per_domain = int(topology_config["ingress_selection_policy"]["ingress_candidates_per_domain"])
    controller_prefix_template = f"/hiroute/{topology_config['topology_id']}/{{domain_id}}/controller"

    seeds = select_seeds(nodes, adjacency, domain_count)
    assignments, seed_to_domain = assign_domains(nodes, adjacency, seeds)
    assignments = rebalance_domains(
        adjacency,
        assignments,
        seed_to_domain,
        minimum_domain_size=3,
    )

    grouped_nodes: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        grouped_nodes[assignments[node]].append(node)

    rows = []
    for seed in seeds:
        domain_id = seed_to_domain[seed]
        domain_nodes = sorted(grouped_nodes[domain_id])
        producers, ingress = select_role_nodes(
            domain_nodes,
            adjacency,
            seed,
            producers_per_domain,
            ingress_candidates_per_domain,
        )
        producer_count = len(producers)

        for index, node_name in enumerate(domain_nodes, start=1):
            zone_id = f"{domain_id}-zone-{((index - 1) % zones_per_domain) + 1:02d}"
            role = "relay"
            if node_name == seed:
                role = "controller"
            elif node_name in ingress:
                role = "ingress"
            elif node_name in producers:
                role = "producer"

            rows.append(
                {
                    "node_id": node_name,
                    "role": role,
                    "domain_id": domain_id,
                    "zone_id": zone_id,
                    "controller_prefix": controller_prefix_template.format(domain_id=domain_id),
                    "producer_count": producer_count,
                }
            )

    output_path = repo_root() / (args.output if args.output else Path(topology_config["mapping_output_path"]))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_path,
        ["node_id", "role", "domain_id", "zone_id", "controller_prefix", "producer_count"],
        rows,
    )

    report_path = repo_root() / topology_config["report_output_path"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(build_report(rows), indent=2) + "\n", encoding="utf-8")

    print(f"generated {len(rows)} topology rows for {topology_config['topology_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
