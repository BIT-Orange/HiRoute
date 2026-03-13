# Figure: fig_failure_breakdown

## Purpose

- Separate wrong-domain, wrong-object, timeout, and other failure modes across baselines.

## Built from

- `results/aggregate/failure_breakdown.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- `oracle` now has the expected all-success profile, which confirms that the centralized upper reference is aligned with `qrels_object.csv`.
- `hiroute` reduces `wrong_object` failures to `0.04918`, compared with `0.393443` for both `flood` and `flat_iroute`.
- The current main workload also surfaces a smaller `predicate_miss` slice (`0.04918`) for `hiroute`, `flood`, and `flat_iroute`, which is useful because it separates predicate-stage misses from object-resolution mistakes.

## Caveats

- `exact` is intentionally omitted from the plotted semantic-discovery comparison even though the aggregate retains it for reference bookkeeping.
- This figure is sourced from the current promoted ndnSIM main-experiment runs only.
