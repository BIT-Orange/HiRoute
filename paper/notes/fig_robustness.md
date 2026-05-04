# Figure: fig_robustness

## Paper binding

- figure number: Figure 9
- label: `fig:robust`
- caption target: `Degradation profile under controller-down and stale-summary stressors. HiRoute degrades and recovers under per-domain controller failure with a bounded minimum-success floor; the centralized directory is shown as a non-peer availability reference because it does not expose per-domain controllers to this stressor.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/robustness_summary.csv`
- companion aggregate csv: `results/aggregate/mainline/robustness_timeseries.csv`
- trace json: `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json`
- figure assets: `results/figures/mainline/fig_robustness.pdf` and `results/figures/mainline/fig_robustness.png`
- source experiment: `robustness`

## Validation status

- runtime slice: `review_artifacts/robustness/validation/robustness_validate_runtime_slice.txt`
- aggregate traceability: current `tools/validate_aggregate_traceability.py --registry-source runs` fails because the registry points to `runs/completed/...` robustness directories that are missing locally; stage-copy raw logs exist under `review_artifacts/robustness/runs/`
- figure binding: current `tools/validate_figures.py` fails for the same promoted-run/raw-log provenance reason

## Status

- diagnostic/blocking until robustness raw-run provenance, query-count, figure-binding, and clean-promotion gates pass

## Interpretation

- Figure 9 should be read as a degradation-profile figure, not as a blanket robustness win. It is not paper-ready until the robustness raw-run provenance is restored or the stage is rerun and promoted cleanly.
- The left subplot is the controller-failure scenario and the right subplot is the stale-summaries scenario; the event markers should come directly from `failure_time_s` and `recovery_time_s` in the timeseries aggregate.
- If `t95_recovery_sec` is zero, the text must explain that this means recovery within the first post-event one-second bin, not that the workload experienced no degradation.
- The `controller_down` variant is a HiRoute-specific fault: `central_directory` does not depend on a per-domain controller, so its `min_success_after_event=1.0` is not a robustness advantage over HiRoute — it is evidence that this particular fault does not apply to that scheme. Captions and paper text must frame the comparison as "how HiRoute degrades under a fault its architecture exposes" rather than "HiRoute is less robust than centralized directory."
- The `stale_summaries` variant currently uses `staleDropProbability=0.5` with `manifestSize=5` and `probeBudget=5`, which produces `min_success_after_event=1.0` for `hiroute`. This near-flat curve means the scenario is currently a weak stressor for the implemented fallback path; any "hiroute is robust to staleness" claim must be qualified accordingly, or the scenario parameters must be tightened (see revision_log entry 2026-04-19).
