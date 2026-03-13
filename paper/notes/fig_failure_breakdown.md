# Figure: fig_failure_breakdown

## Purpose

- Separate wrong-domain, wrong-object, timeout, and other failure modes across baselines.

## Built from

- `results/aggregate/failure_breakdown.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- `oracle` now has the expected all-success profile, which confirms that the centralized upper reference is aligned with `qrels_object.csv`.
- On the filtered `medium/high` ambiguity workload, `hiroute` reduces `wrong_object` failures to `0.071429`, compared with `0.571429` for both `flood` and `flat_iroute`.
- The filtered main workload still exposes a non-trivial `predicate_miss` slice (`0.071429`) for `hiroute`, `flood`, and `flat_iroute`, which makes the predicate-stage miss vs object-resolution miss split visible.

## Caveats

- `exact` is intentionally omitted from the plotted semantic-discovery comparison even though the aggregate retains it for reference bookkeeping.
- This figure is sourced from the current promoted ndnSIM main-experiment runs only.
