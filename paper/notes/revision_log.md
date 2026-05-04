# Revision Log

## 2026-05-04

- Audited the current Figure 3--9 paper path against the mainline aggregates and validation gates. The paper now treats Figure 3 as a fixed-manifest diagnostic, Figure 5 as an object-resolution fallback/rescue diagnostic, Figure 8 as state-only bounded-state evidence, and Figures 4/6/7/9 as diagnostic support until their promotion/provenance gates are repaired.
- Re-audited Figures 3--9 against current local stage decisions. The active local status is now `object_main = support_only_figure`, `ablation = rerun_needed`, and `routing/robustness` remain diagnostic until their promoted-run query-count and raw-run provenance gates are repaired.
- Updated `paper/main.tex` so it no longer claims a clean, standalone HiRoute superiority result from the manifest-1 ablation, routing-support, deadline, or robustness figures. The supportable current story is bounded hierarchical discovery and recovery: improved relevant-domain reach, explicit candidate contraction, and measurable bounded-fallback rescue at wider manifests, with first-fetch object-ranking limitations left visible.
- Tightened the introduction, algorithm, implementation-boundary, and conclusion wording so the evaluation is described as readiness-bounded evidence rather than as a fully closed validation of every mechanism component.
- Updated `paper/notes/claim_c001.md` through `claim_c004.md` so reusable claim notes no longer preserve stale lower-cost, failure-breakdown, robustness, or old Figure-10 ablation wording that is stronger than the current local evidence.
- Aligned the Figure 3--9 note files with the current captions and readiness audit: routing, candidate-contraction, deadline, and robustness notes are diagnostic/blocking; object-resolution and state-scaling notes are support-only until the worktree is clean.
- Updated ablation-related script, bundle, and skill text that still referred to the current ablation figure as Figure 10; future placeholders and stage-decision stdout now use Figure 3.
- Added `tools/audit_paper_claim_hygiene.py` and wired it into `tools/audit_mainline_figure_readiness.py` so stale/over-strong paper wording such as old Figure-10 ablation authority, universal lower-cost claims, and stale robustness captions fail the readiness audit.
- Fixed `scripts/eval/build_candidate_shrinkage.py` so staged search traces are filtered to query IDs that also appear in `query_log.csv` before aggregation. This prevents `candidate_shrinkage.csv` from declaring a `query_count` larger than the source query log.
- Regenerated the diagnostic routing figure artifacts through `scripts/plots/plot_experiment.py --experiment configs/experiments/routing_main.yaml` and refreshed `candidate_shrinkage.csv` plus its trace JSON with scoped run IDs. `tools/validate_aggregate_traceability.py --experiment configs/experiments/routing_main.yaml --registry-source runs --run-ids-file review_artifacts/routing_main/run_ids.txt` now passes.
- Updated `scripts/plots/plot_main_figures.py` so HiRoute/Full HiRoute receives consistent visual emphasis and centralized references are lower-emphasis dashed/reference curves where applicable. Regenerated Figure 3--9 mainline assets through the plotting workflow; this changes presentation only, not aggregate values.
- Added `tools/audit_mainline_figure_readiness.py` as a read-only Figure 3--9 completion audit. It checks figure files, aggregate files, figure-note caption alignment, promoted-run figure gates, stage-decision eligibility for ablation/object_main, raw `query_log.csv` provenance, and git worktree cleanliness. It currently exits nonzero because Figure 3 is blocked by `ablation_decision=rerun_needed`, Figures 4/6/7 still fail the promoted routing query-count gate, Figure 9 still fails robustness query-count/raw-run provenance checks, and the worktree is dirty.
- Increased `runner.params.stopSeconds` from `32` to `48` in `configs/experiments/routing_main.yaml` and `configs/experiments/robustness.yaml` for the next clean rerun. Current 32-second routing logs schedule late queries around 27.9 s, so slow timeout/retry cases can remain unlogged at simulation stop even though the eligible query slice is 240.
- Added `tools/validate_query_count_gate.py` to check scoped run-id files against the promotion query-count threshold before promotion. It currently reports routing counts of `224`--`236` for distributed routing schemes and missing registry-side robustness query logs.
- Wired `validate_query_count_gate.py` into `tools/run_mainline_review_stage.py` before `promote_runs.py` for the full object_main, ablation, and generic mainline stages. Dry runs for `object_main`, `ablation`, `routing_main`, and `robustness` show the new gate in the expected pre-promotion position; current scoped `object_main` and `ablation` run-id files pass it at the 240-query threshold.
- Wired `tools/audit_mainline_figure_readiness.py --markdown` into the `paper_freeze` stage after mainline figure rendering. A dry run shows the readiness audit command writing to `review_artifacts/paper_freeze/validation/paper_freeze_audit_mainline_figure_readiness.txt`.
- A later `paper_freeze --dry-run` stops earlier on an `object_main_quick` dataset-fingerprint mismatch, so the next paper-facing attempt must begin with a clean source-sync/rerun sequence rather than a direct freeze.
- Added a clean Figure 3--9 rerun plan to `paper/notes/fig_3_9_current_audit.md`, including the required workflow command order and the exact acceptance gates for ablation, routing, robustness, figure binding, claim hygiene, and final readiness.
- Current blockers: `tools/validate_figures.py` still fails for routing-support, candidate-shrinkage, and deadline figures because the promoted routing runs do not satisfy the configured 240-query threshold; it also fails for robustness because the registry points to missing `runs/completed/...` raw run directories. These figures must not be promoted or described as paper-ready until a clean rerun/promotion or raw-run restoration resolves those gates.

## 2026-04-19

- Adopted Phase 2 metric semantics (documented in `docs/metrics/metric_semantics.md`): `handleFetchReply` at `ns-3/src/ndnSIM/apps/hiroute-ingress-app.cpp:1047` uses `isStrongRelevantObject` (qrel grade `>= 2`) uniformly for `firstFetchRelevant`, sequential manifest fallback, and terminal `finishActiveQuery` outcome. Expect `success_at_1` for `hiroute` on the compact `object_main` workload to drop from the current sealed `1.0` into the `0.6–0.8` band once the full rerun completes; Phase 1 sealed aggregates remain authoritative until then.
- Added `cumulative_manifest_fetches` column to the `query_log.csv` schema produced by the ingress app. The new counter increments at both manifest-fallback sites (`hiroute-ingress-app.cpp:974` and `:1060`) and is reset only when a fresh `ActiveQueryState` starts, so cross-probe manifest rescue is now observable.
- Split `manifest_rescue_rate` into `within_reply_manifest_rescue_rate` and `cross_probe_manifest_rescue_rate` across `build_object_main_manifest_sweep.py`, `build_ablation_summary.py`, `aggregate_query_metrics.py`, `build_stage_decision.py`, and `build_stage_quick_summary.py`. Legacy `manifest_rescue_rate` is aliased to `within_reply_manifest_rescue_rate` for one release cycle. Stage gating (`hiroute_manifest_rescue_signal`, `hiroute_support_signal`) now accepts either rescue variant, so a cross-probe rescue regime (where each probe returns a fresh manifest) is no longer silently coded as "no signal".
- Rewrote `paper/notes/claim_c002.md` to "domain-selection dominated" so the text matches the current sealed `failure_breakdown.csv` (wrong_object = 0 across schemes; the only non-zero term is inf_tag_forwarding wrong_domain = 0.0917).
- Extended `paper/notes/fig_robustness.md` interpretation to make the controller_down scenario explicitly HiRoute-specific (central_directory does not depend on per-domain controllers) and to flag that the current stale_summaries parameters (`staleDropProbability=0.5`, `manifestSize=5`) are a weak stressor.
- Extended `paper/notes/fig_deadline_summary.md` interpretation to call out HiRoute's structural controller-to-ingress RTT as the source of its higher latency on the routing-support workload, so captions do not read the gap as an optimization opportunity.
- Outstanding work before promotion: full `object_main` / `ablation` / `robustness` rerun under the Phase 2 semantics; object_main workload redesign per `/object-main-redesign`; adversarial `stale_summaries` variant in `configs/experiments/robustness.yaml`; and paper caption pass after all reruns land under a clean tree.

## 2026-03-12

- Initialized the paper-side workflow for figure-to-claim traceability.
- Reserved `paper/main.tex` as the canonical paper entry point for later migration.
- Migrated the existing IoTJ draft to `paper/main.tex`.
- Bound `fig_main_success_overhead` to `exp_main_v1` promoted runs and aggregate CSVs.
- Locked the first scoped claim to object-level success versus discovery overhead instead of broad latency claims.
- Added formal Figure 4-10 aggregate and PDF output paths to the workflow.
- Bound Figure 5, 6, 7, 8, 9, and 10 note files and claim stubs to explicit aggregate CSVs.
- Replaced the paper placeholders for Figure 4-10 with `\includegraphics` bindings to `results/figures/*.pdf`.
- Kept Figure 8 and Figure 9 in placeholder-PDF mode until official scaling and robustness runs are promoted.

## 2026-03-13

- Replaced the provisional `hiroute` promoted runs with the final multi-probe ndnSIM reruns on `rf_3967_exodus` and `rf_1239_sprint`.
- Updated the main claim from an incorrect "lower overhead than flood" framing to the actual tradeoff: higher object-level success at higher discovery cost.
- Promoted official Figure 8, Figure 9, and Figure 10 inputs and removed the remaining placeholder language from the paper notes.
- Bound `exp_ablation_v1` into the experiment matrix and figure registry as the formal source for Figure 10.
- Strengthened the Figure 9 failure injections to target the dominant query domain and earlier failure windows, which exposed a real robustness weakness in the current HiRoute implementation instead of the earlier near-flat curves.
- Aligned the default hierarchy with the paper's `zone + service` predicate cells and rebuilt the dataset artifacts under the new hierarchy version.
- Replaced the old predicate-only Figure 6 instrumentation with explicit staged frontier traces through predicate filtering, level-1 expansion, refinement, probing, and manifest return.
- Reworked Figure 8 into the paper's intended fixed-budget object/domain sweep, which now shows flat exported state under object growth and near-linear growth under active-domain expansion.
- Expanded the formal Smart Data Models workload to sixteen active data domains and added topology-aware runtime slicing so `rf_3967_exodus` and `rf_1239_sprint` exercise eight and sixteen active domains respectively.
- Tightened Figure 8 to a state-only scenario and reran its official inputs so the large Rocketfuel topology now reaches `16` active domains and `256` exported summaries under the fixed budget.
- Repaired the HiRoute reliability path by fixing the domain-id/cache mismatch, adding domain-aware negative suppression, and replanning after failed probes.
- Reran the official Figure 9 inputs after the fallback repair; `hiroute` now recovers to `0.868852` under staleness, `0.803279` under link failure, and `0.688525` under domain failure.
- Corrected the `oracle` baseline from a mislabeled domain-local controller into a true centralized semantic directory keyed by `qrels_object.csv`.
- Removed `exact` from the plotted semantic-discovery comparisons for Figure 4, Figure 5, and Figure 7, keeping it only as a syntactic reference outside the main comparison set.
- Reran all `exp_main_v1` schemes on commit `922a148`, which equalized the current promoted main-experiment inputs at `305` queries and restored the expected ordering `oracle > hiroute > flood/flat_iroute`.
- Reworked Figure 6 into a two-panel mechanism figure: HiRoute-only staged contraction on the left, cross-method probes/query on the right.
- Reworked Figure 7 into a two-panel deadline figure: success within deadline on the left, median successful latency on the right.
- Added explicit query filters to the experiment configs so `exp_main_v1` now runs only the `medium/high` ambiguity workload and `exp_ablation_v1` now runs only the `high`-ambiguity stress workload.
- Reran `exp_main_v1` on the filtered workload; the main comparison now uses `210` queries and preserves the expected ordering `oracle (1.0) > hiroute (0.857143) > flood/flat_iroute (0.357143)`.
- Reran `exp_ablation_v1` on the filtered `high`-ambiguity workload; the ablation now clearly separates the full hierarchy from predicate-only filtering (`0.875` vs `0.208333`), which resolves the earlier constraint-dominant artifact.

## 2026-03-16

- Rebuilt the official main-paper experiments around `smartcity_v2`, topology-consistent query bundles, and budget-aware `exp_routing_main_v2` / `exp_object_main_v2` / `exp_ablation_v2`.
- Enforced split-safe runtime slicing, added explicit `budget` to run IDs and manifests, and switched the v2 figures to query-bootstrap confidence intervals.
- Separated `flat_iroute` from `flood`, added the `inf_tag_forwarding` external semantic baseline, and aligned the v2 figure registry to the new experiment IDs.
- Shared sequential manifest fallback across discovery baselines; this removed the old unfair advantage from HiRoute-only fallback logic.
- Fixed workflow parsing so system `python3` can read YAML manifests written by the project `.venv`.
- Extended the v2 official scenario horizon from `16s` to `24s` so every promoted run completes all `240` test queries.
- Reran the complete v2 official matrix on commit `c4e7cfc`.
- Figure 4 is now a true budget frontier. The main signal is no longer a large success gap; instead HiRoute reduces discovery cost relative to the flat and INF-style baselines while staying near-perfect on success, and oracle remains the latency upper bound.
- Figure 5 and Figure 10 are now marked as sanity/internal figures. Once the corrected fallback semantics are enforced, the current `object_hard` bundle no longer discriminates methods strongly enough for publication-grade failure or ablation claims.

## 2026-03-18

- Rebound the compact `smartcity_v3` paper path so Figure 4 is now a routing-support figure rather than a saturated success-overhead frontier.
- Promoted the compact object-main manifest sweep to Figure 5, making object-level semantic resolution the primary compact effectiveness result.
- Recast Figure 10 as a manifest=`1` ablation figure, which at the time was intended to support a mechanism story under tight fallback.
- Updated the paper notes and figure registry so Figure 4, Figure 5, and Figure 10 now reflect the actual compact promoted results instead of the earlier v2 roles.
- Expanded the compact routing baseline set to include `predicates_only` and `random_admissible`, so the next Figure 4 rerun can separate hard-filter-only behavior, admissible random control, and hierarchical semantic routing.

## 2026-04-17

- Split the mainline stage freshness model into `simulation_fingerprint` versus `stage_contract_fingerprint`, so unchanged ndnSIM inputs now reuse completed runs while contract-only changes refresh validations, aggregates, and figures without rerunning simulation.
- Formalized `state_scaling` as a `state_only` experiment, updated `validate_runtime_slice.py` and `validate_aggregate_traceability.py` accordingly, and promoted the existing `20260416_134544` scaling runs without rerunning ndnSIM.
- Reran the official `robustness` stage on the mainline compact topology with parallel dispatch; all four scenario assignments completed, promoted, aggregated, and rendered successfully.
- Fixed the mainline figure renderer so `plot_main_figures.py` no longer crashes on duplicate per-scheme rows in `routing_support.csv` / `candidate_shrinkage.csv`; the total `full_mainline` refresh now completes end-to-end.
- At that point, the mainline gate state was: `object_main = ready_for_main_figure`, `ablation = ready_for_support_figure`, `routing_main = completed`, `state_scaling = completed`, `robustness = completed`. Later 2026-05-04 notes supersede this status.
- At that point, the refreshed Route B evidence remained consistent with the implementation-bound paper story: object-level terminal success was strong, first-fetch correctness stayed materially below terminal success for HiRoute, manifest rescue was still invariant in `object_main` / `ablation`, and the ablation mechanism ordering was clean even though cost ordering was not.
- Recentered the active Route B paper path around `fig_ablation` as the main mechanism figure, with `routing_support`, `candidate_shrinkage`, and `deadline_summary` as routing support, `object_main` as a cautionary manifest-sweep figure, `state_scaling` as a large-topology support experiment, and `robustness` as a degradation-profile figure.
- Removed the vacuous paper-facing object metric `best_object_chosen_given_relevant_domain` from `object_main_manifest_sweep.csv`, added `ci_manifest_rescue_rate`, and kept manifest rescue explicit even when the observed rate is zero.
- Added query-bootstrap CI fields and remote-probe summaries to `ablation_summary.csv`, then rebuilt the paper-facing ablation figure around terminal success, first-fetch correctness, and discovery cost instead of an empty wrong-object panel.
- Extended `robustness_timeseries.csv` with `failure_time_s` and `recovery_time_s` so the plotted figure can mark events directly rather than relying on hard-coded time annotations.
- Switched the paper-facing `state_scaling` experiment to the larger `rf_1239_sprint` topology with `domainSweepCounts = 4,8,12,16` and `objectsPerDomainSweep = 200,400,800`, while preserving the `state_only` contract.
