# Revision Log

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
