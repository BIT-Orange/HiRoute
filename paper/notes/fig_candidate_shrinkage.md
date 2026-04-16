# Figure: fig_candidate_shrinkage

## Paper binding

- figure number: Figure 6
- label: `fig:shrinkage`
- caption target: `Candidate shrinkage under hierarchical filtering and refinement.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/candidate_shrinkage.csv`
- trace json: `results/aggregate/mainline/candidate_shrinkage.trace.json`
- figure assets: `results/figures/mainline/fig_candidate_shrinkage.pdf` and `results/figures/mainline/fig_candidate_shrinkage.png`
- source experiment: `routing_main`

## Validation status

- runtime slice: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_runtime_slice.txt`)
- aggregate traceability: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_aggregate_traceability.txt`)
- figure binding: blocked by routing headline failure (`review_artifacts/object_ablation_routing/validation/routing_main_validate_figures_routing_support.txt`)

## Status

- completed on 2026-03-31 mainline rerun, but blocked as supporting-only evidence

## Interpretation

- This is a mechanism-support figure paired with `fig_routing_support`.
- The mainline rerun confirmed non-empty `zone_constraint` and preserved `2/3/4` domain-count support.
- Candidate shrinkage traces are populated and traceable, but they cannot rescue Figure 4 as a paper headline while the routing-support aggregate remains fully degenerate on success and reach.
