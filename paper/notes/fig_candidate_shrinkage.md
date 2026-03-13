# Figure: fig_candidate_shrinkage

## Purpose

- Show how strongly each method narrows the candidate set before object fetch.

## Built from

- `results/aggregate/candidate_shrinkage.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- `hiroute` now shows a real staged contraction curve instead of a flat predicate-only ratio: after predicate screening it keeps about `0.297917` of the original domain frontier, and after hierarchical refinement it drops to about `0.258333`.
- `flat_iroute` contracts only at the predicate stage and then stays flat at about `0.297917`, which is the behavior the paper wanted Figure 6 to separate from hierarchical refinement.
- `flood` collapses to the predicate-admissible set first, but its frontier rebounds to `1.0` at the refined/probed stages because it still fans out to every controller.

## Caveats

- `exact` is intentionally not plotted here because it bypasses semantic discovery altogether and therefore does not produce a meaningful hierarchical frontier trace.
