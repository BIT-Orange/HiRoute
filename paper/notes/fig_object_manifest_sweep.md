# Figure: fig_object_manifest_sweep

## Paper binding

- figure number: Figure 5
- label: `fig:waterfall`
- caption target: `Object-resolution manifest sweep. HiRoute has the largest absolute terminal-success gain across the manifest sizes tested (panel D), driven by the highest manifest rescue rate (panel C). First-fetch correctness (panel B) remains low across schemes because the current workload's failures are concentrated at the predicate-filter stage; the centralized directory remains a non-peer reference for first-fetch correctness.`

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

- semantically supportable support figure, but blocked for final paper-facing readiness while the worktree is dirty

## Interpretation

- Figure 5 remains in the paper, but it is not a headline effectiveness figure.
- Its job is to show the gap between terminal success and first-fetch correctness and to answer the narrow question of whether manifest rescue is doing measurable work on the current workload.
- The current aggregate has non-zero manifest rescue at manifest sizes 2 and 3, especially for HiRoute at manifest size 3.
- This figure should never be used to imply that larger manifests fix first-choice local object ranking; the supportable claim is that bounded fallback and re-probing improve terminal resolution after weak first choices.
