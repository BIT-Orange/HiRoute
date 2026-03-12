# Figure: fig_deadline_summary

## Purpose

- Compare deadline-sensitive usefulness rather than raw completion time alone.

## Built from

- `results/aggregate/deadline_summary.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- The pipeline now emits success-before-deadline curves suitable for the latency section.

## Caveats

- Current values should be refreshed after the formal ndnSIM promoted runs replace the earlier promoted registry rows.
