# Figure: fig_main_success_overhead

## Purpose

- Show compact routing-support evidence under saturated end-to-end success.
- Focus on first relevant-domain reach, discovery cost, and staged candidate shrinkage at the default compact budget.

## Built from

- `results/aggregate/v3/compact/main_success_overhead.csv`
- `results/aggregate/v3/compact/candidate_shrinkage.csv`

## Promoted runs

- Current promoted rows come from `exp_routing_main_v3_compact` in `runs/registry/promoted_runs.csv`.
- Figure 4 reads the compact promoted slice at budget `16` and uses the compact `candidate_shrinkage.csv` mechanism slice for Panel C.

## Observations

- Under compact-medium evaluation with shared fallback, end-to-end `ServiceSuccess@1` saturates at `1.0` for every routing baseline. Figure 4 therefore stops treating success as the headline metric.
- At budget `16`, `hiroute` improves first relevant-domain reach (`0.641667`) relative to `flat_iroute` and `inf_tag_forwarding` (`0.425` each), even though end-to-end success is tied.
- This compact routing gain is not a universal cost win: `hiroute` also spends more discovery bytes (`186.670833`) than the flat and INF-style baselines (`149.870833`).
- The mechanism panel remains informative because `hiroute` contracts the staged search surface from `1.0` at `all_domains` to about `0.196` by `refined_cells` and `probed_cells`.

## Caveats

- `central_directory` is retained as a discovery-cost reference, but its first-domain-reach metric is not directly comparable to the distributed probing baselines.
- `flood` is intentionally omitted from the new Figure 4 support figure because the compact result is already saturated on end-to-end success and the paper-facing comparison is now about reach quality and mechanism evidence.
