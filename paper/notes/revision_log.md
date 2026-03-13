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
