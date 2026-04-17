# Figure Registry

The active paper path is the mainline compact-medium route:

- dataset: `smartcity`
- hierarchy: `hiroute_hkm`
- topology: `rf_3967_exodus_compact`
- outputs: `results/{aggregate,figures,tables}/mainline/`

Legacy `v1/v2/v3*` figures remain archived evidence only. Their lineage is tracked in `runs/registry/experiment_lineage.csv`.

| Figure | Paper Section | Aggregate CSV | Trace JSON | Source Experiment | Validation Gates | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `fig_routing_support` | `Evaluation-A` | `results/aggregate/mainline/routing_support.csv` and `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/routing_support.trace.json` and `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | completed on 2026-03-31; blocked because routing headline metrics remain degenerate and `validate_figures.py` fails |
| `fig_object_manifest_sweep` | `Evaluation-B` | `results/aggregate/mainline/object_main_manifest_sweep.csv` | `results/aggregate/mainline/object_main_manifest_sweep.trace.json` | `object_main` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | completed on 2026-03-31; current rerun contradicts the intended HiRoute object-resolution claim |
| `fig_candidate_shrinkage` | `Evaluation-C` | `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | completed on 2026-03-31; traceable, but blocked as supporting-only evidence until routing headline metrics recover |
| `fig_deadline_summary` | `Evaluation-D` | `results/aggregate/mainline/deadline_summary.csv` | `results/aggregate/mainline/deadline_summary.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | completed on 2026-03-31; traceable, but currently diagnostic because all deadline rows collapse to failure |
| `fig_state_scaling` | `Evaluation-E` | `results/aggregate/mainline/state_scaling_summary.csv` | `results/aggregate/mainline/state_scaling_summary.trace.json` | `state_scaling` | `validate_runtime_slice.py (state-only contract)`, `validate_aggregate_traceability.py`, `validate_figures.py` | pending rerun; state-only figure, so query-side columns may remain placeholder-like |
| `fig_robustness` | `Evaluation-F` | `results/aggregate/mainline/robustness_summary.csv` and `results/aggregate/mainline/robustness_timeseries.csv` | `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json` | `robustness` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | pending rerun; placeholder permitted until new runs land |
| `fig_ablation` | `Evaluation-G` | `results/aggregate/mainline/ablation_summary.csv` | `results/aggregate/mainline/ablation_summary.trace.json` | `ablation` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | completed on 2026-03-31; signal currently degraded because all schemes remain at zero success |
