# Figure: fig_ablation

## Paper binding

- figure number: Figure 10
- label: `fig:ablation`
- caption target: `Mainline object-main ablation at manifest size \`1\`.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/ablation_summary.csv`
- trace json: `results/aggregate/mainline/ablation_summary.trace.json`
- figure assets: `results/figures/mainline/fig_ablation_summary.pdf` and `results/figures/mainline/fig_ablation_summary.png`
- source experiment: `ablation`

## Validation status

- runtime slice: completed (`review_artifacts/object_ablation_routing/validation/ablation_validate_runtime_slice.txt`)
- manifest regression: completed (`review_artifacts/object_ablation_routing/validation/ablation_validate_manifest_regression_*.txt`)
- aggregate traceability: completed (`review_artifacts/object_ablation_routing/validation/ablation_validate_aggregate_traceability.txt`)
- figure binding: completed (`review_artifacts/object_ablation_routing/validation/ablation_validate_figures_ablation.txt`)

## Status

- completed on 2026-03-31 mainline rerun

## Interpretation

- Figure 10 remains a mechanism figure, not an archive of legacy compact-v3 numbers.
- The fresh rerun preserves cost ordering but not success separation: all ablation schemes are at `mean_success_at_1=0.0`, with `flat_semantic_only` highest in discovery bytes, `full_hiroute` intermediate, and `predicates_only` / `predicates_plus_flat` lowest.
- The paper must describe this as degraded mechanism evidence until the object-main failure mode is explained or fixed.
- `manifest_size=1` stays fixed because it is the most discriminative setting for local ranking quality, even though the current rerun still collapses the success axis.
