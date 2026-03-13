# Figure: fig_state_scaling

## Purpose

- Validate the paper's control-plane claim that exported state tracks the fixed summary budget more than local object population.

## Built from

- `results/aggregate/state_scaling_summary.csv`

## Promoted runs

- `exp_scaling_v1` promoted runs filtered by topology.
- Latest `hiroute` scaling runs: `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_063946`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_064030`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_064114`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed1__20260313_065309`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed2__20260313_065607`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed3__20260313_065903`

## Observations

- Under a fixed export budget of `16`, the total exported summaries stay flat at `128` while objects per domain grow from about `23` to `92`.
- The domain-count sweep is now linear in the expected way: `32 -> 64 -> 96 -> 128` exported summaries for `2 -> 4 -> 6 -> 8` active domains.
- `hiroute` keeps high end-to-end success during the scaling experiment on both topologies (`0.96875` on `rf_3967_exodus`, `0.984375` on `rf_1239_sprint`) even though Figure 8 itself is about control-plane state.

## Caveats

- The current dataset activates eight application domains on both topologies, so the large-topology advantage in Figure 8 comes from network size rather than additional active data domains.
