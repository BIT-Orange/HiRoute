# Figure: fig_routing_support

## Paper binding

- figure number: Figure 4
- label: `fig:main`
- caption target: `Mainline routing-support figure showing first relevant-domain reach, discovery cost, and staged candidate shrinkage under non-empty zone constraints.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/routing_support.csv`
- companion aggregate csv: `results/aggregate/mainline/candidate_shrinkage.csv`
- trace json: `results/aggregate/mainline/routing_support.trace.json`
- figure assets: `results/figures/mainline/fig_routing_support.pdf` and `results/figures/mainline/fig_routing_support.png`
- source experiment: `routing_main`

## Validation status

- runtime slice: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_runtime_slice.txt`)
- aggregate traceability: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_aggregate_traceability.txt`)
- figure binding: failed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_figures_routing_support.txt`)

## Status

- completed on 2026-03-31 mainline rerun, but blocked for paper-headline use

## Interpretation

- Figure 4 is a support figure, not the primary end-to-end superiority claim.
- The fresh rerun satisfies the workload preconditions: runtime `zone_constraint` coverage is `1.0` and relevant-domain support covers `2/3/4`.
- The current result does not support a positive routing claim: all promoted schemes remain at `mean_success_at_1=0.0`, `mean_manifest_hit_at_5=0.0`, and the headline reach metrics collapse to `nan`/degenerate values.
- `validate_figures.py` blocked the figure because multiple distributed controls remain degenerate on all routing headline metrics, so the figure can be reviewed as diagnostic evidence only.
