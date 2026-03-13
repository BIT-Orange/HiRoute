# Figure: fig_deadline_summary

## Purpose

- Compare deadline-sensitive usefulness rather than raw completion time alone.

## Built from

- `results/aggregate/deadline_summary.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- On the filtered `medium/high` ambiguity workload, `oracle` dominates the comparable methods on deadline-sensitive usefulness, reaching `1.0` success within `200 ms`.
- `hiroute` still improves eventual useful retrieval over the decentralized baselines, reaching `0.619048` success within `500 ms` versus `0.357143` for both `flat_iroute` and `flood`.
- The right-hand latency panel now reports median latency among successful queries instead of mixing incomparable curves and the exact-name reference in one panel.

## Caveats

- `exact` is intentionally left out of the plotted semantic-discovery comparison and should only be referenced as a syntactic lower-bound appendix point.
- The deadline story is deadline-dependent: `hiroute` wins on eventual object resolution, but not on the tightest latency thresholds.
