# HiRoute Autoresearch Runbook

This file is retained as a compatibility entry point only.

## Status

- The active paper-facing line is `mainline`, not `compact-v3`.
- The active dataset is `configs/datasets/smartcity.yaml`.
- The active hierarchy is `configs/hierarchy/hiroute_hkm.yaml`.
- The active experiments are `object_main`, `ablation`, `routing_main`, `state_scaling`, and `robustness`.
- The active outputs live under `results/{aggregate,figures,tables}/mainline/`.

## Use instead

- Primary workflow: `docs/workflows/mainline_workflow.md`
- Legacy experiment lineage: `runs/registry/experiment_lineage.csv`
- Legacy compact-v3 notes: `docs/workflows/compact_v3_workflow.md`

## Mainline reminders

- `routing_main` and `object_main` now require non-empty `zone_constraint`.
- `routing_main` workload support must cover relevant-domain counts `2`, `3`, and `4`.
- `object_main` workload support must cover relevant-domain counts `1` and `2`.
- `failure_breakdown.csv` is appendix diagnostics only; the active Figure 5 asset is `fig_object_manifest_sweep.pdf`.
- Figures 8 and 9 stay `pending rerun` until mainline scaling and robustness runs are promoted.

After each experiment matrix completes, record a short structured decision note in `paper/notes/revision_log.md` or another dedicated note under `paper/notes/`.

Recommended format is a short block containing date, experiment, observation, decision, impact on paper figures, and next action.

### 10.5 Figure registry updates

After promoted aggregates are generated, update `docs/experiments/figure_registry.md`. Every paper-facing figure must record the experiment id, aggregate source, paper role, and whether it is main, support, or appendix.

## 11. How Codex Should Make Decisions Autonomously

Codex may autonomously rebuild datasets and topology artifacts, run dry validation, run compact experiment matrices in the required order, aggregate and plot results, update figure registry and notes, and downgrade figures from main to support if metrics saturate and no longer support the intended claim.

Codex must stop and ask for confirmation before changing workload semantics or qrels logic, changing the baseline set for paper-facing experiments, changing topology family away from the compact path, changing the main claim of the paper, or deleting past promoted results.

Codex may automatically downgrade a figure from main to support if its headline metric saturates for all compared methods, if it no longer discriminates methods under the current fairness rules, or if another figure now contains the clearest signal for the paper’s claim. If compact routing success remains saturated, Figure 4 stays support-only.

Codex must stop and emit a decision note if compact object main also saturates with no meaningful gap, ablation collapses with no separation at `manifest_size = 1`, runtime repeatedly exceeds machine capacity, or aggregates are inconsistent with figure validation.

## 12. Fault Handling and Recovery

If a run crashes or stalls, check whether the run was written into `runs.csv`, whether `manifest.yaml` exists, and inspect `stdout.log` and `stderr.log`. If the run has partial files but no valid completion record, do not promote it. Re-run only the missing matrix entries.

If memory usage becomes unsafe, stop the active matrix, do not start a second matrix, record the failure in a note, and resume from the smallest unfinished paper-facing matrix rather than from support experiments.

If validation fails after aggregation, read `validate_figures.py` output, determine whether the failure is due to missing promoted runs, missing schemes, wrong aggregate path, or mixed-version outputs, then fix the root cause and re-run aggregation and validation.

If compact routing remains saturated, do not keep re-running the same matrix. Keep Figure 4 as support-only, continue with object and ablation as main paper evidence, and only revisit routing workload redesign if explicitly requested.

If object-hard signal disappears, stop and report the current object main aggregate, the ablation aggregate, whether `manifest_size = 1` still has any separation, and whether `wrong_object_rate` still differs. Do not continue polishing figures if the signal has disappeared.

## 13. Commands for End-to-End Current-Machine Paper Path

### 13.1 Build

```bash
cd /path/to/HiRoute
.venv/bin/python scripts/build_dataset/build_all.py --config configs/datasets/smartcity_v3.yaml
python3 scripts/build_dataset/build_topology_mapping.py --topology-config configs/topologies/rocketfuel_3967_exodus_compact.yaml
```

### 13.2 Validate

```bash
python3 tools/validate_run.py --experiment configs/experiments/exp_object_main_v3_compact.yaml --scheme hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_ablation_v3_compact.yaml --scheme full_hiroute --seed 1 --manifest-size 1 --mode dry
python3 tools/validate_run.py --experiment configs/experiments/exp_routing_main_v3_compact.yaml --scheme hiroute --seed 1 --budget 16 --mode dry
```

### 13.3 Run main matrices

```bash
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_object_main_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_ablation_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_routing_main_v3_compact.yaml --max-workers 1 --postprocess --validate
```

### 13.4 Run support matrices

```bash
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_scaling_v3_compact.yaml --max-workers 1 --postprocess --validate
python3 scripts/run/run_experiment_matrix.py --experiment configs/experiments/exp_robustness_v3_compact.yaml --max-workers 1 --postprocess --validate
```

### 13.5 Figure validation examples

```bash
python3 tools/validate_figures.py --experiment configs/experiments/exp_object_main_v3_compact.yaml --aggregate results/aggregate/v3/compact/object_main_manifest_sweep.csv
python3 tools/validate_figures.py --experiment configs/experiments/exp_ablation_v3_compact.yaml --aggregate results/aggregate/v3/compact/ablation_summary.csv
python3 tools/validate_figures.py --experiment configs/experiments/exp_routing_main_v3_compact.yaml --aggregate results/aggregate/v3/compact/main_success_overhead.csv
```

### 13.6 Review bundle generation

```bash
scripts/review/build_review_bundles.sh
```

## 14. Expected Autonomous Research Loop for Codex

Codex should follow this loop. Build dataset and compact topology. Validate all target experiment configs. Run `object_main`. Promote, aggregate, plot, and validate. Decide whether Figure 5 is main-paper ready. Run `ablation`. Promote, aggregate, plot, and validate. Decide whether Figure 10 is mechanism-ready. Run `routing_main`. Promote, aggregate, plot, and validate. Treat Figure 4 as support unless routing compact becomes meaningfully discriminative. Run scaling and robustness only after the main evidence chain is in place. Update figure registry and revision log. Stop if the main object-level signal disappears or if runtime exceeds safe machine limits.

## 15. Final Current-State Guidance

For the current machine path, the most realistic paper-facing interpretation is the following. The strongest signal is in object-level semantic name resolution. Compact routing is best interpreted as search-efficiency support evidence. Scaling and robustness are support evidence. The compact medium path is a resource-bounded but paper-facing evaluation route. Local and local-lite remain debug and smoke-only.

This runbook should be treated as the authoritative execution guide for Codex unless a human explicitly revises the paper strategy.
