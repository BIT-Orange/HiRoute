# Figure: fig_object_manifest_sweep

## Paper binding

- figure number: Figure 6
- label: `fig:waterfall`
- caption target: `Object-main manifest sweep showing terminal success, first-fetch correctness, and observed manifest rescue under fallback.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/object_main_manifest_sweep.csv`
- diagnostic aggregate csv: `results/aggregate/mainline/failure_breakdown.csv`
- trace json: `results/aggregate/mainline/object_main_manifest_sweep.trace.json`
- figure assets: `results/figures/mainline/fig_object_manifest_sweep.pdf` and `results/figures/mainline/fig_object_manifest_sweep.png`
- source experiment: `object_main`

## Validation status

- runtime slice: `review_artifacts/object_main/validation/object_main_validate_runtime_slice.txt`
- manifest regression: `review_artifacts/object_main/validation/object_main_validate_manifest_regression.txt`
- aggregate traceability: `review_artifacts/object_main/validation/object_main_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/object_main/validation/object_main_validate_figures.txt`

## Status

- cautionary/support figure only

## Interpretation

- Figure 6 remains in the paper, but it is not a headline effectiveness figure.
- Its job is to show the gap between terminal success and first-fetch correctness and to answer the narrow question of whether manifest rescue is doing measurable work on the current workload.
- If the manifest-rescue panel stays at zero, the text must say that explicitly. The honest reading is then that terminal recovery is stronger than first-choice quality and that this workload does not expose a meaningful manifest-rescue signal.
- This figure should never be used to imply that larger manifests fix local object ranking unless the aggregate directly shows a non-zero rescue signal.
