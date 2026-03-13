# Figure: fig_failure_breakdown

## Purpose

- Separate wrong-domain, wrong-object, timeout, and other failure modes across baselines.

## Built from

- `results/aggregate/failure_breakdown.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- `hiroute` reduces `wrong_object` failures to `0.008333`, compared with `0.2` for both `flood` and `flat_iroute`.
- `oracle` splits its misses between `wrong_domain` (`0.225`) and `wrong_object` (`0.2`), while `hiroute`, `flood`, and `flat_iroute` only expose `wrong_object` in the promoted main experiment.

## Caveats

- This figure is sourced from the current promoted ndnSIM main-experiment runs only.
