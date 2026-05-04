# Figure: fig_candidate_shrinkage

## Paper binding

- figure number: Figure 6
- label: `fig:shrinkage`
- caption target: `Candidate-frontier contraction by scheme on the same routing-support slice. HiRoute is the only distributed scheme that contracts the frontier through level-0/level-1 refinement, ending at roughly half the candidate ratio of the next-best peer; the remote-probe panel (right) shows the corresponding probe-count consequence.`

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

- This is the structural figure backing the routing-support claims in fig_routing_support. It shows that HiRoute is the only distributed scheme on the current workload that genuinely contracts the candidate frontier through hierarchical refinement.
- Per the budget-16 candidate_shrinkage.csv: hiroute traces 1.00 (all_domains) -> 0.733 (admissible) -> 0.733 (level0) -> 0.549 (level1) -> 0.414 (refined) -> 0.414 (probed). The four other distributed peers stay at 0.733 from admissibility onward.
- The 44% reduction annotation in panel A is computed from the start (all_domains, ratio 1.0) to end (probed_cells, ratio 0.414).
- Central directory and flood are excluded from the waterfall because they violate the bounded distributed-discovery contract; they appear as references in fig_routing_support panel A and B but do not belong on this contraction comparison.
- Remote-probe panel: hiroute 2.99 probes per query at budget 16 vs inf_tag 3.56, predicates_only 3.10, random_admissible 3.02. The probe count is the operational consequence of the contraction.
- Diagnostic until the routing query-count and figure-binding gates pass under a clean promotion.
