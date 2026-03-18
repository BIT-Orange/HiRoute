# Figure: fig_main_success_overhead

## Purpose

- Show compact routing-support evidence under saturated end-to-end success.
- Focus on first relevant-domain reach, discovery cost, and staged candidate shrinkage at the default compact budget.

## Built from

- `results/aggregate/v3/compact/main_success_overhead.csv`
- `results/aggregate/v3/compact/candidate_shrinkage.csv`

## Promoted runs

- Current promoted rows come from `exp_routing_main_v3_compact` in `runs/registry/promoted_runs.csv`.
- The next paper-facing Figure 4 refresh requires rerunning `exp_routing_main_v3_compact` with the expanded routing-support baseline set that includes `predicates_only` and `random_admissible`.

## Observations

- Under compact-medium evaluation with shared fallback, end-to-end `ServiceSuccess@1` saturates for the distributed routing schemes. Figure 4 therefore remains a routing-support figure rather than a success frontier.
- The expanded routing-support slice is intended to separate three effects: what hard predicates alone already solve, what an admissible-but-nonsemantic policy looks like, and what semantic scoring plus hierarchy adds beyond both controls.
- Panel A compares first relevant-domain reach for `predicates_only`, `random_admissible`, `flat_iroute`, `inf_tag_forwarding`, and `hiroute` at budget `16`.
- Panel B compares discovery cost on the same compact budget, with `central_directory` retained only as a centralized reference.

## Caveats

- `central_directory` is retained as a discovery-cost reference, but its first-domain-reach metric is not directly comparable to the distributed probing baselines.
- `flood` remains in the compact routing experiment and support aggregates, but it is intentionally omitted from the paper-facing Figure 4 because the comparison is now about admissible reach quality and mechanism evidence rather than high-overhead recall.
