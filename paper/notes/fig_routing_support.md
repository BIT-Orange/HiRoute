# Figure: fig_routing_support

## Paper binding

- figure number: Figure 4
- label: `fig:main`
- caption target: `Routing-support comparison among bounded distributed-discovery schemes. HiRoute reaches the first relevant domain most often (panel A) and uses the fewest discovery bytes per query (panel B), and is the only scheme that contracts the candidate frontier through hierarchical refinement (panel C). Dashed horizontal lines mark the centralized directory and unbounded flood as non-peer references.`

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

- Figure 4 compares HiRoute against the four distributed peers that respect the bounded inter-domain state contract: predicates_only, random_admissible, inf_tag_forwarding, hiroute. Within that cohort, HiRoute is best on every panel.
- Panel A (relevant-domain reach@1) at budget 16: hiroute 0.674, random_admissible 0.594, predicates_only 0.479, inf_tag_forwarding 0.368.
- Panel B (mean discovery bytes / query) at budget 16: hiroute 487, inf_tag_forwarding 528, random_admissible 626, predicates_only 626 — HiRoute lowest.
- Panel C (staged candidate contraction): only hiroute contracts (5.86 -> 4.39 -> 3.31 -> 3.31, 44% reduction across the hierarchy); the four distributed peers stay flat at 5.0.
- Central directory and flood appear as dashed horizontal reference lines because they violate the bounded distributed-discovery contract: central directory is a logically centralized oracle and flood is unrestricted parallel broadcast. They are references, not peers.
- Figure remains diagnostic until the routing runs are promoted from a clean tree and the figure validator passes the 240-query gate.
