# Figure: fig_state_scaling

## Purpose

- Validate the paper's control-plane claim that exported state tracks the fixed summary budget more than local object population.

## Built from

- `results/aggregate/state_scaling_summary.csv`

## Promoted runs

- `exp_scaling_v1` promoted runs filtered by topology.
- Latest `hiroute` scaling runs: `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_084457`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_084500`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_084502`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed1__20260313_084504`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed2__20260313_084509`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed3__20260313_084514`

## Observations

- Under a fixed export budget of `16`, the total exported summaries stay flat while objects per domain grow from about `23` to `92`: `128` summaries on `rf_3967_exodus` and `256` summaries on `rf_1239_sprint`.
- The domain-count sweep is now topology-correct: `rf_3967_exodus` grows `32 -> 64 -> 96 -> 128` over `2 -> 4 -> 6 -> 8` domains, while `rf_1239_sprint` grows `64 -> 128 -> 192 -> 256` over `4 -> 8 -> 12 -> 16` domains.
- The large Rocketfuel topology now exposes a denser data plane rather than just a larger router graph, which is the key missing behavior from the previous audit.

## Caveats

- This scenario is intentionally state-only after the latest alignment pass, so the query-side columns in `state_scaling_summary.csv` are placeholders and should not be cited as end-to-end success results.
