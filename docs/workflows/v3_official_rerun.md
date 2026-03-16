# v3 Official Rerun Checklist

This checklist is the execution contract for the first official `smartcity_v3` rerun.

## Freeze gate

Run in order:

```bash
cd /Users/jiyuan/Desktop/HiRoute
git status --short
git rev-parse HEAD
.venv/bin/python scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v3.yaml
python3 tools/validate_run.py --experiment configs/experiments/exp_routing_main_v3.yaml --scheme hiroute --seed 1 --topology-id rf_3967_exodus --budget 16 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_object_main_v3.yaml --scheme hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_ablation_v3.yaml --scheme full_hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_scaling_v3.yaml --scheme hiroute --seed 1 --topology-id rf_3967_exodus --budget 16 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_robustness_v3.yaml --scheme hiroute --seed 1 --variant stale_summaries --budget 16 --mode dry
```

All five validations must pass before any official rerun starts.

## Smoke runs

Run one official smoke per main family:

```bash
python3 scripts/run/run_experiment.py --experiment configs/experiments/exp_routing_main_v3.yaml --scheme hiroute --seed 1 --topology-id rf_3967_exodus --budget 16 --mode official
python3 scripts/run/run_experiment.py --experiment configs/experiments/exp_object_main_v3.yaml --scheme hiroute --seed 1 --manifest-size 1 --mode official
python3 scripts/run/run_experiment.py --experiment configs/experiments/exp_ablation_v3.yaml --scheme full_hiroute --seed 1 --manifest-size 1 --mode official
```

Inspect each run directory for:

- `manifest.yaml`
- `query_log.csv`
- `probe_log.csv`
- `search_trace.csv`
- `state_log.csv`
- `stdout.log`
- `stderr.log`

The manifest must expose `runner_type: ndnsim`. Routing runs must expose `budget`. Object and ablation runs must expose `manifest_size`.

## Official rerun order

1. `exp_routing_main_v3`
2. `exp_object_main_v3`
3. `exp_ablation_v3`
4. `exp_scaling_v3` only if 1-3 are interpretable
5. `exp_robustness_v3` only if 1-3 are interpretable

Use direct `python3 scripts/...` commands for `v3`. The root `Makefile` still defaults to `v2`.

## Go or harden

### routing_hard_v3

Proceed if:

- distributed methods do not all saturate above `0.97` success
- `hiroute` has either a success advantage or at least `15%` cost advantage over `flat_iroute` on both topologies
- `flat_iroute` and `inf_tag_forwarding` are not numerically collapsed
- the budget sweep changes the frontier

Harden into `routing_hard_v3b` if:

- all distributed methods saturate near `1.0`
- frontier points are nearly flat across budgets
- `hiroute`, `flat_iroute`, and `inf_tag_forwarding` differ only by noise
- `flat_iroute` and `inf_tag_forwarding` remain effectively identical

### object_hard_v3

Treat `manifest_size = 1` as the primary readout.

Proceed if:

- `manifest_size = 1` separates `hiroute` from at least one strong baseline
- the `1 -> 2 -> 3 -> 5` sweep materially changes at least one curve
- `central_directory` remains the upper reference

Harden into `object_hard_v3b` if:

- `manifest_size = 1` is already saturated
- `manifest_size = 2` collapses all methods together
- `wrong_object_rate` barely differs across methods
- `best_object_chosen_given_relevant_domain` is too similar across methods

### ablation

Proceed if `full_hiroute` is clearly better than at least one ablation at `manifest_size = 1`.

Audit implementation before changing the workload if:

- all ablations collapse together
- only larger manifest sizes show separation
- `predicates_plus_flat` is still anomalously worse than `predicates_only`
