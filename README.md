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
