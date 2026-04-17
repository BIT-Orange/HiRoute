# Figure Registry

The active paper path is the mainline compact-medium route:

- dataset: `smartcity`
- hierarchy: `hiroute_hkm`
- topology: `rf_3967_exodus_compact`
- outputs: `results/{aggregate,figures,tables}/mainline/`
- exception: `state_scaling` is a state-only support experiment on `rf_1239_sprint` so that active-domain growth can be observed beyond the compact topology

Legacy `v1/v2/v3*` figures remain archived evidence only. Their lineage is tracked in `runs/registry/experiment_lineage.csv`.

| Figure | Paper Section | Aggregate CSV | Trace JSON | Source Experiment | Validation Gates | Status |
| --- | --- | --- | --- | --- | --- | --- |
| `fig_ablation` | `Evaluation-A` | `results/aggregate/mainline/ablation_summary.csv` | `results/aggregate/mainline/ablation_summary.trace.json` | `ablation` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | Route B main mechanism figure; read it through terminal success, first-fetch correctness, and discovery cost rather than wrong-object rate or semantic-centroid claims |
| `fig_routing_support` | `Evaluation-B` | `results/aggregate/mainline/routing_support.csv` and `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/routing_support.trace.json` and `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | support figure only; terminal success is saturated on this workload, so the paper-facing reading is first relevant-domain reach, candidate narrowing, probes, and bytes |
| `fig_object_manifest_sweep` | `Evaluation-C` | `results/aggregate/mainline/object_main_manifest_sweep.csv` | `results/aggregate/mainline/object_main_manifest_sweep.trace.json` | `object_main` | `validate_runtime_slice.py`, `validate_manifest_regression.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | cautionary/support figure only; use it to show the gap between terminal success and first-fetch correctness and to state explicitly when manifest rescue is absent |
| `fig_candidate_shrinkage` | `Evaluation-D` | `results/aggregate/mainline/candidate_shrinkage.csv` | `results/aggregate/mainline/candidate_shrinkage.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | routing-support mechanism figure; explains why the compact routing slice can separate on probes and bytes even when terminal success is saturated |
| `fig_deadline_summary` | `Evaluation-E` | `results/aggregate/mainline/deadline_summary.csv` | `results/aggregate/mainline/deadline_summary.trace.json` | `routing_main` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | diagnostic/support figure only; deadline behavior should be interpreted together with routing-support reach and cost, not as an independent superiority claim |
| `fig_state_scaling` | `Evaluation-F` | `results/aggregate/mainline/state_scaling_summary.csv` | `results/aggregate/mainline/state_scaling_summary.trace.json` | `state_scaling` | `validate_runtime_slice.py (state-only contract)`, `validate_aggregate_traceability.py`, `validate_figures.py` | large-topology state-only support figure on `rf_1239_sprint`; query-side metrics are intentionally `NaN` / `0`, and the figure should be read strictly as exported-state evidence under object-density and active-domain sweeps |
| `fig_robustness` | `Evaluation-G` | `results/aggregate/mainline/robustness_summary.csv` and `results/aggregate/mainline/robustness_timeseries.csv` | `results/aggregate/mainline/robustness_summary.trace.json` and `results/aggregate/mainline/robustness_timeseries.trace.json` | `robustness` | `validate_runtime_slice.py`, `validate_aggregate_traceability.py`, `validate_figures.py` | degradation-profile support figure; controller loss is expected to show measurable HiRoute degradation and extra probes, while stale summaries may remain near-flat on the current workload |
