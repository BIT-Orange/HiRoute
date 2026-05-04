# Figure 3-9 Current Audit

Last checked: 2026-05-04

This note consolidates the current evidence status for the paper figures that are now bound to the mainline outputs. It is intentionally conservative: a figure is paper-facing only if its data path is traceable and its wording does not claim more than the current metric semantics support. Dirty-tree outputs remain diagnostic until rerun, validated, and promoted from a clean tree.

## Summary

| Figure | Label | Artifact | Current supported role | Current status | Blocker or caution |
| --- | --- | --- | --- | --- | --- |
| 3 | `fig:ablation` | `results/figures/mainline/fig_ablation_summary.pdf` | Fixed-manifest mechanism diagnostic using terminal strong success, first-fetch strong correctness, and discovery cost. | Diagnostic/blocking under the local stage decision. | `review_artifacts/ablation/aggregate/ablation_decision.json` currently says `rerun_needed`; manifest size 1 gap is small and byte ordering is not clean. |
| 4 | `fig:main` | `results/figures/mainline/fig_routing_support.pdf` | Diagnostic routing-support comparison: first relevant-domain reach, discovery bytes, and staged contraction. | Diagnostic only. | Scoped traceability passes with `review_artifacts/routing_main/run_ids.txt`, but the promoted-run figure gate still fails because promoted routing runs are stale/missing or below the 240-query threshold. |
| 5 | `fig:waterfall` | `results/figures/mainline/fig_object_manifest_sweep.pdf` | Object-resolution fallback/rescue diagnostic across manifest sizes. | Semantically supportable but blocked for final readiness by the dirty worktree. | Supports bounded fallback after weak first choices; it does not support a strong first-object top-1 ranking claim. |
| 6 | `fig:shrinkage` | `results/figures/mainline/fig_candidate_shrinkage.pdf` | Diagnostic candidate-contraction evidence for bounded hierarchical filtering and refinement. | Diagnostic only. | Current scoped traceability passes after filtering search traces to query-log query IDs, but the routing promoted-run figure gate remains unrepaired. |
| 7 | `fig:latency` | `results/figures/mainline/fig_deadline_summary.pdf` | Diagnostic deadline/latency tradeoff on the routing-support workload. | Diagnostic only. | Same routing promoted-run blocker as Figures 4 and 6; also not a universal HiRoute latency advantage because the centralized directory is a non-peer low-latency reference. |
| 8 | `fig:state` | `results/figures/mainline/fig_state_scaling.pdf` | State-only bounded exported-summary evidence on the larger topology. | Semantically supportable but blocked for final readiness by the dirty worktree. | Query-side success, latency, and bytes are intentionally undefined; do not present as end-to-end runtime effectiveness. |
| 9 | `fig:robust` | `results/figures/mainline/fig_robustness.pdf` | Diagnostic degradation profile under stale summaries and controller failures. | Diagnostic only. | Local registry points to missing `runs/completed/...` raw run directories; stage-copy logs exist, but raw-run provenance must be restored or rerun cleanly before promotion. |

## Paper Claim Boundary

The current paper text may claim that HiRoute's implemented path supports bounded hierarchical discovery and recovery when those claims are tied to the checked aggregates:

- Figure 3: Full HiRoute is best on terminal strong success in the fixed-manifest ablation slice, but the margin is small and the local ablation decision remains `rerun_needed`.
- Figure 4: HiRoute improves first relevant-domain reach and contracts the frontier more strongly than distributed search controls in the scoped diagnostic slice.
- Figure 5: Wider manifests produce observable fallback rescue at manifest sizes 2 and 3, especially for HiRoute at size 3.
- Figure 6: Candidate contraction explains the bounded-search mechanism, not a universal cost or latency win.
- Figure 7: Latency is a tradeoff, not an independent superiority proof.
- Figure 8: Exported state follows the configured budget/active-domain surface; this is state-only evidence.
- Figure 9: Robustness is a degradation profile; the controller-down case is HiRoute-specific and the stale-summary stressor is currently weak.

The paper may describe the current application-level query-summary and query-object embedding scoring path only when it is tied to the C++ runtime that consumes those embedding rows. The figures still must not be used to claim forwarding-plane semantic reasoning, true first-object top-1 correctness, universal discovery-byte superiority, universal latency superiority, or clean robustness superiority over centralized directory.

## Current Aggregate Snapshot

These values are useful for sanity-checking whether the current figures can truthfully be presented as "HiRoute is best" comparisons.

| Evidence point | Current value | Interpretation |
| --- | --- | --- |
| Figure 3, manifest 1 ablation | `full_hiroute` terminal strong success `0.141667`; next best shown in the manifest-1 slice is `predicates_plus_flat` at `0.133333`. | HiRoute is highest, but the gap is small. |
| Figure 4, budget 16 routing support | `hiroute` first relevant-domain reach `0.673729`; `random_admissible` `0.59375`; `predicates_only` `0.478632`; `inf_tag_forwarding` `0.367965`. | Supports a relevant-domain reach claim against distributed controls. |
| Figure 4, budget 16 discovery bytes | `hiroute` `486.567797`; `inf_tag_forwarding` `528.800866`; `flood` `223.75`; `central_directory` `130.408333`. | Supports lower cost than INF-style tag forwarding only, not lower cost than every control. |
| Figure 5, manifest 3 object resolution | `hiroute` terminal strong success `0.591667`, first-fetch strong correctness `0.0875`, manifest rescue `0.45`. | Supports fallback/rescue, not first-object top-1 correctness. |
| Figure 7, 500 ms deadline | `hiroute` success-before-deadline `0.449153`; `flood` `0.8375`; `central_directory` remains a low-latency reference. | Does not support a universal latency or deadline advantage. |
| Figure 8, state scaling | `query_count=0`; exported summaries grow from `64` to `256` with active-domain count and stay at `256` under object-density growth. | State-only bounded-summary evidence, not runtime success evidence. |
| Figure 9, robustness | `hiroute` min success after `controller_down` is `0.727273`; stale summaries remain `1.0`; central directory is `1.0` in both variants. | Degradation-profile evidence only; no blanket robustness win. |

## Validation Snapshot

- `.venv/bin/python tools/audit_mainline_figure_readiness.py --markdown` currently exits nonzero and marks every Figure 3--9 row as `diagnostic/blocking` because `worktree_gate=dirty(...)`; Figures 3, 4, 6, 7, and 9 also have figure-specific blockers. The audit now also checks each figure note's `caption target` against the live `paper/main.tex` caption and runs `tools/audit_paper_claim_hygiene.py`; all current Figure 3--9 `note_caption` and `claim_hygiene` checks report `ok`.
- `configs/experiments/routing_main.yaml` and `configs/experiments/robustness.yaml` now use `runner.params.stopSeconds=48` for the next clean rerun, because current 32-second routing logs under-count some slow schemes despite a 240-query eligible slice.
- `.venv/bin/python tools/validate_query_count_gate.py --experiment configs/experiments/routing_main.yaml --registry-source runs --run-ids-file review_artifacts/routing_main/run_ids.txt` currently fails with scoped routing counts of `224`--`236` for the distributed routing schemes.
- `.venv/bin/python tools/validate_query_count_gate.py --experiment configs/experiments/robustness.yaml --registry-source runs --run-ids-file review_artifacts/robustness/run_ids.txt` currently fails because the registry-side robustness run directories are missing `query_log.csv`.
- `tools/run_mainline_review_stage.py` now runs `validate_query_count_gate.py` before `promote_runs.py` in the full object_main, ablation, routing/state/robustness stage paths, so future under-counted reruns should fail before promotion.
- The current scoped `object_main` and `ablation` run-id files pass `tools/validate_query_count_gate.py` at the 240-query threshold.
- `tools/run_mainline_review_stage.py paper_freeze` now runs `tools/audit_mainline_figure_readiness.py --markdown` after regenerating the mainline figures, so paper freeze should fail until every Figure 3--9 readiness row is paper-facing checked.
- A dry run of `tools/run_mainline_review_stage.py paper_freeze --dry-run --max-workers 1` currently stops before that final audit because `object_main_quick` has a dataset-fingerprint mismatch against the current full stage. This is another reason a clean source-sync/rerun sequence is required before paper freeze.
- `tools/validate_run.py --mode dry` passed for representative ablation, object_main, routing_main, and robustness run IDs.
- `tools/validate_figures.py` passed for ablation, object_main, and state_scaling, but the stricter readiness audit now also checks stage-decision eligibility and worktree cleanliness; it blocks Figure 3 on `ablation_decision=rerun_needed` and blocks all rows while the worktree is dirty.
- A fresh temporary rebuild of the ablation decision with `scripts/eval/build_stage_decision.py --stage ablation` also returns `decision: rerun_needed`, so the Figure 3 blocker is not just a stale JSON file.
- Current `tools/validate_figures.py --experiment configs/experiments/routing_main.yaml` fails for routing-support, candidate-shrinkage, and deadline aggregates because promoted routing runs do not satisfy the configured 240-query threshold for all required schemes and budget tiers.
- Current `tools/validate_figures.py --experiment configs/experiments/robustness.yaml` fails because promoted robustness runs do not satisfy the configured 240-query threshold for `hiroute@rf_3967_exodus_compact@budget16` and `central_directory@rf_3967_exodus_compact@budget16`.
- `tools/validate_aggregate_traceability.py --experiment configs/experiments/routing_main.yaml --registry-source runs --run-ids-file review_artifacts/routing_main/run_ids.txt` passes for the scoped diagnostic routing aggregates after the candidate-shrinkage filter fix.
- Current `tools/validate_aggregate_traceability.py --experiment configs/experiments/robustness.yaml --registry-source runs` fails because registry-referenced robustness run directories are missing `query_log.csv` under `runs/completed/`.

## Prompt-to-Artifact Checklist

| Requirement | Artifact or evidence | Status |
| --- | --- | --- |
| Organize current experiments/data with the paper for Figures 3-9. | This note maps Figure 3-9 labels, figure files, aggregate sources, claim boundaries, validator status, and blockers. | Done. |
| Focus on Figures 3, 4, 5, 6, 7, 8, and 9. | The summary table covers exactly Figures 3-9. | Done. |
| Find unsupported parts of the paper. | Unsupported universal superiority, top-1 object correctness, latency, byte-cost, robustness, stale failure-breakdown, stale ablation figure-number, and forwarding-plane semantic-reasoning claims are listed in the claim boundary and reflected in `paper/main.tex` plus `paper/notes/claim_c001.md`--`paper/notes/claim_c004.md`; application-level embedding scoring is allowed only where tied to the current C++ path. | Done for current evidence. |
| Modify unsupported paper text. | `paper/main.tex` now labels routing, deadline, candidate-contraction, and robustness as diagnostic until gates pass; Figure 8 is state-only; Figure 5 is fallback/rescue rather than first-object top-1 proof. The introduction, methodology, algorithm, implementation-boundary, and conclusion wording now describe readiness-bounded evidence rather than closed validation of every mechanism component. `paper/notes/claim_c001.md`--`paper/notes/claim_c004.md` no longer preserve stale lower-cost, failure-breakdown, robustness, or old Figure-10 ablation wording. The Figure 3--9 note captions now match the live `paper/main.tex` captions and are covered by the readiness audit. `tools/audit_paper_claim_hygiene.py` now guards the known stale/over-strong wording patterns. | Done. |
| Keep experiment comparisons real. | Current aggregate values are recorded above; claims are narrowed where HiRoute is not actually best. | Done for wording; not enough for final promotion. |
| Make all figures visibly prove HiRoute is the most effective scheme. | `scripts/plots/plot_main_figures.py` now visually emphasizes HiRoute/Full HiRoute consistently and improves readability where small gaps or long labels were previously hard to see, but current data do not support this evidence claim for every figure: flood/central directory dominate some terminal success, byte, latency, state/reference, or robustness views. | Presentation improved; evidence requirement not achieved. Requires clean rerun, workload redesign, or legitimate metric/figure redesign, not cosmetic editing. |
| Preserve provenance and avoid manual generated-artifact edits. | Generated outputs are not hand-edited; candidate-shrinkage was regenerated through the script path. Dirty-tree outputs remain diagnostic. | Done so far. |
| Pass paper-facing gates. | `.venv/bin/python tools/audit_mainline_figure_readiness.py --markdown` marks every Figure 3--9 row as `diagnostic/blocking` under the current dirty worktree; Figure 3 is additionally blocked by `ablation_decision=rerun_needed`, routing figure gates fail, and robustness provenance/gate still fail. The stage workflow now has a pre-promotion query-count gate for future reruns. | Not achieved. |

## Next Required Repairs

1. Repair or rerun ablation until `review_artifacts/ablation/aggregate/ablation_decision.json` no longer reports `rerun_needed`.
2. Repair the routing promotion path by rerunning and promoting `routing_main` from a clean tree with the 48-second horizon so that the promoted run set satisfies the 240-query figure gate.
3. Repair robustness raw-run provenance by rerunning and promoting robustness cleanly with the 48-second horizon, or by restoring the exact completed run directories through an auditable provenance-preserving procedure.
4. Before promotion, run `tools/validate_query_count_gate.py` on the new scoped run-id files to confirm every required scheme/budget/variant reaches the 240-query threshold.
5. Restore a clean worktree before treating any Figure 3--9 row as paper-facing readiness evidence.
6. Keep Figures 3, 4, 6, 7, and 9 labeled as diagnostic until the gates above pass.
7. Do not promote any dirty-tree aggregate or figure into the paper claim set.

## Clean Rerun Plan

Do not run this as paper-facing work from the current dirty tree. First isolate or commit the current edits so `git status --short` is clean. Then run the active mainline workflow in order:

```bash
tools/run_mainline_review_stage.sh source_sync
tools/run_mainline_review_stage.sh object_ablation_routing --max-workers 1
tools/run_mainline_review_stage.sh full_mainline --max-workers 1
tools/run_mainline_review_stage.sh paper_freeze --max-workers 1
```

The clean rerun is acceptable for Figure 3--9 paper-facing use only if all of the following hold:

| Gate | Required evidence |
| --- | --- |
| Clean source state | `git status --short` is empty before promotion/freeze. |
| Figure 3 ablation | `review_artifacts/ablation/aggregate/ablation_decision.json` reports an allowed readiness decision rather than `rerun_needed`. |
| Routing query-count gate | `tools/validate_query_count_gate.py --experiment configs/experiments/routing_main.yaml --registry-source runs --run-ids-file review_artifacts/routing_main/run_ids.txt` passes at the 240-query threshold. |
| Robustness query-count/provenance gate | `tools/validate_query_count_gate.py --experiment configs/experiments/robustness.yaml --registry-source runs --run-ids-file review_artifacts/robustness/run_ids.txt` passes, and `tools/validate_aggregate_traceability.py --experiment configs/experiments/robustness.yaml --registry-source runs` finds the raw `query_log.csv` files. |
| Figure binding | `tools/validate_figures.py` passes for `routing_main`, `object_main`, `ablation`, `state_scaling`, and `robustness`. |
| Claim hygiene | `tools/audit_paper_claim_hygiene.py --markdown` exits zero. |
| Final Figure 3--9 readiness | `tools/audit_mainline_figure_readiness.py --markdown` exits zero with every row marked `paper-facing checked`. |

If any gate fails, the corresponding figure remains diagnostic/support only and the paper text must keep the current narrowed wording.
