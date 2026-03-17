# HiRoute Research Repository

This repository is the single source of truth for HiRoute simulation code, dataset preparation,
experiment execution, result aggregation, and paper writing.

## Canonical roots

- `ns-3/src/ndnSIM/`: simulation and protocol implementation root
- `configs/`: frozen dataset, baseline, hierarchy, and experiment configs
- `data/registry/`: tracked dataset version registry
- `runs/registry/`: tracked run and promotion registries
- `results/aggregate/`: tracked aggregate CSVs
- `paper/`: canonical paper sources and notes

## Workflow rules

1. Every formal experiment starts from a committed, clean worktree.
2. Every formal run must emit a `manifest.yaml`.
3. Aggregation reads registries, not ad-hoc directory selections.
4. Paper claims must map to figures, aggregate CSVs, and promoted runs.

See `docs/workflows/experiment_workflow.md` and `docs/workflows/git_workflow.md` for the
operational rules.

## Local Validation

For resource-constrained local reruns, use the reduced `v3_local` experiment configs documented in
[`docs/workflows/local_v3_workflow.md`](/Users/jiyuan/Desktop/HiRoute/docs/workflows/local_v3_workflow.md).
These runs are for local validation only; the full paper-facing matrices still require the official
`exp_*_v3.yaml` configs.
For an even smaller routing-only sanity pass, start with
[`exp_routing_main_v3_local_lite.yaml`](/Users/jiyuan/Desktop/HiRoute/configs/experiments/exp_routing_main_v3_local_lite.yaml).
