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

- runtime slice: `review_artifacts/routing_main/validation/routing_main_validate_runtime_slice.txt`
- aggregate traceability: `review_artifacts/routing_main/validation/routing_main_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/routing_main/validation/routing_main_validate_figures.txt`

## Status

- diagnostic/support figure only

## Interpretation

- This figure is support evidence for the reach-versus-latency tradeoff in the routing-support workload.
- It should be interpreted together with first relevant-domain reach and discovery cost, not as an independent superiority result.
- The paper-facing role of the right panel is diagnostic readability, which is why the bar chart is rendered horizontally to keep the deadline labels legible.
