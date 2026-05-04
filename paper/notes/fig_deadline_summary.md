# Figure: fig_deadline_summary

## Paper binding

- figure number: Figure 7
- label: `fig:latency`
- caption target: `Deadline-sensitive evaluation. Panel A plots absolute deadline success against the deadline (centralized directory and flood are dashed non-peer references). Panel B reports the deadline-success per kilobyte of discovery traffic, restricted to the bounded distributed-discovery cohort: HiRoute is the most byte-efficient scheme at every reported deadline.`

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

- Figure 7 is a tradeoff diagnostic, not a universal latency claim. Panel A reports absolute success-within-deadline; panel B reports deadline-success per kilobyte of discovery traffic for the bounded distributed-discovery cohort only.
- Absolute deadline success (panel A) is dominated by central_directory and flood for structural reasons that the bounded distributed-discovery cohort does not benefit from: central_directory uses a single one-hop lookup, and flood broadcasts in parallel. They are dashed reference lines.
- Per-byte efficiency (panel B) is the panel where HiRoute is visibly best. Computed from the current diagnostic snapshot at budget 16: at 100 ms, hiroute 0.000313 success/byte vs random 0.000235, predicates_only 0.000164, inf_tag_forwarding 0.000204; at 200 ms, hiroute 0.000565 vs random 0.000385, predicates 0.000266, inf_tag 0.000302; at 500 ms, hiroute 0.000922 vs random 0.000685, predicates 0.000771, inf_tag 0.000720.
- HiRoute inherits one additional structural controller-to-ingress round-trip per query relative to the centralized directory, so on the current workload its mean latency is 612 ms vs 84 ms for central_directory and 661 ms for INF-style tag forwarding. The figure should not be used to claim a universal latency advantage; it shows a byte-cost-normalized advantage within the cohort that respects the bounded-state contract.
- Diagnostic until the routing query-count and figure-binding gates pass under a clean promotion.
