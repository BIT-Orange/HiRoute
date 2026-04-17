# Figure: fig_routing_support

## Paper binding

- figure number: Figure 5
- label: `fig:main`
- caption target: `Mainline routing-support figure showing first relevant-domain reach, discovery cost, and staged candidate shrinkage under non-empty zone constraints.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/routing_support.csv`
- companion aggregate csv: `results/aggregate/mainline/candidate_shrinkage.csv`
- trace json: `results/aggregate/mainline/routing_support.trace.json`
- figure assets: `results/figures/mainline/fig_routing_support.pdf` and `results/figures/mainline/fig_routing_support.png`
- source experiment: `routing_main`

## Validation status

- runtime slice: `review_artifacts/routing_main/validation/routing_main_validate_runtime_slice.txt`
- aggregate traceability: `review_artifacts/routing_main/validation/routing_main_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/routing_main/validation/routing_main_validate_figures.txt`

## Status

- support figure only

## Interpretation

- Figure 5 is a routing-support figure rather than the paper's main end-to-end claim.
- Its intended reading is limited to first relevant-domain reach, candidate narrowing, remote probes, and discovery bytes under non-empty zone constraints.
- If terminal success is saturated across several schemes, that is not a problem for this figure as long as the support-side reach and cost panels still separate the hierarchical pipeline from flatter or random controls.
- The paper text should therefore avoid any phrasing that implies a fresh terminal-success win on this workload.
