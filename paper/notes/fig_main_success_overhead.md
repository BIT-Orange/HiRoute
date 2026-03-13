# Figure: fig_main_success_overhead

## Purpose

Compare end-to-end service success against discovery overhead on `rf_3967_exodus`.

## Built from

- `results/aggregate/main_success_overhead.csv`

## Promoted runs

- Current promoted rows are the latest `exp_main_v1` entries in `runs/registry/promoted_runs.csv`.
- The current `source_run_ids` in `results/aggregate/main_success_overhead.csv` point to the `20260313_111001` to `20260313_113901` reruns on commit `922a148`.

## Observations

- `oracle` now behaves as the intended centralized semantic directory upper reference: `1.0` `ServiceSuccess@1` with `81.47541` discovery bytes/query.
- Among comparable distributed discovery schemes, `hiroute` reaches `0.901639` `ServiceSuccess@1`, substantially above `0.557377` for both `flood` and `flat_iroute`.
- The gain comes with higher discovery cost: `1.770492` remote probes/query and `211.442623` discovery bytes/query for `hiroute`, compared with `0.967213` / `78.163934` for `flood` and `0.967213` / `95.57377` for `flat_iroute`.

## Caveats

- `exact` is intentionally excluded from the main semantic-discovery plot; it remains a syntactic known-name reference rather than a comparable semantic baseline.
- These values come from promoted ndnSIM runs on `rf_3967_exodus`, not the earlier mock pipeline.
