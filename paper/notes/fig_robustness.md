# Figure: fig_robustness

## Paper binding

- figure number: Figure 9
- label: `fig:robust`
- caption target: `Mainline robustness under stale summaries and controller failures. Placeholder until promoted mainline runs land.`

## Evidence binding

- aggregate csv: `results/aggregate/mainline/robustness_summary.csv`
- companion aggregate csv: `results/aggregate/mainline/robustness_timeseries.csv`
- trace json: `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json`
- figure assets: `results/figures/mainline/fig_robustness.pdf` and `results/figures/mainline/fig_robustness.png`
- source experiment: `robustness`

## Validation status

- runtime slice: pending rerun
- aggregate traceability: pending rerun
- figure binding: pending rerun

## Status

- pending rerun; placeholder figure is acceptable until promoted runs land

## Interpretation

- Figure 9 is only suitable for the main paper if the rerun yields a real recovery time series, not just a summary bar.
- The active reading is recovery behavior under stale summaries and controller failure, not a generic fault-tolerance slogan.
