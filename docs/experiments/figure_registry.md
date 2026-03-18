# Figure Registry

| Figure | Paper Section | Aggregate CSV | Source Experiment | Source Runs | Status |
| --- | --- | --- | --- | --- | --- |
| `fig_main_success_overhead` | `Evaluation-A` | `results/aggregate/v3/compact/main_success_overhead.csv` and `results/aggregate/v3/compact/candidate_shrinkage.csv` | `exp_routing_main_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_routing_main_v3_compact` | rerun required with expanded routing-support baselines (`predicates_only`, `random_admissible`) |
| `fig_failure_breakdown` | `Evaluation-B` | `results/aggregate/v3/compact/object_main_manifest_sweep.csv` | `exp_object_main_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_object_main_v3_compact` | promoted compact primary effectiveness figure |
| `fig_candidate_shrinkage` | `Evaluation-C` | `results/aggregate/v3/compact/candidate_shrinkage.csv` | `exp_routing_main_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_routing_main_v3_compact` | rerun required with expanded compact routing baseline set |
| `fig_deadline_summary` | `Evaluation-D` | `results/aggregate/v3/compact/deadline_summary.csv` | `exp_routing_main_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_routing_main_v3_compact` | rerun required with expanded compact routing baseline set |
| `fig_state_scaling` | `Evaluation-E` | `results/aggregate/v3/compact/state_scaling_summary.csv` | `exp_scaling_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_scaling_v3_compact` | pending compact rerun |
| `fig_robustness` | `Evaluation-F` | `results/aggregate/v3/compact/robustness_timeseries.csv` | `exp_robustness_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_robustness_v3_compact` | pending compact rerun |
| `fig_ablation` | `Evaluation-G` | `results/aggregate/v3/compact/ablation_summary.csv` | `exp_ablation_v3_compact` | `runs/registry/promoted_runs.csv` filtered by `exp_ablation_v3_compact` | promoted compact manifest=1 mechanism figure |
