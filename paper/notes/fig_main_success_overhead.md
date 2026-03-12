# Figure: fig_main_success_overhead

## Purpose

Compare end-to-end service success against discovery overhead for the first formal experiment.

## Built from

- `results/aggregate/main_success_overhead.csv`

## Promoted runs

- `exact`: `exp_main_v1__exact__smartcity_v1__seed1__20260312_122120`, `exp_main_v1__exact__smartcity_v1__seed2__20260312_122120`, `exp_main_v1__exact__smartcity_v1__seed3__20260312_122121`, `exp_main_v1__exact__smartcity_v1__seed4__20260312_122121`, `exp_main_v1__exact__smartcity_v1__seed5__20260312_122121`
- `flood`: `exp_main_v1__flood__smartcity_v1__seed1__20260312_122121`, `exp_main_v1__flood__smartcity_v1__seed2__20260312_122121`, `exp_main_v1__flood__smartcity_v1__seed3__20260312_122122`, `exp_main_v1__flood__smartcity_v1__seed4__20260312_122122`, `exp_main_v1__flood__smartcity_v1__seed5__20260312_122122`
- `flat_iroute`: `exp_main_v1__flat_iroute__smartcity_v1__seed1__20260312_122122`, `exp_main_v1__flat_iroute__smartcity_v1__seed2__20260312_122122`, `exp_main_v1__flat_iroute__smartcity_v1__seed3__20260312_122123`, `exp_main_v1__flat_iroute__smartcity_v1__seed4__20260312_122123`, `exp_main_v1__flat_iroute__smartcity_v1__seed5__20260312_122123`
- `oracle`: `exp_main_v1__oracle__smartcity_v1__seed1__20260312_122123`, `exp_main_v1__oracle__smartcity_v1__seed2__20260312_122123`, `exp_main_v1__oracle__smartcity_v1__seed3__20260312_122124`, `exp_main_v1__oracle__smartcity_v1__seed4__20260312_122124`, `exp_main_v1__oracle__smartcity_v1__seed5__20260312_122124`
- `hiroute`: `exp_main_v1__hiroute__smartcity_v1__seed1__20260312_122124`, `exp_main_v1__hiroute__smartcity_v1__seed2__20260312_122124`, `exp_main_v1__hiroute__smartcity_v1__seed3__20260312_122124`, `exp_main_v1__hiroute__smartcity_v1__seed4__20260312_122125`, `exp_main_v1__hiroute__smartcity_v1__seed5__20260312_122125`

## Observations

- `hiroute` improves mean `success_at_1` over `flat_iroute` (`0.7050` vs `0.4975`).
- `hiroute` uses much less discovery overhead than `flood` (`851.24` vs `1815.03` mean discovery bytes).
- `oracle` remains the upper bound on success (`0.7925`) while `exact` remains the lowest-overhead but lowest-success baseline.

## Caveats

- These values come from the deterministic mock runner, not the final ndnSIM protocol path.
- The current figure supports workflow traceability and baseline wiring; it is not yet a publishable protocol result.
