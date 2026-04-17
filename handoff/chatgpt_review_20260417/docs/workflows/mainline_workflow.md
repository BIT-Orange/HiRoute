# Mainline Workflow

This is the only active paper-facing workflow. The mainline source of truth is:

1. code/configs
2. completed run logs and registry rows
3. `results/{aggregate,figures,tables}/mainline/`
4. `paper/` and `docs/`

## Active contract

- dataset config: `configs/datasets/smartcity.yaml`
- hierarchy config: `configs/hierarchy/hiroute_hkm.yaml`
- experiment configs:
  - `configs/experiments/object_main.yaml`
  - `configs/experiments/ablation.yaml`
  - `configs/experiments/routing_main.yaml`
  - `configs/experiments/state_scaling.yaml`
  - `configs/experiments/robustness.yaml`
- outputs:
  - `results/aggregate/mainline/`
  - `results/figures/mainline/`
  - `results/tables/mainline/`

## Fixed stage runner

Use `tools/run_mainline_review_stage.sh` as the only active orchestration entrypoint.

```bash
tools/run_mainline_review_stage.sh source_sync --mode official
tools/run_mainline_review_stage.sh full_mainline --mode official --max-workers 6
tools/run_mainline_review_stage.sh paper_freeze --mode official --max-workers 6 --force-rerun
```

Dry-run must print the exact command order without mutating the repo:

```bash
tools/run_mainline_review_stage.sh source_sync --dry-run
tools/run_mainline_review_stage.sh full_mainline --dry-run --max-workers 6
```

`full_mainline` is the only official five-experiment entrypoint. It must execute, in order:

1. `object_main_quick`
2. `object_main`
3. `ablation_quick`
4. `ablation`
5. `routing_main`
6. `state_scaling`
7. `robustness`

The stage runner does not set `HIROUTE_ALLOW_DIRTY_WORKTREE` unless `--allow-dirty-worktree` is passed explicitly. Official reruns should omit that flag.

The stage runner now maintains two fingerprint layers:

- `simulation_fingerprint`: ndnSIM-relevant experiment fields plus `scripts/run/run_experiment.py` and referenced baseline/topology/hierarchy/dataset configs
- `stage_contract_fingerprint`: promotion/measurement/output contract plus the gate/aggregate/figure tooling for that stage

Reuse policy is:

- dataset/binary/simulation fingerprint changed: rerun ndnSIM assignments for that experiment
- only stage-contract fingerprint changed: reuse completed runs and refresh validations, aggregates, and figures
- no fingerprint changed: skip simulation and only refresh the minimal stage metadata needed for traceability

Use `--force-rerun` only when you explicitly want a from-scratch rerun of every assignment.

## Gate order per experiment

For `object_main`, `ablation`, `routing_main`, `state_scaling`, and `robustness`, the stage runner applies the same serial gates:

1. `tools/validate_run.py --mode dry`
2. `scripts/run/run_experiment_matrix.py` with `--max-workers 6` by default for active reruns; if one stage hits contention, rerun only that stage at `--max-workers 4`
3. `tools/validate_runtime_slice.py`
4. `tools/validate_manifest_regression.py` for `object_main` and `ablation`
5. `scripts/eval/promote_runs.py`
6. `scripts/eval/aggregate_experiment.py`
7. `tools/validate_aggregate_traceability.py`
8. `scripts/plots/plot_experiment.py`
9. `tools/validate_figures.py`

Figure notes and the main paper text stay in `pending rerun` language until gates `1-9` pass for the relevant experiment.

## Required dataset checks

- `data/processed/eval/workload_audit_mainline.json` must exist.
- `routing_main` runtime queries must have `zone_constraint` coverage `1.0`.
- `routing_main` relevant-domain support must cover `2`, `3`, and `4`.
- `object_main` relevant-domain support must cover `1` and `2`.
- `object_main` confuser-object counts must have non-zero variance.

## Rerun order

1. Incremental refresh:
   `source_sync --mode official`
   `full_mainline --mode official --max-workers 6`
2. Full fresh rerun:
   `source_sync --mode official`
   `full_mainline --mode official --force-rerun --max-workers 6`

## Review bundles

The active bundle path is explicit-whitelist only:

- `tools/package_review_bundle.sh source_sync`
- `tools/package_review_bundle.sh run_review_object_ablation_routing`

Bundle manifests live in:

- `tools/review_manifests/source_sync.txt`
- `tools/review_manifests/run_review_object_ablation_routing.txt`

The legacy `scripts/review/build_review_bundles.sh` script is retained only for archive compatibility and must not be used for mainline review.

## Cache and build policy

- `source_sync` and the first rerun stage may reuse cached dataset artifacts, but `checks.txt` must state that cache reuse occurred and that `audit_query_workloads.py` and `validate_dataset.py` passed.
- `paper_freeze` must run `scripts/build_dataset/build_all.py` to natural completion before the workflow can claim full reproducibility.

## Figure policy

- Figure 4 is `fig_routing_support.pdf`; if success saturates, the headline stays on `RelevantDomain@1` and discovery cost.
- Figure 5 is `fig_object_manifest_sweep.pdf`; treat it as a support figure showing terminal success versus first-fetch correctness, with manifest rescue reported in the aggregate.
- `failure_breakdown.csv` is appendix diagnostics only.
- Figure 10 is the main Route B mechanism figure; keep the narrative centered on predicate elimination, hierarchical refinement, manifest fallback, and reliability-aware suppression.
- Figures 8 and 9 stay `pending rerun` until `state_scaling` and `robustness` are promoted under mainline.
