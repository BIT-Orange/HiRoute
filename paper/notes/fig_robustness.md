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
- The `controller_down` variant is a HiRoute-specific fault: `central_directory` does not depend on a per-domain controller, so its `min_success_after_event=1.0` is not a robustness advantage over HiRoute — it is evidence that this particular fault does not apply to that scheme. Captions and paper text must frame the comparison as "how HiRoute degrades under a fault its architecture exposes" rather than "HiRoute is less robust than centralized directory."
- The `stale_summaries` variant currently uses `staleDropProbability=0.5` with `manifestSize=5` and `probeBudget=5`, which produces `min_success_after_event=1.0` for `hiroute`. This near-flat curve means the scenario is currently a weak stressor for the implemented fallback path; any "hiroute is robust to staleness" claim must be qualified accordingly, or the scenario parameters must be tightened (see revision_log entry 2026-04-19).
