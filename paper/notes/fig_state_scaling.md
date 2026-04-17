# Figure: fig_state_scaling

## Paper binding

- figure number: Figure 8
- label: `fig:state`
- caption target: `Routing-state scaling under fixed-budget object-density and active-domain sweeps.`

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

- state-only support figure on the large `rf_1239_sprint` topology

## Interpretation

- Figure 8 validates the bounded-state claim and nothing more.
- The left panel should be read as a fixed-budget object-density sweep. The right panel should be read as the active-domain sweep on the larger topology, not as another compact-routing panel.
- Query-side fields are intentionally absent from this experiment. The paper should not use this figure to imply any end-to-end success claim.
