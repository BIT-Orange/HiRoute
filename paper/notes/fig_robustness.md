# Figure: fig_robustness

## Purpose

- Compare service success and overhead under stale summaries and failure scenarios.

## Built from

- `results/aggregate/robustness_summary.csv`

## Promoted runs

- `exp_staleness_v1` and `exp_failures_v1` promoted runs.
- Latest `hiroute` robustness runs: `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_024922`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_025427`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_025513`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed1__20260313_025007`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed2__20260313_030937`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed3__20260313_031105`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed1__20260313_025053`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed2__20260313_031022`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed3__20260313_031150`

## Observations

- Under targeted stale-summary injection, `hiroute` drops to `0.641667` mean `success_at_1`, versus `0.733333` for `flat_iroute` and `0.575` for `oracle`.
- Under targeted link failure, `hiroute` drops to `0.591667` and incurs the highest latency (`493.966667 ms`), while `flood` and `flat_iroute` remain at `0.708333` and `0.7`.
- Under targeted domain failure, `hiroute` drops further to `0.441667`, below `flat_iroute` (`0.666667`), `flood` (`0.6`), and `oracle` (`0.575`).

## Caveats

- This figure now reflects a stronger, dominant-domain-targeted stress model rather than the earlier mild injections.
- The result should be read as a current implementation weakness: HiRoute is still too sensitive when a heavily demanded controller domain becomes stale or unavailable.
