# Figure: fig_candidate_shrinkage

## Paper binding

- figure number: Figure 6
- label: `fig:shrinkage`
- caption target: `Diagnostic candidate contraction under hierarchical filtering and refinement.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/candidate_shrinkage.csv`
- trace json: `results/aggregate/mainline/candidate_shrinkage.trace.json`
- figure assets: `results/figures/mainline/fig_candidate_shrinkage.pdf` and `results/figures/mainline/fig_candidate_shrinkage.png`
- source experiment: `routing_main`

## Validation status

- aggregate traceability: current routing_main traceability passes after filtering staged search traces to query IDs present in `query_log.csv`
- figure binding: still blocked by the routing_main promoted-run validation failure

## Status

- diagnostic/blocking until routing query-count, figure-binding, and clean-promotion gates pass

## Interpretation

- This is a mechanism-support figure paired with `fig_routing_support`.
- The mainline rerun confirmed non-empty `zone_constraint` and preserved `2/3/4` domain-count support.
- Candidate shrinkage traces are populated and traceable in the current diagnostic aggregate, but they remain support evidence. They help explain HiRoute's stronger first relevant-domain reach and lower probe count versus INF-style tag forwarding; they do not prove universally lower byte or latency cost.
