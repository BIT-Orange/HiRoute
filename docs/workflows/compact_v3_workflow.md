# Compact v3 Workflow

`compact_v3` is the current paper-facing path for machines that cannot sustain the full
`rf_3967_exodus` plus `rf_1239_sprint` official reruns.

It preserves:
- the full `smartcity_v3` query bundles
- the full routing/object baseline sets
- the original `rf_3967_exodus` domain assignments and qrels

It reduces memory by:
- deriving `rf_3967_exodus_compact` from the original Rocketfuel 3967 topology
- retaining all active domains
- coalescing producer placement
- compressing relay-only degree-2 chains

## Rebuild compact topology artifacts

```bash
cd /Users/jiyuan/Desktop/HiRoute
.venv/bin/python scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v3.yaml
python3 scripts/build_dataset/build_topology_mapping.py --topology-config configs/topologies/rocketfuel_3967_exodus_compact.yaml
```

## Dry validation

```bash
python3 tools/validate_run.py --experiment configs/experiments/exp_object_main_v3_compact.yaml --scheme hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_ablation_v3_compact.yaml --scheme full_hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_routing_main_v3_compact.yaml --scheme hiroute --seed 1 --budget 16 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_scaling_v3_compact.yaml --scheme hiroute --seed 1 --budget 16 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_robustness_v3_compact.yaml --scheme hiroute --seed 1 --variant stale_summaries --budget 16 --mode dry
```

## Execution order

Run in this order:

1. `exp_object_main_v3_compact`
2. `exp_ablation_v3_compact`
3. `exp_routing_main_v3_compact`
4. `exp_scaling_v3_compact`
5. `exp_robustness_v3_compact`

```bash
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_object_main_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_ablation_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_routing_main_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_scaling_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_robustness_v3_compact.yaml --max-workers 1 --postprocess --validate
```

## Positioning

- `exp_*_v3_compact` is the current paper-facing route on this machine.
- `exp_*_v3_local` and `exp_*_v3_local_lite` remain debug/smoke routes only.
- `exp_*_v3` remains the future full-topology route for larger-memory machines.
