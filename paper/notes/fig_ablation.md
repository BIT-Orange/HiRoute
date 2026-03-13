# Figure: fig_ablation

## Purpose

- Summarize component-level tradeoffs across the current comparison set.

## Built from

- `results/aggregate/ablation_summary.csv`

## Promoted runs

- Current `exp_ablation_v1` promoted runs.
- Latest `full_hiroute` runs: `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_022826`, `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_022912`, `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_022956`

## Observations

- `full_hiroute` is the highest-success ablation at `0.891667`, ahead of `predicates_only` (`0.8`), `predicates_plus_flat` (`0.775`), and `flat_semantic_only` (`0.775`).
- The gain costs more overhead and latency: `230.433333 ms` and `237.458333` discovery bytes for `full_hiroute`, versus `131.233333 ms` and `104.725` bytes for `predicates_only`.

## Caveats

- `predicates_only` remains stronger on the `200 ms` deadline metric (`0.683333` vs `0.6`), so the ablation claim should focus on object-resolution quality rather than strict tail latency.
