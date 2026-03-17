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

## Current machine path

The current paper-facing path on this machine is the compact-medium `v3` route documented in
[`docs/workflows/compact_v3_workflow.md`](/Users/jiyuan/Desktop/HiRoute/docs/workflows/compact_v3_workflow.md).
It preserves the full `smartcity_v3` query bundles and the full routing/object baseline sets while
replacing the original Rocketfuel 3967 topology with a domain-preserving compact derivative.

## Debug and smoke paths

[`docs/workflows/local_v3_workflow.md`](/Users/jiyuan/Desktop/HiRoute/docs/workflows/local_v3_workflow.md)
documents the reduced `v3_local` and `v3_local_lite` configs. Those runs are debug/smoke-only and
must not be treated as paper-facing evidence.

## Full official path

The original `exp_*_v3.yaml` configs remain in the repository for future higher-memory reruns on
the uncompressed `rf_3967_exodus` and `rf_1239_sprint` topologies.
