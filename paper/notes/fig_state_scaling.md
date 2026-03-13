# Figure: fig_state_scaling

## Purpose

- Relate exported state growth to topology size and routing scale.

## Built from

- `results/aggregate/state_scaling_summary.csv`

## Promoted runs

- `exp_scaling_v1` promoted runs filtered by topology.
- Latest `hiroute` scaling runs: `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_021004`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_021355`, `exp_scaling_v1__hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_021743`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed1__20260313_021051`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed2__20260313_021440`, `exp_scaling_v1__hiroute__smartcity_v1__rf_1239_sprint__seed3__20260313_021827`

## Observations

- `hiroute` preserves `0.891667` mean `success_at_1` on both `rf_3967_exodus` and `rf_1239_sprint`.
- State and topology scale up from `79` nodes / `8` controllers to `315` nodes / `16` controllers, while `hiroute` latency rises from `230.433333 ms` to `335.483333 ms`.
- `flat_iroute` stays at `0.8` success on both topologies, and `oracle` stays at `0.575`.

## Caveats

- The current scaling figure measures the configured state export size and topology expansion, not additional object-count sweeps.
