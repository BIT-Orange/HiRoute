# Figure: fig_ablation

## Paper binding

- figure number: Figure 3
- label: `fig:ablation`
- caption target: `Diagnostic mechanism ablation at manifest size 1, showing terminal strong success, first-fetch strong correctness, and discovery cost.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/ablation_summary.csv`
- trace json: `results/aggregate/mainline/ablation_summary.trace.json`
- figure assets: `results/figures/mainline/fig_ablation_summary.pdf` and `results/figures/mainline/fig_ablation_summary.png`
- source experiment: `ablation`

## Validation status

- runtime slice: `review_artifacts/ablation/validation/ablation_validate_runtime_slice.txt`
- manifest regression: `review_artifacts/ablation/validation/ablation_validate_manifest_regression.txt`
- aggregate traceability: `review_artifacts/ablation/validation/ablation_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/ablation/validation/ablation_validate_figures.txt`

## Status

- Diagnostic/blocking under the local stage decision. `review_artifacts/ablation/aggregate/ablation_decision.json` currently reports `rerun_needed`.

## Interpretation

- Figure 3 is a fixed-manifest diagnostic rather than a standalone proof of full-system superiority.
- The local ablation decision is `rerun_needed`, so this figure must not be treated as paper-facing support until ablation is repaired or rerun cleanly.
- The current reading is narrow: `full_hiroute` has the highest terminal strong success at manifest size 1, but the current gap is small and the discovery-byte ordering is not clean.
- Panel B is included specifically to expose the difference between terminal success and first-fetch correctness. If those two orderings diverge, the text must say that the gain comes from bounded hierarchical search plus recovery rather than from superior first-choice object ranking alone.
- `manifest_size=1` remains the required compact paper-facing ablation slice; the current manifest-1 aggregate has only a small terminal-success separation and should not be used as the headline mechanism proof by itself.
