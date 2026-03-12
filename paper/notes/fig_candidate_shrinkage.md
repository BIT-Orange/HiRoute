# Figure: fig_candidate_shrinkage

## Purpose

- Show how strongly each method narrows the candidate set before object fetch.

## Built from

- `results/aggregate/candidate_shrinkage.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- The evaluation pipeline now preserves a route from raw query traces to candidate-shrinkage aggregates.

## Caveats

- Older promoted runs do not contain full raw shrinkage fields, so current committed values may include compatibility fallbacks.
