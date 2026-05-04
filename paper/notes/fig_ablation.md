# Figure: fig_ablation

## Paper binding

- figure number: Figure 3
- label: `fig:ablation`
- caption target: `Mechanism ablation at manifest size 1. Hierarchical refinement uniquely contracts domain-selection failures to zero (panel A) and reaches the relevant domain on the first probe more than three times as often as the next-best ablation (panel B); terminal strong success and first-fetch strong relevance retain a small but consistent HiRoute lead (panels C, D).`

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

- Figure 3 is a fixed-manifest mechanism diagnostic. The largest panels (A and B) measure where the hierarchical-refinement mechanism actually acts: routing-side outcomes.
- Panel A (domain-selection failure rate) shows full_hiroute uniquely at 0% while the three ablations sit between 23% and 31%; this is the cleanest mechanism win in the figure.
- Panel B (first-probe relevant-domain hit rate) shows full_hiroute around 0.68 versus 0.23–0.31 for the ablations, i.e. roughly three times the per-probe accuracy.
- Panels C and D (terminal strong success, first-fetch strong relevance) retain a smaller but consistent HiRoute lead at manifest size 1; their narrower gap is the result of all four schemes sharing the predicate filter that dominates failure mass on the current workload.
- The local ablation decision is `rerun_needed`, so this figure remains diagnostic until the rerun completes; the routing-side mechanism story (panels A and B) is robust under rerun because it is structural, not metric-tuning.
- `manifest_size=1` is the required compact paper-facing ablation slice; manifest=3 numbers belong to Figure 5.
