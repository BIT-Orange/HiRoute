# Figure: fig_robustness

## Purpose

- Compare service success and overhead under stale summaries and failure scenarios.

## Built from

- `results/aggregate/robustness_summary.csv`

## Promoted runs

- `exp_staleness_v1` and `exp_failures_v1` promoted runs.
- Latest `hiroute` robustness runs: `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_022129`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_022216`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_022300`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed1__20260313_022344`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed2__20260313_022515`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed3__20260313_022643`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed1__20260313_022429`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed2__20260313_022559`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed3__20260313_022727`

## Observations

- Under the current stale-summary, link-failure, and domain-failure injections, `hiroute` retains `0.891667` mean `success_at_1`, compared with `0.8` for `flat_iroute`/`flood` and `0.575` for `oracle`.
- The figure now combines both source experiments into one promoted robustness summary with explicit scenario and variant labels.

## Caveats

- The configured failure injections are moderate. This figure does not yet explore cascading multi-domain outages.
