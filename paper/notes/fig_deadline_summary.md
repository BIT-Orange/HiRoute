# Figure: fig_deadline_summary

## Paper binding

- figure number: Figure 7
- label: `fig:latency`
- caption target: `Diagnostic deadline-sensitive latency evaluation on the routing-support workload.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/deadline_summary.csv`
- trace json: `results/aggregate/mainline/deadline_summary.trace.json`
- figure assets: `results/figures/mainline/fig_deadline_summary.pdf` and `results/figures/mainline/fig_deadline_summary.png`
- source experiment: `routing_main`

## Validation status

- aggregate traceability: current routing_main traceability passes with the scoped run-id file
- figure binding: current `tools/validate_figures.py` fails against `promoted_runs.csv` because the promoted routing_main run directories are stale/missing or below the configured 240-query threshold

## Status

- diagnostic/blocking until routing query-count, figure-binding, and clean-promotion gates pass

## Interpretation

- This figure is diagnostic support evidence for the reach-versus-latency tradeoff in the routing-support workload until the routing promotion/figure gate is repaired.
- It should be interpreted together with first relevant-domain reach and discovery cost, not as an independent superiority result.
- The paper-facing role of the right panel is diagnostic readability, which is why the bar chart is rendered horizontally to keep the deadline labels legible.
- HiRoute inherits one additional structural controller-to-ingress round-trip per query (discovery reply, then object fetch), which is visible in the latency distribution. On the current routing-support slice this produces `mean_latency_ms=612.475` for hiroute versus `661.459` for inf_tag_forwarding and `83.700` for central_directory. The deadline panel should be read with this structural RTT cost and the non-peer centralized reference in mind, and the paper should not describe hiroute as having a universal latency advantage on this workload.
