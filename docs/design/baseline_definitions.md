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

## Oracle

Uses idealized global object knowledge to answer each query through a centralized semantic
directory. It is an upper-bound reference for discovery quality, not a decentralized overhead
comparison target.

## HiRoute

Constraint-guided hierarchical discovery with manifest-based object resolution, reliability-aware
selection, and object-level evaluation.
