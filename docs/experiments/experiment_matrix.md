# Experiment Matrix

| Experiment ID | Hypotheses | Dataset | Topology | Schemes | Seeds | Outputs | Promotion Rule | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `exp_main_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `exact`, `flood`, `flat_iroute`, `oracle`, `hiroute` | `1..5` | `results/aggregate/main_success_overhead.csv`, `results/figures/fig_main_success_overhead.pdf` | min 5 runs/scheme, zero missing logs, clean git state | planned |
| `exp_staleness_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `flat_iroute`, `hiroute`, `oracle` | `1..3` | `results/aggregate/robustness_summary.csv`, `results/figures/fig_robustness.pdf` | min 3 runs/scheme, zero missing logs, clean git state | planned |
| `exp_failures_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` | `flood`, `flat_iroute`, `hiroute`, `oracle` | `1..3` | `results/aggregate/robustness_summary.csv`, `results/figures/fig_robustness.pdf` | min 3 runs/scheme, zero missing logs, clean git state | planned |
| `exp_scaling_v1` | `H-001` | `smartcity_v1` | `rf_3967_exodus` + `rf_1239_sprint` | `flat_iroute`, `hiroute`, `oracle` | `1..3` | `results/aggregate/state_scaling_summary.csv`, `results/figures/fig_state_scaling.pdf` | min 3 runs/scheme, zero missing logs, clean git state | planned |
