# Claim C-002

## Text

After enforcing topology-consistent query bundles, shared local resolver semantics, sequential
manifest fallback, and full-query completion, the current `object_hard` bundle no longer
separates distributed methods on success. Figure 5 should therefore be read as a sanity check,
while Figure 7 still supports a bounded-latency efficiency story in which HiRoute outperforms
the flat and INF-style baselines at moderate deadlines without surpassing the centralized oracle.

## Supported by

- `results/figures/fig_failure_breakdown.pdf`
- `results/figures/fig_deadline_summary.pdf`

## Aggregates

- `results/aggregate/failure_breakdown.csv`
- `results/aggregate/deadline_summary.csv`

## Source runs

- Promoted runs for `exp_object_main_v2` and `exp_routing_main_v2`

## Status

revised
