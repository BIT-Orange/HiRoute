# Figure: fig_deadline_summary

## Purpose

- Compare deadline-sensitive usefulness rather than raw completion time alone.

## Built from

- `results/aggregate/deadline_summary.csv`

## Promoted runs

- `exp_routing_main_v2` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- `oracle` remains the centralized latency upper reference, reaching `0.916667` success within `200 ms` and `1.0` by `500 ms`, with median successful latency `107 ms`.
- Among the distributed methods on the corrected routing bundle, `hiroute` reaches `0.866667` success within `500 ms`, slightly above `flood` (`0.854167`) and above `flat_iroute` / `inf_tag_forwarding` (`0.833333`), while also keeping a lower median successful latency (`202 ms` vs `275.5 ms` for `flood` and `238 ms` for `flat_iroute` / `inf_tag_forwarding`).
- The deadline story is therefore still useful, but it now supports a latency-efficiency tradeoff claim rather than a raw success-gap claim.

## Caveats

- `exact` is intentionally left out of the plotted semantic-discovery comparison and should only be referenced as a syntactic lower-bound appendix point.
- The tight-deadline regime still favors the centralized oracle.
