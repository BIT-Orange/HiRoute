# Figure: fig_object_manifest_sweep

## Paper binding

- figure number: Figure 5
- label: `fig:waterfall`
- caption target: `Mainline object-main manifest sweep showing terminal success and first-fetch correctness under manifest fallback.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/object_main_manifest_sweep.csv`
- diagnostic aggregate csv: `results/aggregate/mainline/failure_breakdown.csv`
- trace json: `results/aggregate/mainline/object_main_manifest_sweep.trace.json`
- figure assets: `results/figures/mainline/fig_object_manifest_sweep.pdf` and `results/figures/mainline/fig_object_manifest_sweep.png`
- source experiment: `object_main`

## Validation status

- runtime slice: completed (`review_artifacts/object_ablation_routing/validation/object_main_validate_runtime_slice.txt`)
- manifest regression: completed (`review_artifacts/object_ablation_routing/validation/object_main_validate_manifest_regression_*.txt`)
- aggregate traceability: completed (`review_artifacts/object_ablation_routing/validation/object_main_validate_aggregate_traceability.txt`)
- figure binding: completed (`review_artifacts/object_ablation_routing/validation/object_main_validate_figures_object_manifest_sweep.txt`)

## Status

- completed on 2026-03-31 mainline rerun

## Interpretation

- Figure 5 is an object-resolution figure.
- The fresh mainline rerun does not support a positive HiRoute claim: `central_directory` reaches `mean_success_at_1=1.0` for manifest sizes `1/2/3`, while the distributed baselines remain degenerate.
- The diagnostic `failure_breakdown.csv` shows that the frontier baselines are dominated by `wrong_domain` and `predicate_miss`, so the paper must frame this figure as a blocking discrepancy in object resolution rather than as routing superiority evidence.
- `manifest_size=1` remains the tightest reading because it exposes local ranking quality before fallback expands, but the current rerun shows no recovery benefit for HiRoute across `1/2/3`.
