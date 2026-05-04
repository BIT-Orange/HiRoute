# Claim C-004

## Text

The active ablation claim is bound to the mainline `ablation` aggregate rather than to archived
legacy figures. In the current paper layout this is Figure 3, not Figure 10. The local ablation
stage decision is `rerun_needed`, so the figure is only a fixed-manifest diagnostic: it may say
that `full_hiroute` has the highest terminal strong success at manifest size 1 in the current
local slice, but it must also say that the gap is small, the cost ordering is not clean, and the
first-fetch ordering does not close a mechanism-superiority claim.

## Supported by

- `results/figures/mainline/fig_ablation_summary.pdf`

## Aggregates

- `results/aggregate/mainline/ablation_summary.csv`

## Source runs

- Current local `ablation` run IDs recorded in the aggregate trace
- `review_artifacts/ablation/aggregate/ablation_decision.json`

## Status

diagnostic/blocking; local stage decision is `rerun_needed`
