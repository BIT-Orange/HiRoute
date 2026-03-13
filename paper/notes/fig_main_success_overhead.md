# Figure: fig_main_success_overhead

## Purpose

Compare end-to-end service success against discovery overhead on `rf_3967_exodus`.

## Built from

- `results/aggregate/main_success_overhead.csv`

## Promoted runs

- Current promoted rows are the latest `exp_main_v1` entries in `runs/registry/promoted_runs.csv`.
- The current `source_run_ids` in `results/aggregate/main_success_overhead.csv` point to the `20260313_120501` to `20260313_122901` filtered reruns on commit `55e2e2f`.

## Observations

- On the filtered `medium/high` ambiguity workload, `oracle` remains the intended centralized upper reference at `1.0` `ServiceSuccess@1` with `73.952381` discovery bytes/query.
- Among comparable distributed discovery schemes, `hiroute` reaches `0.857143` `ServiceSuccess@1`, substantially above `0.357143` for both `flood` and `flat_iroute`.
- The gain comes with higher discovery cost: `2.214286` remote probes/query and `251.5` discovery bytes/query for `hiroute`, compared with `0.952381` / `69.142857` for `flood` and `0.952381` / `86.285714` for `flat_iroute`.

## Caveats

- `exact` is intentionally excluded from the main semantic-discovery plot; it remains a syntactic known-name reference rather than a comparable semantic baseline.
- These values come from promoted ndnSIM runs on `rf_3967_exodus` filtered to `medium/high` ambiguity queries.
