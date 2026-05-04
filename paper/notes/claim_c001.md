# Claim C-001

## Text

On the active `smartcity` `routing_main` workload, HiRoute is interpreted as a diagnostic
routing-support method rather than as a saturated end-to-end success claim. The current local
budget-16 aggregate supports the narrow statement that HiRoute reaches a relevant domain more
often than the distributed routing controls and uses fewer probes/bytes than the INF-style tag
forwarding baseline. It does not support a blanket lower-cost claim against every control:
`flood`, `predicates_only`, `random_admissible`, and the non-peer `central_directory` reference
all have lower discovery-byte values in the current local slice.

## Supported by

- `results/figures/mainline/fig_routing_support.pdf`

## Aggregates

- `results/aggregate/mainline/routing_support.csv`
- `results/aggregate/mainline/candidate_shrinkage.csv`

## Source runs

- Diagnostic scoped run IDs in `review_artifacts/routing_main/run_ids.txt`
- Current promoted-run figure gates still fail because several routing rows are below the
  240-query threshold.

## Status

diagnostic/blocking until the routing query-count and clean-promotion gates pass
