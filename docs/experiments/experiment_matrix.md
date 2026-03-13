# Experiment Matrix

| Experiment ID | Hypotheses | Dataset | Topology | Schemes | Seeds | Outputs | Promotion Rule | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `exp_main_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `exact`, `flood`, `flat_iroute`, `oracle`, `hiroute` | `1..5` | `results/aggregate/main_success_overhead.csv`, `results/aggregate/failure_breakdown.csv`, `results/aggregate/candidate_shrinkage.csv`, `results/aggregate/deadline_summary.csv`, `results/figures/fig_main_success_overhead.pdf` | min 5 runs/scheme, zero missing logs, clean git state | completed |
| `exp_staleness_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `hiroute` | `1..3` | `results/aggregate/robustness_summary.csv`, `results/figures/fig_robustness.pdf` | min 3 runs/scheme, zero missing logs, clean git state | completed |
| `exp_failures_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `hiroute` | `1..3` | `results/aggregate/robustness_summary.csv`, `results/figures/fig_robustness.pdf` | min 3 runs/scheme, zero missing logs, clean git state | completed |
| `exp_scaling_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` + `rf_1239_sprint` | `hiroute` | `1..3` | `results/aggregate/state_scaling_summary.csv`, `results/figures/fig_state_scaling.pdf` | min 3 runs/scheme, zero missing logs, clean git state | completed |
| `exp_ablation_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `predicates_only`, `flat_semantic_only`, `predicates_plus_flat`, `full_hiroute` | `1..3` | `results/aggregate/ablation_summary.csv`, `results/figures/fig_ablation.pdf` | min 3 runs/scheme, zero missing logs, clean git state | completed |
