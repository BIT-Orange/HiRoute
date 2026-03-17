"""Build Rocketfuel-derived topology mappings and compact topology variants for HiRoute."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from heapq import heappop, heappush
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.workflow_support import load_json_yaml, read_csv, repo_root, write_csv


@dataclass(frozen=True)
class NodeRecord:
    node_id: str
    comment: str
    y_pos: float
    x_pos: float


@dataclass(frozen=True)
class EdgeRecord:
    src: str
    dst: str
    bandwidth_raw: str
    bandwidth_mbps: float
    metric: int
    delay_ms: float
    queue: int

    def key(self) -> tuple[str, str]:
        return tuple(sorted((self.src, self.dst)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--topology-config",
        default="configs/topologies/rocketfuel_3967_exodus.yaml",
        type=Path,
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _parse_bandwidth_mbps(raw: str) -> float:
    token = raw.strip()
    if token.endswith("Gbps"):
        return float(token[:-4]) * 1000.0
    if token.endswith("Mbps"):
        return float(token[:-4])
    if token.endswith("Kbps"):
        return float(token[:-4]) / 1000.0
    return float(token)


def _format_bandwidth_mbps(value: float) -> str:
    if value >= 1000 and math.isclose(value % 1000, 0.0, abs_tol=1e-9):
        return f"{int(round(value / 1000.0))}Gbps"
    if math.isclose(value, round(value), abs_tol=1e-9):
        return f"{int(round(value))}Mbps"
    return f"{value:.3f}Mbps".rstrip("0").rstrip(".")


def _format_delay_ms(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-9):
        return f"{int(round(value))}ms"
    return f"{value:.3f}ms".rstrip("0").rstrip(".")


def parse_annotated_topology(
    path: Path,
) -> tuple[dict[str, NodeRecord], dict[tuple[str, str], EdgeRecord], dict[str, set[str]]]:
    nodes: dict[str, NodeRecord] = {}
    edges: dict[tuple[str, str], EdgeRecord] = {}
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
                node_id = parts[0]
                comment = parts[1] if len(parts) > 1 else "NA"
                y_pos = float(parts[2]) if len(parts) > 2 else 0.0
                x_pos = float(parts[3]) if len(parts) > 3 else 0.0
                nodes[node_id] = NodeRecord(node_id=node_id, comment=comment, y_pos=y_pos, x_pos=x_pos)
                adjacency.setdefault(node_id, set())
                continue
            if section != "link":
                continue

            src = parts[0]
            dst = parts[1]
            bandwidth_raw = parts[2]
            metric = int(parts[3]) if len(parts) > 3 else 1
            delay_token = parts[4] if len(parts) > 4 else "1ms"
            queue = int(parts[5]) if len(parts) > 5 else 100
            delay_ms = float(delay_token[:-2]) if delay_token.endswith("ms") else float(delay_token)
            edge = EdgeRecord(
                src=src,
                dst=dst,
                bandwidth_raw=bandwidth_raw,
                bandwidth_mbps=_parse_bandwidth_mbps(bandwidth_raw),
                metric=metric,
                delay_ms=delay_ms,
                queue=queue,
            )
            edges[edge.key()] = edge
            adjacency[src].add(dst)
            adjacency[dst].add(src)

    return nodes, edges, {node_id: set(sorted(neighbors)) for node_id, neighbors in adjacency.items()}


def write_annotated_topology(
    path: Path,
    nodes: dict[str, NodeRecord],
    edges: dict[tuple[str, str], EdgeRecord],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# any empty lines and lines starting with '#' symbol is ignored",
        "",
        "# The file should contain exactly two sections: router and link, each starting with the corresponding keyword",
        "",
        "router",
        "",
        "# node  comment     yPos    xPos",
    ]
    for node_id in sorted(nodes):
        node = nodes[node_id]
        lines.append(f"{node.node_id}\t{node.comment}\t{node.y_pos:g}\t{node.x_pos:g}")
    lines.extend(
        [
            "",
            "link",
            "",
            "# src  dst  bandwidth  metric  delay  queue",
        ]
    )
    for src, dst in sorted(edges):
        edge = edges[(src, dst)]
        lines.append(
            f"{src}\t{dst}\t{edge.bandwidth_raw}\t{edge.metric}\t{_format_delay_ms(edge.delay_ms)}\t{edge.queue}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_graphviz(
    path: Path,
    nodes: dict[str, NodeRecord],
    edges: dict[tuple[str, str], EdgeRecord],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["graph topology {"]
    for node_id in sorted(nodes):
        node = nodes[node_id]
        label = node.node_id.replace('"', '\\"')
        lines.append(f'  "{node.node_id}" [label="{label}"];')
    for src, dst in sorted(edges):
        edge = edges[(src, dst)]
        label = f"{edge.metric}/{edge.delay_ms:g}ms"
        lines.append(f'  "{src}" -- "{dst}" [label="{label}"];')
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _load_source_mapping(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    if not rows:
        raise ValueError(f"source mapping is empty: {path}")
    return rows


def _adjacency_from_edges(edges: dict[tuple[str, str], EdgeRecord]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    for src, dst in edges:
        adjacency[src].add(dst)
        adjacency[dst].add(src)
    return {node_id: set(sorted(neighbors)) for node_id, neighbors in adjacency.items()}


def _lexicographic_shortest_path(
    start: str,
    goal: str,
    adjacency: dict[str, set[str]],
    edges: dict[tuple[str, str], EdgeRecord],
) -> list[str]:
    heap: list[tuple[tuple[int, float, int], str]] = [((0, 0.0, 0), start)]
    costs: dict[str, tuple[int, float, int]] = {start: (0, 0.0, 0)}
    parents: dict[str, str | None] = {start: None}

    while heap:
        cost, node = heappop(heap)
        if node == goal:
            break
        if cost != costs.get(node):
            continue
        for neighbor in sorted(adjacency[node]):
            edge = edges[tuple(sorted((node, neighbor)))]
            next_cost = (
                cost[0] + edge.metric,
                cost[1] + edge.delay_ms,
                cost[2] + 1,
            )
            if neighbor not in costs or next_cost < costs[neighbor]:
                costs[neighbor] = next_cost
                parents[neighbor] = node
                heappush(heap, (next_cost, neighbor))

    if goal not in parents:
        raise ValueError(f"no path between {start} and {goal}")

    path = [goal]
    current = goal
    while parents[current] is not None:
        current = parents[current]  # type: ignore[assignment]
        path.append(current)
    path.reverse()
    return path


def _retain_producers(
    domain_rows: list[dict[str, str]],
    adjacency: dict[str, set[str]],
    keep_per_domain: int,
) -> list[dict[str, str]]:
    producers = [row for row in domain_rows if row["role"] == "producer"]
    if len(producers) <= keep_per_domain:
        return producers
    return sorted(
        producers,
        key=lambda row: (-len(adjacency.get(row["node_id"], set())), row["node_id"]),
    )[:keep_per_domain]


def _build_compact_mapping_rows(
    compact_nodes: set[str],
    source_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    rows = [row for row in source_rows if row["node_id"] in compact_nodes]
    rows.sort(key=lambda row: (row["domain_id"], row["role"], row["node_id"]))
    return rows


def _compress_degree_two_relays(
    nodes: dict[str, NodeRecord],
    edges: dict[tuple[str, str], EdgeRecord],
    retained_terminals: set[str],
    compact_mapping_rows: list[dict[str, str]],
) -> tuple[dict[str, NodeRecord], dict[tuple[str, str], EdgeRecord], int]:
    adjacency = _adjacency_from_edges(edges)
    roles_by_node = {row["node_id"]: row["role"] for row in compact_mapping_rows}

    def compressible(node_id: str) -> bool:
        return (
            node_id not in retained_terminals
            and roles_by_node.get(node_id, "relay") == "relay"
            and len(adjacency.get(node_id, set())) == 2
        )

    kept_nodes = {
        node_id
        for node_id in adjacency
        if not compressible(node_id)
    }
    new_edges: dict[tuple[str, str], EdgeRecord] = {}
    consumed_paths: set[tuple[str, str]] = set()
    chains_compressed = 0

    def register_edge(src: str, dst: str, path_edges: list[EdgeRecord]) -> None:
        nonlocal chains_compressed
        ordered = tuple(sorted((src, dst)))
        bandwidth_mbps = min(edge.bandwidth_mbps for edge in path_edges)
        metric = sum(edge.metric for edge in path_edges)
        delay_ms = sum(edge.delay_ms for edge in path_edges)
        queue = min(edge.queue for edge in path_edges)
        candidate = EdgeRecord(
            src=ordered[0],
            dst=ordered[1],
            bandwidth_raw=_format_bandwidth_mbps(bandwidth_mbps),
            bandwidth_mbps=bandwidth_mbps,
            metric=metric,
            delay_ms=delay_ms,
            queue=queue,
        )
        existing = new_edges.get(ordered)
        if existing is None or (candidate.metric, candidate.delay_ms) < (existing.metric, existing.delay_ms):
            new_edges[ordered] = candidate
        if len(path_edges) > 1:
            chains_compressed += 1

    for anchor in sorted(kept_nodes):
        for neighbor in sorted(adjacency[anchor]):
            undirected = tuple(sorted((anchor, neighbor)))
            if undirected in consumed_paths:
                continue
            path_nodes = [anchor, neighbor]
            path_edges = [edges[undirected]]
            prev = anchor
            current = neighbor
            while compressible(current):
                next_candidates = sorted(candidate for candidate in adjacency[current] if candidate != prev)
                if not next_candidates:
                    break
                nxt = next_candidates[0]
                path_nodes.append(nxt)
                path_edges.append(edges[tuple(sorted((current, nxt)))])
                consumed_paths.add(tuple(sorted((prev, current))))
                prev, current = current, nxt
            consumed_paths.add(tuple(sorted((path_nodes[-2], path_nodes[-1]))))
            register_edge(path_nodes[0], path_nodes[-1], path_edges)

    compact_nodes = {node_id: nodes[node_id] for node_id in sorted(kept_nodes)}
    for src, dst in new_edges:
        compact_nodes.setdefault(src, nodes[src])
        compact_nodes.setdefault(dst, nodes[dst])
    return compact_nodes, new_edges, chains_compressed


def build_compact_topology(topology_config: dict[str, object]) -> tuple[list[dict[str, str]], dict[str, object]]:
    source_topology_config_path = ROOT / Path(str(topology_config["source_topology_config"]))
    source_topology_config = load_json_yaml(source_topology_config_path)
    source_topology_path = repo_root() / Path(str(source_topology_config["annotated_topology_path"]))
    source_mapping_path = repo_root() / Path(str(topology_config["source_mapping_csv"]))
    if not source_topology_path.exists():
        raise FileNotFoundError(f"source annotated topology is missing: {source_topology_path}")
    if not source_mapping_path.exists():
        raise FileNotFoundError(f"source mapping is missing: {source_mapping_path}")

    nodes, edges, adjacency = parse_annotated_topology(source_topology_path)
    source_rows = _load_source_mapping(source_mapping_path)
    rows_by_domain: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        rows_by_domain[row["domain_id"]].append(row)

    compact_policy = topology_config.get("compact_policy", {})
    if not isinstance(compact_policy, dict):
        raise ValueError("compact_policy must be an object")
    keep_producers_per_domain = int(compact_policy.get("keep_producers_per_domain", 2))

    retained_rows: list[dict[str, str]] = []
    for domain_id in sorted(rows_by_domain):
        domain_rows = rows_by_domain[domain_id]
        controllers = sorted(
            [row for row in domain_rows if row["role"] == "controller"],
            key=lambda row: row["node_id"],
        )
        ingresses = sorted(
            [row for row in domain_rows if row["role"] == "ingress"],
            key=lambda row: row["node_id"],
        )
        producers = _retain_producers(domain_rows, adjacency, keep_producers_per_domain)
        retained_rows.extend(controllers)
        retained_rows.extend(ingresses)
        retained_rows.extend(producers)

    retained_terminals = {row["node_id"] for row in retained_rows}
    terminal_list = sorted(retained_terminals)
    edge_union: set[tuple[str, str]] = set()
    for index, start in enumerate(terminal_list):
        for goal in terminal_list[index + 1 :]:
            path = _lexicographic_shortest_path(start, goal, adjacency, edges)
            for src, dst in zip(path, path[1:]):
                edge_union.add(tuple(sorted((src, dst))))

    compact_edge_map = {key: edges[key] for key in sorted(edge_union)}
    compact_node_ids = set(retained_terminals)
    for src, dst in compact_edge_map:
        compact_node_ids.add(src)
        compact_node_ids.add(dst)
    compact_nodes = {node_id: nodes[node_id] for node_id in sorted(compact_node_ids)}

    compact_mapping_rows = _build_compact_mapping_rows(compact_node_ids, source_rows)
    compressed_nodes, compressed_edges, chains_compressed = _compress_degree_two_relays(
        compact_nodes,
        compact_edge_map,
        retained_terminals,
        compact_mapping_rows,
    )
    compact_mapping_rows = _build_compact_mapping_rows(set(compressed_nodes), source_rows)

    annotated_path = repo_root() / Path(str(topology_config["annotated_topology_path"]))
    graphviz_path = repo_root() / Path(str(topology_config["graphviz_path"]))
    write_annotated_topology(annotated_path, compressed_nodes, compressed_edges)
    write_graphviz(graphviz_path, compressed_nodes, compressed_edges)

    report = {
        "source_topology_id": source_topology_config["topology_id"],
        "topology_id": topology_config["topology_id"],
        "source_nodes_total": len(nodes),
        "compact_nodes_total": len(compressed_nodes),
        "source_links_total": len(edges),
        "compact_links_total": len(compressed_edges),
        "domains_preserved": sorted({row["domain_id"] for row in compact_mapping_rows}),
        "controllers_retained": sum(1 for row in compact_mapping_rows if row["role"] == "controller"),
        "ingresses_retained": sum(1 for row in compact_mapping_rows if row["role"] == "ingress"),
        "producers_retained": sum(1 for row in compact_mapping_rows if row["role"] == "producer"),
        "relays_retained": sum(1 for row in compact_mapping_rows if row["role"] == "relay"),
        "chains_compressed": chains_compressed,
        "role_counts": dict(Counter(row["role"] for row in compact_mapping_rows)),
    }
    return compact_mapping_rows, report


def build_standard_mapping(topology_config: dict[str, object]) -> tuple[list[dict[str, str]], dict[str, object]]:
    annotated_path = repo_root() / Path(str(topology_config["annotated_topology_path"]))
    if not annotated_path.exists():
        raise FileNotFoundError(f"annotated topology is missing: {annotated_path}")

    nodes, _, adjacency = parse_annotated_topology(annotated_path)
    node_names = sorted(nodes)
    domain_count = int(topology_config["domain_partition_policy"]["domains_total"])
    zones_per_domain = int(topology_config.get("zones_per_domain", 1))
    producers_per_domain = int(topology_config["producer_assignment_policy"]["producers_per_domain"])
    ingress_candidates_per_domain = int(topology_config["ingress_selection_policy"]["ingress_candidates_per_domain"])
    controller_prefix_template = f"/hiroute/{topology_config['topology_id']}" + "/{domain_id}/controller"

    seeds = select_seeds(node_names, adjacency, domain_count)
    assignments, seed_to_domain = assign_domains(node_names, adjacency, seeds)
    assignments = rebalance_domains(adjacency, assignments, seed_to_domain, minimum_domain_size=3)

    grouped_nodes: dict[str, list[str]] = defaultdict(list)
    for node_name in node_names:
        grouped_nodes[assignments[node_name]].append(node_name)

    rows: list[dict[str, str]] = []
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
    return rows, build_report(rows)


def main() -> int:
    args = parse_args()
    topology_config = load_json_yaml(ROOT / args.topology_config)
    mode = topology_config.get("mode", "partition_from_annotated_topology")

    if mode == "compact_from_source_mapping":
        rows, report = build_compact_topology(topology_config)
    else:
        rows, report = build_standard_mapping(topology_config)

    output_path = repo_root() / (args.output if args.output else Path(str(topology_config["mapping_output_path"])))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_path,
        ["node_id", "role", "domain_id", "zone_id", "controller_prefix", "producer_count"],
        rows,
    )

    report_path = repo_root() / Path(str(topology_config["report_output_path"]))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"generated {len(rows)} topology rows for {topology_config['topology_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
