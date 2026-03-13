# Figure: fig_ablation

## Purpose

- Summarize component-level tradeoffs across the current comparison set.

## Built from

- `results/aggregate/ablation_summary.csv`

## Promoted runs

- Current `exp_ablation_v1` promoted runs.
- Latest `full_hiroute` runs: `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed1__20260313_123901`, `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed2__20260313_124001`, `exp_ablation_v1__full_hiroute__smartcity_v1__rf_3967_exodus__seed3__20260313_124101`

## Observations

- On the filtered `high`-ambiguity workload, `full_hiroute` is the highest-success ablation at `0.875`, far ahead of `predicates_only` (`0.208333`), `predicates_plus_flat` (`0.125`), and `flat_semantic_only` (`0.125`).
- This is the first ablation run that clearly supports the paper's causal story: hard predicates alone no longer solve the task, and the full hierarchy dominates even though it pays higher discovery cost (`327.958333` bytes) and latency (`494.916667 ms`).

## Caveats

- The filtered ablation is intentionally a stress workload for semantic ambiguity, so its latency numbers are less representative than the main filtered workload.
