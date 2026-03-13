# Figure: fig_deadline_summary

## Purpose

- Compare deadline-sensitive usefulness rather than raw completion time alone.

## Built from

- `results/aggregate/deadline_summary.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- At `200 ms`, `flat_iroute` remains ahead on deadline satisfaction (`0.683333`) while `hiroute` reaches `0.6`.
- At `500 ms`, `hiroute` overtakes the semantic baselines at `0.858333`, compared with `0.8` for `flat_iroute` and `0.75` for `flood`.

## Caveats

- The deadline story is deadline-dependent: `hiroute` wins on eventual object resolution, but not on the tightest latency thresholds.
