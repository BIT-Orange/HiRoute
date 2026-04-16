# Figure: fig_deadline_summary

## Paper binding

- figure number: Figure 7
- label: `fig:latency`
- caption target: `Deadline-sensitive latency evaluation.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/deadline_summary.csv`
- trace json: `results/aggregate/mainline/deadline_summary.trace.json`
- figure assets: `results/figures/mainline/fig_deadline_summary.pdf` and `results/figures/mainline/fig_deadline_summary.png`
- source experiment: `routing_main`

## Validation status

- runtime slice: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_runtime_slice.txt`)
- aggregate traceability: completed (`review_artifacts/object_ablation_routing/validation/routing_main_validate_aggregate_traceability.txt`)
- figure binding: blocked by routing headline failure (`review_artifacts/object_ablation_routing/validation/routing_main_validate_figures_routing_support.txt`)

## Status

- completed on 2026-03-31 mainline rerun, but blocked as supporting-only evidence

## Interpretation

- This figure is support evidence for the reach-versus-latency tradeoff in Figure 4.
- The current rerun collapses the latency curves to all-failure rows, so this figure is diagnostic evidence of routing failure rather than proof of superiority.
