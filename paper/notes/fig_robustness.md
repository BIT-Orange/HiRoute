# Figure: fig_robustness

## Purpose

- Measure HiRoute's service success and overhead under stale summaries, link failures, and domain failures.

## Built from

- `results/aggregate/robustness_summary.csv`

## Promoted runs

- `exp_staleness_v1` and `exp_failures_v1` promoted runs.
- Latest `hiroute` robustness runs: `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_084545`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_084629`, `exp_staleness_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_084713`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed1__20260313_084814`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed2__20260313_084858`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__link__seed3__20260313_084942`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed1__20260313_085025`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed2__20260313_085110`, `exp_failures_v1__hiroute__smartcity_v1__rf_3967_exodus__domain__seed3__20260313_085154`

## Observations

- Under targeted stale-summary injection, the repaired `hiroute` path now holds `0.868852` mean `success_at_1` with `307.180328 ms` mean latency.
- Under targeted link failure, `hiroute` holds `0.803279` mean `success_at_1`, materially above the previous pre-fix `0.591667` level.
- Under targeted domain failure, `hiroute` still degrades the most, but it recovers to `0.688525` mean `success_at_1` instead of the earlier `0.441667`.

## Caveats

- This figure now reflects a stronger, dominant-domain-targeted stress model rather than the earlier mild injections.
- Domain failure is still the harshest case, so the result should be read as a repaired but not yet final robustness profile.
