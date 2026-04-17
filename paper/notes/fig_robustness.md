# Figure: fig_robustness

## Paper binding

- figure number: Figure 9
- label: `fig:robust`
- caption target: `Robustness support figure showing degradation under stale summaries and controller loss.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/robustness_summary.csv`
- companion aggregate csv: `results/aggregate/mainline/robustness_timeseries.csv`
- trace json: `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json`
- figure assets: `results/figures/mainline/fig_robustness.pdf` and `results/figures/mainline/fig_robustness.png`
- source experiment: `robustness`

## Validation status

- runtime slice: `review_artifacts/robustness/validation/robustness_validate_runtime_slice.txt`
- aggregate traceability: `review_artifacts/robustness/validation/robustness_validate_aggregate_traceability.txt`
- figure binding: `review_artifacts/robustness/validation/robustness_validate_figures.txt`

## Status

- degradation-profile support figure

## Interpretation

- Figure 9 should be read as a degradation-profile figure, not as a blanket robustness win.
- The left subplot is the controller-loss scenario and the right subplot is the stale-summaries scenario; the event markers should come directly from `failure_time_s` and `recovery_time_s` in the timeseries aggregate.
- If `t95_recovery_sec` is zero, the text must explain that this means recovery within the first post-event one-second bin, not that the workload experienced no degradation.
