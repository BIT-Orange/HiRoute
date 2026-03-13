# Figure: fig_main_success_overhead

## Purpose

Compare end-to-end service success against discovery overhead on `rf_3967_exodus`.

## Built from

- `results/aggregate/main_success_overhead.csv`

## Promoted runs

- Current promoted rows are the latest `exp_main_v1` entries in `runs/registry/promoted_runs.csv`.
- Latest `hiroute` runs: `exp_main_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_062613`, `exp_main_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_062657`, `exp_main_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_062741`, `exp_main_v1__hiroute__smartcity_v1__rf_3967_exodus__seed4__20260313_062825`, `exp_main_v1__hiroute__smartcity_v1__rf_3967_exodus__seed5__20260313_062910`
- Full per-scheme run lists are captured in the `source_run_ids` column of `results/aggregate/main_success_overhead.csv`.

## Observations

- `hiroute` now reaches `0.991667` object-level success on `rf_3967_exodus`, substantially above `0.8` for both `flood` and `flat_iroute`.
- The gain still comes with higher discovery cost: `1.475` remote probes/query and `183.275` discovery bytes/query for `hiroute`, compared with `1.225` / `106.841667` for `flood` and `1.008333` / `104.725` for `flat_iroute`.
- `exact` remains the name-known lower bound at `1.0` success and zero discovery bytes; `oracle` remains below `hiroute` at `0.575` success because it skips hierarchical constraint-guided refinement.

## Caveats

- These values come from promoted ndnSIM runs on `rf_3967_exodus`, not the earlier mock pipeline.
- The main tradeoff is success vs discovery overhead, not lower latency than all baselines.
