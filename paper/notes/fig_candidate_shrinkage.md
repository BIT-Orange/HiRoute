# Figure: fig_candidate_shrinkage

## Purpose

- Show how strongly each method narrows the candidate set before object fetch.

## Built from

- `results/aggregate/candidate_shrinkage.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- The current implementation yields the same predicate-level shrinkage ratio (`0.007237` mean) across `oracle`, `hiroute`, `flood`, and `flat_iroute`; the differentiator is how many remote probes each strategy spends after predicate filtering.
- `hiroute` reaches the best semantic success with the highest mean probe count (`1.808333`), which is consistent with the adaptive multi-probe policy added in the final ndnSIM pass.

## Caveats

- The current shrinkage metric is driven by predicate candidate elimination. It does not yet separate post-manifest object shrinkage from pre-probe cell shrinkage.
