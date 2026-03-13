# Figure: fig_candidate_shrinkage

## Purpose

- Show HiRoute's staged frontier contraction and separate it from cross-method probe breadth.

## Built from

- `results/aggregate/candidate_shrinkage.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- In the left panel, `hiroute` keeps about `0.385246` of the original domain frontier after predicate screening and shrinks it further to `0.327869` by the probed-cell stage.
- In the right panel, the cross-method comparison is no longer a fake shared stage trace; it now reports discovery breadth directly through mean remote probes/query.
- This separation makes the mechanism claim legible: HiRoute's hierarchy contracts the frontier before probing, while the method comparison stays on a quantity every scheme actually shares.

## Caveats

- `oracle`, `flood`, and `flat_iroute` are intentionally not placed on the staged contraction curve because they do not share the same hierarchical refinement pipeline.
