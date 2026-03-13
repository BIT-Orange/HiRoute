# Figure Registry

| Figure | Paper Section | Aggregate CSV | Source Experiment | Source Runs | Status |
| --- | --- | --- | --- | --- | --- |
| `fig_main_success_overhead` | `Evaluation-A` | `results/aggregate/main_success_overhead.csv` | `exp_main_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_main_v1` | ready |
| `fig_failure_breakdown` | `Evaluation-B` | `results/aggregate/failure_breakdown.csv` | `exp_main_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_main_v1` | ready |
| `fig_candidate_shrinkage` | `Evaluation-C` | `results/aggregate/candidate_shrinkage.csv` | `exp_main_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_main_v1` | ready |
| `fig_deadline_summary` | `Evaluation-D` | `results/aggregate/deadline_summary.csv` | `exp_main_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_main_v1` | ready |
| `fig_state_scaling` | `Evaluation-E` | `results/aggregate/state_scaling_summary.csv` | `exp_scaling_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_scaling_v1` | ready |
| `fig_robustness` | `Evaluation-F` | `results/aggregate/robustness_summary.csv` | `exp_staleness_v1` + `exp_failures_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_staleness_v1` and `exp_failures_v1` | ready |
| `fig_ablation` | `Evaluation-G` | `results/aggregate/ablation_summary.csv` | `exp_ablation_v1` | `runs/registry/promoted_runs.csv` filtered by `exp_ablation_v1` | ready |
