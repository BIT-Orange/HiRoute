# Figure Registry

The active paper path is the mainline compact-medium route:

- dataset: `smartcity`
- hierarchy: `hiroute_hkm`
- topology: `rf_3967_exodus_compact`
- outputs: `results/{aggregate,figures,tables}/mainline/`

Legacy `v1/v2/v3*` figures remain archived evidence only. Their lineage is tracked in `runs/registry/experiment_lineage.csv`.

| Figure | Paper Section | Aggregate CSV | Trace JSON | Source Experiment | Validation Gates | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `fig_routing_support` | `Evaluation-A` | `results/aggregate/mainline/routing_support.csv` and `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/routing_support.trace.json` and `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; gates pass; terminal success is saturated, so keep this as a support figure on relevant-domain reach, probes, and bytes rather than a headline success figure |
| `fig_object_manifest_sweep` | `Evaluation-B` | `results/aggregate/mainline/object_main_manifest_sweep.csv` | `results/aggregate/mainline/object_main_manifest_sweep.trace.json` | `object_main` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; stage decision is `ready_for_main_figure`; use it for the terminal-success versus first-fetch-correctness story and note that manifest rescue remains invariant at `0.0` |
| `fig_candidate_shrinkage` | `Evaluation-C` | `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; traceable support figure; the mainline plotter now collapses duplicate scheme rows at the default budget before rendering |
| `fig_deadline_summary` | `Evaluation-D` | `results/aggregate/mainline/deadline_summary.csv` | `results/aggregate/mainline/deadline_summary.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; traceable diagnostic/support figure for deadline-side behavior under the recovered routing_main workload |
| `fig_state_scaling` | `Evaluation-E` | `results/aggregate/mainline/state_scaling_summary.csv` | `results/aggregate/mainline/state_scaling_summary.trace.json` | `state_scaling` | `validate_runtime_slice.py (state-only contract)`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; state-only rerun complete; query-side metrics are intentionally `NaN` / `0` and the figure should be read strictly as exported-state evidence |
| `fig_robustness` | `Evaluation-F` | `results/aggregate/mainline/robustness_summary.csv` and `results/aggregate/mainline/robustness_timeseries.csv` | `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json` | `robustness` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; promoted rerun complete with non-empty summary and timeseries; `central_directory` stays flat while `hiroute` shows measurable degradation under `controller_down` plus extra recovery probes |
| `fig_ablation` | `Evaluation-G` | `results/aggregate/mainline/ablation_summary.csv` | `results/aggregate/mainline/ablation_summary.trace.json` | `ablation` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | refreshed on 2026-04-17; stage decision is `ready_for_support_figure`; mechanism ordering is clean with `full_hiroute > predicates_plus_flat > predicates_only > flat_semantic_only` |
