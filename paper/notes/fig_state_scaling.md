# Figure: fig_state_scaling

## Paper binding

- figure number: Figure 8
- label: `fig:state`
- caption target: `Bounded inter-domain state under per-domain object growth (left) and active-domain growth (right). Both bounded distributed-discovery schemes track the configured budget envelope; HiRoute provides the routing-side and contraction wins of Figures 4 and 6 under exactly this state envelope rather than at additional state cost.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/state_scaling_summary.csv`
- trace json: `results/aggregate/mainline/state_scaling_summary.trace.json`
- figure assets: `results/figures/mainline/fig_state_scaling.pdf` and `results/figures/mainline/fig_state_scaling.png`
- source experiment: `state_scaling`

## Validation status

- runtime slice: `review_artifacts/state_scaling/validation/state_scaling_validate_runtime_slice.txt`
- aggregate traceability: `review_artifacts/state_scaling/validation/state_scaling_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/state_scaling/validation/state_scaling_validate_figures.txt`

## Status

- semantically supportable state-only support figure on the large `rf_1239_sprint` topology, but blocked for final paper-facing readiness while the worktree is dirty

## Interpretation

- Figure 8 verifies Proposition 1: exported inter-domain state is bounded by `B_i × |D|` and does not grow with the local object population.
- Both bounded distributed-discovery schemes (HiRoute and INF-style tag forwarding) trace the configured budget × domain-count envelope (dashed gray line on the right panel). Per-domain object growth (left panel) leaves exported state flat.
- This is a two-axis statement, not a one-axis "HiRoute is best" comparison. HiRoute meets the same bounded-state contract as the strongest distributed peer AND delivers the routing-side and contraction wins of Figures 4 and 6 under exactly this envelope.
- Centralized directory and flood are excluded by construction: central directory carries unbounded directory state, flood does not maintain inter-domain state at all.
- Query-side fields are intentionally absent (`query_count=0`, success/latency/discovery-byte are `nan`). The paper must not use this figure to imply an end-to-end query-side success claim.
