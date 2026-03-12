# Baseline Definitions

## Exact-NDN

Uses only exact prefix naming. No semantic discovery, no hierarchical summaries, and no manifest
reply path. It is the strict lower bound for semantic resolution capability.

## Flood

Broadcast-style semantic discovery across admissible domains without hierarchical pruning. It
provides a high-recall, high-overhead comparison point.

## Flat iRoute

Semantic discovery without hierarchical refinement. It scores flat candidates directly and serves
as the primary non-hierarchical baseline.

## Oracle

Uses idealized global knowledge to select the best destination directly. It is an upper-bound
reference for success and overhead tradeoffs.

## HiRoute

Constraint-guided hierarchical discovery with manifest-based object resolution, reliability-aware
selection, and object-level evaluation.
