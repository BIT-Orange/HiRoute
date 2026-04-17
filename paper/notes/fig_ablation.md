# Figure: fig_ablation

## Paper binding

- figure number: Figure 4
- label: `fig:ablation`
- caption target: `Mainline mechanism ablation at manifest size \`1\`, showing terminal success, first-fetch correctness, and discovery cost.`

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

- Route B main mechanism figure

## Interpretation

- Figure 4 is the strongest paper-facing evidence for Route B.
- The paper-facing reading is fixed even when exact values refresh: `full_hiroute` should be judged on terminal success and discovery cost, not on a claim that it necessarily improves first-fetch precision.
- Panel B is included specifically to expose the difference between terminal success and first-fetch correctness. If those two orderings diverge, the text must say that the gain comes from bounded hierarchical search plus recovery rather than from superior first-choice object ranking alone.
- `manifest_size=1` stays fixed because it is the sharpest setting for mechanism discrimination; wider fallback would make it easier for later recovery to conceal weak intermediate choices.
