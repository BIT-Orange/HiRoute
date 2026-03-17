# Local v3 Workflow

This workflow is for running a reduced `smartcity_v3` validation matrix on a laptop-class machine.
It is intentionally smaller than the official `v3` matrix and should be treated as a local signal
check, not as paper-grade evidence.

## What Is Reduced

- only the medium topology `rf_3967_exodus` is used
- routing frontier is reduced to budgets `8,16`
- object and ablation sweeps are reduced to manifest sizes `1,2`
- query scheduling is capped per ingress node
- scaling and robustness use reduced sweeps and shorter simulation horizons

## Local Configs

- [`exp_routing_main_v3_local.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_routing_main_v3_local.yaml)
- [`exp_object_main_v3_local.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_object_main_v3_local.yaml)
- [`exp_ablation_v3_local.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_ablation_v3_local.yaml)
- [`exp_scaling_v3_local.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_scaling_v3_local.yaml)
- [`exp_robustness_v3_local.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_robustness_v3_local.yaml)

## Recommended Order

1. Validate the reduced configs.
2. Run routing, object, and ablation first.
3. Inspect the local aggregates.
4. Only then decide whether scaling and robustness are worth running locally.

## Commands

Validate:

```bash
python3 tools/validate_run.py --experiment configs/experiments/exp_routing_main_v3_local.yaml --scheme hiroute --seed 1 --budget 16 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_object_main_v3_local.yaml --scheme hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_ablation_v3_local.yaml --scheme full_hiroute --seed 1 --manifest-size 1 --mode dry
```

Run the local validation matrix:

```bash
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_routing_main_v3_local.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_object_main_v3_local.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_ablation_v3_local.yaml --max-workers 1 --postprocess --validate
```

Optional reduced scaling and robustness:

```bash
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_scaling_v3_local.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_robustness_v3_local.yaml --max-workers 1 --postprocess --validate
```

## Output Roots

Local validation outputs live under:

- `results/aggregate/v3/local/`
- `results/figures/v3/local/`

Keep them separate from the official `v3` outputs.
