# Figure: fig_failure_breakdown

## Purpose

- Separate wrong-domain, wrong-object, timeout, and other failure modes across baselines.

## Built from

- `results/aggregate/failure_breakdown.csv`

## Promoted runs

- `exp_object_main_v2` promoted runs recorded in `runs/registry/promoted_runs.csv`

## Observations

- On the current `object_hard` bundle, every distributed method and the centralized oracle finish with `1.0` success after shared manifest fallback is enabled.
- As a result, the figure now functions as an evaluation sanity check: the local resolver, qrels, and runtime slicing are consistent, but the workload is no longer discriminative enough to support a strong object-resolution superiority claim.
- This outcome is still informative because it shows the earlier v1 failure gap was partly an artifact of inconsistent fallback and incomplete runtime coverage.

## Caveats

- `exact` remains omitted from the semantic-discovery comparison.
- This figure should currently be treated as `sanity-only`; the next paper-grade iteration needs a harder object-level bundle that still respects the corrected query/qrels and fallback semantics.
