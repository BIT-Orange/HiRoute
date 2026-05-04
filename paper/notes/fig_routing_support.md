# Figure: fig_routing_support

## Paper binding

- figure number: Figure 4
- label: `fig:main`
- caption target: `Diagnostic routing-support evaluation showing first relevant-domain reach, discovery cost, and staged candidate contraction under non-empty zone constraints.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/routing_support.csv`
- companion aggregate csv: `results/aggregate/mainline/candidate_shrinkage.csv`
- trace json: `results/aggregate/mainline/routing_support.trace.json`
- figure assets: `results/figures/mainline/fig_routing_support.pdf` and `results/figures/mainline/fig_routing_support.png`
- source experiment: `routing_main`

## Validation status

- aggregate traceability: current `tools/validate_aggregate_traceability.py --registry-source runs --run-ids-file review_artifacts/routing_main/run_ids.txt` passes for `routing_support.csv`, `candidate_shrinkage.csv`, and `deadline_summary.csv`
- figure binding: current `tools/validate_figures.py` fails against `promoted_runs.csv` because the promoted routing_main run directories are stale/missing or below the configured 240-query threshold

## Status

- diagnostic/blocking until routing query-count, figure-binding, and clean-promotion gates pass

## Interpretation

- Figure 4 is a routing-support figure rather than the paper's main end-to-end claim. It remains diagnostic until the routing runs are promoted from a clean tree and the figure validator passes.
- Its intended reading is limited to first relevant-domain reach, candidate narrowing, remote probes, and discovery bytes under non-empty zone constraints.
- If terminal success is saturated across several schemes, that is not a problem for this figure as long as the support-side reach and candidate-contraction panels still separate the hierarchical pipeline from flatter or random controls.
- The paper text should therefore avoid any phrasing that implies a fresh terminal-success win on this workload.
- Current budget-16 data supports a first relevant-domain reach claim for HiRoute and a lower-byte claim versus INF-style tag forwarding, but it does not support a blanket lower-byte claim across all controls.
