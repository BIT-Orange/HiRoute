# Baseline Definitions

## Exact-NDN

Uses only exact prefix naming. No semantic discovery, no hierarchical summaries, and no manifest
reply path. It is a syntactic reference showing the lower bound when the canonical name is already
known, and it should not be treated as a comparable semantic-discovery baseline in the main
Pareto-style figures.

## Flood

Broadcast-style semantic discovery across admissible domains without hierarchical pruning. It
provides a high-recall, high-overhead comparison point.

## Flat iRoute

Semantic discovery without hierarchical refinement. It scores flat candidates directly and serves
as the primary non-hierarchical baseline.

## INF-Style Tag Forwarding

Approximates a semantic-tag forwarding design using service, zone-type, freshness, and
intent-facet tags to rank domain controllers. It does not use hierarchical refinement and it
shares the same controller-local resolver as the other distributed baselines so that the comparison
isolates cross-domain discovery policy rather than domain-local ranking.

## Predicates Only

Applies the same hard predicate admissibility filter as \sysname{} but removes both flat semantic
scoring and hierarchical refinement. It routes to the cheapest admissible controller path first,
using shortest-hop controller distance with deterministic lexical tie-breaks. This baseline answers
the question of what hard constraints alone already solve before any semantic ranking is allowed.

## Random Admissible

Applies the same admissibility filter as \sysname{} but then chooses among admissible controllers
with a deterministic random order keyed by query ID and run seed. It shares the same downstream
manifest and fallback path as the other distributed baselines, making it the negative control for
"admissible but nonsemantic" routing behavior.

## Oracle / Central Directory

Uses idealized global object knowledge to answer each query through a centralized semantic
directory. It is an upper-bound reference for discovery quality, not a decentralized overhead
comparison target.

## HiRoute

Constraint-guided hierarchical discovery with manifest-based object resolution, reliability-aware
selection, and object-level evaluation.
