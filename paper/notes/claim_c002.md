# Claim C-002

## Text

On the active `smartcity` `object_main` workload, the failure mix is dominated by
`domain_selection` failure, not by `wrong_object`. In the current sealed aggregate
`failure_breakdown.csv`, `wrong_object` is zero for every scheme and every manifest size;
the only non-zero failure component is `inf_tag_forwarding`'s `wrong_domain` rate of
`0.091667`. `hiroute` and `central_directory` have no failures of either kind.

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

- Promoted runs for `object_main` and `routing_main`
- Legacy `exp_object_main_v2`, `exp_object_main_v3_compact`, and `exp_routing_main_v3_compact`
  provenance is mapped through `runs/registry/experiment_lineage.csv`

## Status

revised (2026-04-19: reworded to "domain_selection_dominated"; aligned with current
failure_breakdown.csv where wrong_object=0 and the only non-zero term is
inf_tag_forwarding wrong_domain=0.0917)
