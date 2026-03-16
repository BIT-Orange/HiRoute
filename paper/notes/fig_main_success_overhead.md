# Figure: fig_main_success_overhead

## Purpose

Compare end-to-end service success against discovery overhead on `rf_3967_exodus`.

## Built from

- `results/aggregate/main_success_overhead.csv`

## Promoted runs

- Current promoted rows are the latest `exp_routing_main_v2` entries in `runs/registry/promoted_runs.csv`.
- The current `source_run_ids` in `results/aggregate/main_success_overhead.csv` point to the `20260316_111715` and `20260316_111716` reruns on commit `c4e7cfc`.

## Observations

- On the topology-consistent `routing_hard` workload, `oracle` remains the centralized upper reference at `1.0` `ServiceSuccess@1`, `116.966667` discovery bytes/query, and `121.533333 ms` mean latency.
- After enforcing shared manifest fallback and full-query completion, the distributed schemes all reach near-perfect success on this workload. The remaining signal is discovery cost: `flat_iroute` and `inf_tag_forwarding` stay at `1.0` success but cost about `386.291667` discovery bytes/query and `2.8625` remote probes/query.
- `hiroute` now forms the useful budget frontier: at budget `8` it reaches `1.0` success with `332.033333` bytes/query, and by budget `64` it still reaches `1.0` success while dropping to `261.3625` bytes/query and `1.620833` probes/query. This is materially lower overhead than the flat and INF-style baselines, but it is not a large success-gap result anymore.
- `flood` also reaches `1.0` success on the current routing bundle at `255.975` bytes/query, so the paper-grade takeaway is now frontier shape rather than success separation.

## Caveats

- `exact` is intentionally excluded from the main semantic-discovery plot; it remains a syntactic known-name reference rather than a comparable semantic baseline.
- These values come from promoted ndnSIM runs on `rf_3967_exodus` filtered to `split=test` and `workload_tier=routing_hard` with query-bootstrap confidence intervals.
