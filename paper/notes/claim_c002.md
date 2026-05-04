# Claim C-002

## Text

On the active `smartcity` `object_main` workload, Figure 5 is support evidence for terminal
recovery under bounded fallback rather than proof of local first-object ranking quality. The
current local mainline `failure_breakdown.csv` is dominated by `predicate_miss` residual failures
for the distributed schemes. `hiroute` has zero terminal `wrong_object` rows in this local
aggregate, while `inf_tag_forwarding` still has non-zero terminal `wrong_object` rows. The paper
therefore must not claim that HiRoute reduces "first returned object was wrong but later rescued"
unless the metric is instrumented directly for that event.

The corresponding figure is therefore interpreted as evidence about terminal recovery
through sequential fallback rather than as evidence about local object-ranking quality
under manifest rescue. Deadline summaries remain supporting latency evidence tied to the
routing-support workload and should not be read as an independent effectiveness claim.

## Supported by

- `results/figures/mainline/fig_object_manifest_sweep.pdf`
- `results/figures/mainline/fig_deadline_summary.pdf`

## Aggregates

- `results/aggregate/mainline/object_main_manifest_sweep.csv`
- `results/aggregate/mainline/failure_breakdown.csv`
- `results/aggregate/mainline/deadline_summary.csv`

## Source runs

- `object_main` stage decision in `review_artifacts/object_main/aggregate/object_main_decision.json`
- Diagnostic routing rows remain gated by the routing query-count failure before paper-facing use.

## Status

revised for the current local mainline aggregate; support-only until the worktree is clean and
the readiness audit passes
