# Figure: fig_failure_breakdown

## Purpose

- Separate wrong-domain, wrong-object, timeout, and other failure modes across baselines.

## Built from

- `results/aggregate/failure_breakdown.csv`

## Promoted runs

- `exp_main_v1` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- The current pipeline exposes per-scheme failure composition rather than only top-line success.

## Caveats

- Current committed values come from the existing promoted registry; once formal ndnSIM promoted runs replace the older promoted set, this figure should be regenerated.
